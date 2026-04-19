/**
 * SafeAlert Service Worker
 * Provides offline support and caching
 */

const CACHE_NAME = 'safealert-v4';
const STATIC_ASSETS = [
    '/',
    '/login',
    '/register',
    '/static/css/style.css',
    '/static/js/auth.js',
    '/static/manifest.json',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[ServiceWorker] Install');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[ServiceWorker] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => self.skipWaiting())
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[ServiceWorker] Activate');
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames
                    .filter((name) => name !== CACHE_NAME)
                    .map((name) => {
                        console.log('[ServiceWorker] Removing old cache:', name);
                        return caches.delete(name);
                    })
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }

    // Skip API requests (always fetch from network)
    if (event.request.url.includes('/api/')) {
        return;
    }

    const requestUrl = new URL(event.request.url);
    const isStaticAsset =
        requestUrl.origin === self.location.origin &&
        requestUrl.pathname.startsWith('/static/');

    // For page navigations, prefer fresh HTML from network to avoid stale UI.
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request)
                .then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        const responseToCache = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, responseToCache);
                        });
                    }
                    return networkResponse;
                })
                .catch(async () => {
                    return (await caches.match(event.request)) || (await caches.match('/offline.html'));
                })
        );
        return;
    }

    // Use network-first for static assets so UI/JS updates are visible immediately.
    if (isStaticAsset) {
        event.respondWith(
            fetch(event.request)
                .then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        const responseToCache = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(event.request, responseToCache);
                        });
                    }
                    return networkResponse;
                })
                .catch(() => caches.match(event.request))
        );
        return;
    }

    event.respondWith(
        caches.match(event.request)
            .then((cachedResponse) => {
                // Return cached response if available
                if (cachedResponse) {
                    return cachedResponse;
                }

                // Otherwise, fetch from network
                return fetch(event.request)
                    .then((networkResponse) => {
                        // Don't cache if not a valid response
                        if (!networkResponse || networkResponse.status !== 200) {
                            return networkResponse;
                        }

                        // Clone the response
                        const responseToCache = networkResponse.clone();

                        // Cache the response for future use
                        caches.open(CACHE_NAME)
                            .then((cache) => {
                                // Only cache same-origin requests
                                if (event.request.url.startsWith(self.location.origin)) {
                                    cache.put(event.request, responseToCache);
                                }
                            });

                        return networkResponse;
                    })
                    .catch(() => {
                        // Return offline page for navigation requests
                        if (event.request.mode === 'navigate') {
                            return caches.match('/offline.html');
                        }
                        return null;
                    });
            })
    );
});

// Background sync for offline incident reports
self.addEventListener('sync', (event) => {
    console.log('[ServiceWorker] Sync event:', event.tag);
    
    if (event.tag === 'sync-incidents') {
        event.waitUntil(syncIncidents());
    }
});

async function syncIncidents() {
    try {
        // Get pending incidents from IndexedDB
        const db = await openDatabase();
        const pendingIncidents = await getPendingIncidents(db);

        for (const incident of pendingIncidents) {
            try {
                const response = await fetch('/api/incidents/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${incident.token}`
                    },
                    body: JSON.stringify(incident.data)
                });

                if (response.ok) {
                    // Remove from pending queue
                    await removePendingIncident(db, incident.id);
                    
                    // Notify the user
                    self.registration.showNotification('SafeAlert', {
                        body: 'Your incident report has been submitted.',
                        icon: '/static/icons/icon-192x192.png',
                        badge: '/static/icons/badge-72x72.png'
                    });
                }
            } catch (err) {
                console.error('[ServiceWorker] Failed to sync incident:', err);
            }
        }
    } catch (err) {
        console.error('[ServiceWorker] Sync failed:', err);
    }
}

// IndexedDB helper functions
function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('SafeAlertDB', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('pendingIncidents')) {
                db.createObjectStore('pendingIncidents', { keyPath: 'id', autoIncrement: true });
            }
        };
    });
}

function getPendingIncidents(db) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['pendingIncidents'], 'readonly');
        const store = transaction.objectStore('pendingIncidents');
        const request = store.getAll();
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

function removePendingIncident(db, id) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['pendingIncidents'], 'readwrite');
        const store = transaction.objectStore('pendingIncidents');
        const request = store.delete(id);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve();
    });
}

// Push notification event
self.addEventListener('push', (event) => {
    console.log('[ServiceWorker] Push received:', event);
    
    let notificationData = {
        title: 'SafeAlert',
        body: 'You have a new notification',
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/badge-72x72.png',
        data: {}
    };

    if (event.data) {
        try {
            notificationData = { ...notificationData, ...event.data.json() };
        } catch (e) {
            notificationData.body = event.data.text();
        }
    }

    event.waitUntil(
        self.registration.showNotification(notificationData.title, {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            data: notificationData.data,
            vibrate: [200, 100, 200],
            actions: notificationData.actions || []
        })
    );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
    console.log('[ServiceWorker] Notification clicked:', event);
    
    event.notification.close();
    
    const urlToOpen = event.notification.data?.url || '/';
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((windowClients) => {
                // Check if app is already open
                for (const client of windowClients) {
                    if (client.url === urlToOpen && 'focus' in client) {
                        return client.focus();
                    }
                }
                // Open new window
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

