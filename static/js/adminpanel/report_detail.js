document.addEventListener('DOMContentLoaded', function() {
    if (!requireAuth()) return;

    const userInfo = getUserInfo();
    if (!userInfo || !userInfo.is_staff) {
        window.location.href = '/reports';
        return;
    }

    const reportId = window.location.pathname.split('/').pop();
    let currentStatus = '';
    
    loadReport();
    loadMessages();

    // Status update form
    document.getElementById('status-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const status = document.getElementById('status').value;
        const notes = document.getElementById('status-notes').value;

        try {
            showLoader();
            await apiPatch(`${API_ENDPOINTS.admin.incidents}${reportId}/status/`, {
                status: status,
                notes: notes || '',
            });

            showToast('Status updated successfully!', 'success');
            document.getElementById('status-notes').value = '';
            loadReport();
        } catch (error) {
            showToast(error.message || 'Failed to update status.', 'error');
        } finally {
            hideLoader();
        }
    });

    // Message form
    document.getElementById('message-form').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = document.getElementById('message').value;

        try {
            showLoader();
            await apiPost(`${API_ENDPOINTS.incidents}${reportId}/messages/`, {
                message: message,
            });

            showToast('Message sent successfully!', 'success');
            document.getElementById('message').value = '';
            loadMessages();
        } catch (error) {
            showToast(error.message || 'Failed to send message.', 'error');
        } finally {
            hideLoader();
        }
    });

    async function loadReport() {
        const container = document.getElementById('report-detail');
        
        try {
            const incident = await apiGet(`${API_ENDPOINTS.admin.incidents}${reportId}/`);
            
            currentStatus = incident.status;
            document.getElementById('status').value = incident.status;
            
            // Calculate time to reach if coordinates are available
            let timeToReachHTML = '';
            if (incident.latitude && incident.longitude) {
                timeToReachHTML = await calculateTimeToReach(incident.latitude, incident.longitude);
            }
            
            container.innerHTML = `
                <div class="card-header bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <h4 class="mb-0">Report #${incident.id} - ${escapeHtml(incident.title || 'Incident Report')}</h4>
                        ${formatStatus(incident.status)}
                    </div>
                </div>
                <div class="card-body">
                    <dl class="row">
                        <dt class="col-sm-2">User:</dt>
                        <dd class="col-sm-10">${escapeHtml(incident.user_username)}</dd>
                        
                        <dt class="col-sm-2">Category:</dt>
                        <dd class="col-sm-10">${escapeHtml(incident.category_name)}</dd>
                        
                        <dt class="col-sm-2">Description:</dt>
                        <dd class="col-sm-10">${escapeHtml(incident.description).replace(/\n/g, '<br>')}</dd>
                        
                        ${incident.location_text ? `
                            <dt class="col-sm-2">Location:</dt>
                            <dd class="col-sm-10">${escapeHtml(incident.location_text)}</dd>
                        ` : ''}
                        
                        ${incident.latitude && incident.longitude ? `
                            <dt class="col-sm-2">Coordinates:</dt>
                            <dd class="col-sm-10">
                                <span class="font-monospace">${incident.latitude}, ${incident.longitude}</span>
                                <a href="${incident.map_url || `https://www.google.com/maps?q=${incident.latitude},${incident.longitude}`}" 
                                   target="_blank" class="btn btn-sm btn-outline-primary ms-2">
                                    <i class="bi bi-geo-alt-fill"></i> View on Map
                                </a>
                            </dd>
                            ${timeToReachHTML}
                        ` : ''}
                        
                        ${incident.attachments && incident.attachments.length > 0 ? `
                            <dt class="col-sm-2">Attachments:</dt>
                            <dd class="col-sm-10">
                                <div class="d-flex flex-column gap-2">
                                    ${incident.attachments.map(attachment => {
                                        const fileName = attachment.file.split('/').pop();
                                        const isImage = /\.(jpg|jpeg|png|gif|webp)$/i.test(fileName);
                                        return `
                                            <div class="d-flex align-items-center gap-2">
                                                <a href="${attachment.file}" target="_blank" class="btn btn-sm btn-outline-primary">
                                                    <i class="bi ${isImage ? 'bi-image' : 'bi-paperclip'}"></i> ${escapeHtml(fileName)}
                                                </a>
                                                ${isImage ? `
                                                    <a href="${attachment.file}" target="_blank" class="btn btn-sm btn-link text-decoration-none">
                                                        <i class="bi bi-eye"></i> Preview
                                                    </a>
                                                ` : ''}
                                                <small class="text-muted">${formatDate(attachment.uploaded_at)}</small>
                                            </div>
                                        `;
                                    }).join('')}
                                </div>
                            </dd>
                        ` : ''}
                        
                        <dt class="col-sm-2">Created:</dt>
                        <dd class="col-sm-10">${formatDate(incident.created_at)}</dd>
                        
                        <dt class="col-sm-2">Last Updated:</dt>
                        <dd class="col-sm-10">${formatDate(incident.updated_at)}</dd>
                    </dl>
                </div>
            `;
            
            // Add event listeners for refresh buttons
            container.querySelectorAll('.refresh-time-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    // Simply reload the report to get fresh location data
                    loadReport();
                });
            });
        } catch (error) {
            container.innerHTML = `<div class="alert alert-danger">${escapeHtml(error.message)}</div>`;
            console.error('Failed to load report:', error);
        }
    }

    async function loadMessages() {
        const container = document.getElementById('messages-list');
        
        try {
            const messages = await apiGet(`${API_ENDPOINTS.incidents}${reportId}/messages/`);
            
            if (!messages || (messages.results && messages.results.length === 0) || (Array.isArray(messages) && messages.length === 0)) {
                container.innerHTML = '<div class="text-center py-4"><p class="text-muted mb-0"><i class="bi bi-chat-left-dots"></i> No messages yet.</p></div>';
                return;
            }

            let html = '';
            const msgs = messages.results || messages;
            if (msgs.length === 0) {
                container.innerHTML = '<div class="text-center py-4"><p class="text-muted mb-0"><i class="bi bi-chat-left-dots"></i> No messages yet.</p></div>';
                return;
            }
            
            msgs.forEach(msg => {
                const isAdmin = msg.sender_role === 'admin';
                html += `
                    <div class="mb-3 pb-3 border-bottom ${isAdmin ? 'border-start border-primary border-3 ps-3' : ''}">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <div>
                                <strong class="small">${escapeHtml(msg.sender_username)}</strong>
                                <span class="badge bg-${isAdmin ? 'primary' : 'secondary'} ms-1" style="font-size: 0.65rem;">${msg.sender_role}</span>
                            </div>
                            <small class="text-muted">${formatDate(msg.created_at)}</small>
                        </div>
                        <p class="mb-0 small">${escapeHtml(msg.message).replace(/\n/g, '<br>')}</p>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        } catch (error) {
            container.innerHTML = `<div class="alert alert-danger">${escapeHtml(error.message)}</div>`;
            console.error('Failed to load messages:', error);
        }
    }

    /**
     * Calculate time to reach incident location from admin's current location
     */
    async function calculateTimeToReach(incidentLat, incidentLon) {
        return new Promise((resolve) => {
            // Check if geolocation is supported
            if (!navigator.geolocation) {
                resolve(`
                    <dt class="col-sm-2">Time to Reach:</dt>
                    <dd class="col-sm-10">
                        <span class="text-muted"><i class="bi bi-info-circle"></i> Location services not supported</span>
                    </dd>
                `);
                return;
            }

            // Request admin's current location
            navigator.geolocation.getCurrentPosition(
                async (position) => {
                    const adminLat = position.coords.latitude;
                    const adminLon = position.coords.longitude;
                    
                    // Calculate distance using Haversine formula
                    const distance = calculateDistance(adminLat, adminLon, parseFloat(incidentLat), parseFloat(incidentLon));
                    
                    // Estimate travel time (assuming average speed of 50 km/h for driving)
                    const avgSpeedKmh = 50;
                    const timeInHours = distance / avgSpeedKmh;
                    const timeInMinutes = Math.round(timeInHours * 60);
                    
                    // Format display
                    let timeDisplay = '';
                    if (timeInMinutes < 60) {
                        timeDisplay = `${timeInMinutes} min`;
                    } else {
                        const hours = Math.floor(timeInMinutes / 60);
                        const mins = timeInMinutes % 60;
                        timeDisplay = mins > 0 ? `${hours}h ${mins}min` : `${hours}h`;
                    }
                    
                    const distanceDisplay = distance < 1 
                        ? `${Math.round(distance * 1000)} m` 
                        : `${distance.toFixed(1)} km`;
                    
                    resolve(`
                        <dt class="col-sm-2">Time to Reach:</dt>
                        <dd class="col-sm-10">
                            <div class="d-flex align-items-center flex-wrap gap-2">
                                <span class="badge bg-info"><i class="bi bi-clock"></i> ~${timeDisplay}</span>
                                <span class="text-muted">(${distanceDisplay} away)</span>
                                <button type="button" class="btn btn-sm btn-outline-secondary refresh-time-btn" data-incident-lat="${incidentLat}" data-incident-lon="${incidentLon}">
                                    <i class="bi bi-arrow-clockwise"></i> Refresh
                                </button>
                            </div>
                            <div class="time-to-reach-info mt-2 small text-muted">
                                <i class="bi bi-info-circle"></i> Estimated based on straight-line distance at average speed (50 km/h). Actual travel time may vary.
                            </div>
                        </dd>
                    `);
                },
                (error) => {
                    let errorMsg = 'Unable to get your location';
                    if (error.code === error.PERMISSION_DENIED) {
                        errorMsg = 'Location permission denied. Please enable location access.';
                    } else if (error.code === error.POSITION_UNAVAILABLE) {
                        errorMsg = 'Location information unavailable';
                    } else if (error.code === error.TIMEOUT) {
                        errorMsg = 'Location request timed out';
                    }
                    
                    resolve(`
                        <dt class="col-sm-2">Time to Reach:</dt>
                        <dd class="col-sm-10">
                            <div class="d-flex align-items-center gap-2">
                                <span class="text-muted"><i class="bi bi-exclamation-circle"></i> ${errorMsg}</span>
                                <button type="button" class="btn btn-sm btn-outline-secondary refresh-time-btn" data-incident-lat="${incidentLat}" data-incident-lon="${incidentLon}">
                                    <i class="bi bi-arrow-clockwise"></i> Retry
                                </button>
                            </div>
                        </dd>
                    `);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 60000 // Cache location for 1 minute
                }
            );
        });
    }

    /**
     * Calculate distance between two coordinates using Haversine formula
     * Returns distance in kilometers
     */
    function calculateDistance(lat1, lon1, lat2, lon2) {
        const R = 6371; // Earth's radius in kilometers
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLon = (lon2 - lon1) * Math.PI / 180;
        const a = 
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }
});

