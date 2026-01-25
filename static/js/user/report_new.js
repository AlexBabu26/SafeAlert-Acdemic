document.addEventListener('DOMContentLoaded', function() {
    if (!requireAuth()) return;

    // Load categories
    loadCategories();
    
    // Automatically fetch location based on IP address
    fetchLocationFromIP();

    // Refresh location button handler
    const refreshBtn = document.getElementById('refresh-location-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            // Clear current values to force refresh
            document.getElementById('location_text').value = '';
            document.getElementById('latitude').value = '';
            document.getElementById('longitude').value = '';
            document.getElementById('coordinates-display').style.display = 'none';
            fetchLocationFromIP();
        });
    }

    const form = document.getElementById('report-form');
    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const categoryId = document.getElementById('category').value;
        const title = document.getElementById('title').value;
        const description = document.getElementById('description').value;
        const location_text = document.getElementById('location_text').value;
        const latitude = document.getElementById('latitude').value;
        const longitude = document.getElementById('longitude').value;
        const fileInput = document.getElementById('attachment');

        if (!categoryId || !description) {
            showToast('Please fill in all required fields.', 'error');
            return;
        }

        try {
            showLoader();

            // First create the incident with coordinates
            const incidentData = {
                category: parseInt(categoryId),
                title: title || undefined,
                description: description,
                location_text: location_text || undefined,
                latitude: latitude ? parseFloat(latitude) : null,
                longitude: longitude ? parseFloat(longitude) : null,
            };

            const incident = await apiPost(API_ENDPOINTS.incidents, incidentData);

            if (!incident || !incident.id) {
                console.error('Invalid response from API:', incident);
                showToast('Report submitted, but could not redirect. Please check your reports.', 'warning');
                setTimeout(() => {
                    window.location.href = '/reports';
                }, 500);
                return;
            }

            // Upload file if selected
            if (fileInput.files.length > 0) {
                try {
                    const formData = new FormData();
                    formData.append('file', fileInput.files[0]);
                    await apiPostFormData(`${API_ENDPOINTS.incidents}${incident.id}/attachments/`, formData);
                    console.log('File uploaded successfully');
                } catch (error) {
                    console.error('Failed to upload file:', error);
                    // Don't fail the whole submission if file upload fails
                    showToast('Report submitted, but file upload failed. You can add it later.', 'warning');
                }
            }

            // Show tracking code modal if tracking code is present
            if (incident.tracking_code) {
                showTrackingCodeModal(incident.tracking_code, incident.id);
            } else {
                showToast('Report submitted successfully!', 'success');
                setTimeout(() => {
                    window.location.href = `/reports/${incident.id}`;
                }, 500);
            }
        } catch (error) {
            showToast(error.message || 'Failed to submit report.', 'error');
        } finally {
            hideLoader();
        }
    });

    async function loadCategories() {
        try {
            const data = await apiGet(API_ENDPOINTS.categories);
            const select = document.getElementById('category');
            // Categories API returns an array directly, not wrapped in results
            const categories = Array.isArray(data) ? data : (data.results || []);
            categories.forEach(cat => {
                const option = document.createElement('option');
                option.value = cat.id;
                option.textContent = cat.name;
                select.appendChild(option);
            });
        } catch (error) {
            showToast('Failed to load categories.', 'error');
            console.error('Failed to load categories:', error);
        }
    }

    /**
     * Automatically fetch user's location based on IP address
     * Uses ipapi.co which handles IP detection and geolocation in one call
     */
    async function fetchLocationFromIP() {
        const locationInput = document.getElementById('location_text');
        const latitudeInput = document.getElementById('latitude');
        const longitudeInput = document.getElementById('longitude');
        const locationStatus = document.getElementById('location-status');
        const coordsDisplay = document.getElementById('coordinates-display');
        const coordsText = document.getElementById('coords-text');
        const mapLink = document.getElementById('map-preview-link');
        
        // Don't overwrite if user has already entered a location
        if (locationInput.value.trim()) {
            locationStatus.textContent = 'Location set manually';
            return;
        }

        locationStatus.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Auto-detecting location...';

        try {
            // Use ipapi.co - combines IP detection and geolocation in one CORS-friendly call
            // Free tier: 1000 requests/day, no API key required
            const response = await fetch('https://ipapi.co/json/');
            const geoData = await response.json();

            if (geoData && !geoData.error) {
                // Format location string (City, Region, Country)
                const locationParts = [];
                if (geoData.city) locationParts.push(geoData.city);
                if (geoData.region) locationParts.push(geoData.region);
                if (geoData.country_name) locationParts.push(geoData.country_name);
                
                const locationString = locationParts.join(', ');
                
                // Auto-fill the location field
                if (locationString) {
                    locationInput.value = locationString;
                    locationInput.setAttribute('data-auto-filled', 'true');
                }

                // Store coordinates
                if (geoData.latitude && geoData.longitude) {
                    latitudeInput.value = geoData.latitude;
                    longitudeInput.value = geoData.longitude;
                    
                    // Show coordinates display
                    coordsText.textContent = `${geoData.latitude.toFixed(6)}, ${geoData.longitude.toFixed(6)}`;
                    mapLink.href = `https://www.google.com/maps?q=${geoData.latitude},${geoData.longitude}`;
                    coordsDisplay.style.display = 'block';
                    
                    locationStatus.innerHTML = '<i class="bi bi-check-circle text-success"></i> Location detected from IP. You can edit if incorrect.';
                    console.log('Location auto-filled from IP:', locationString, `(${geoData.latitude}, ${geoData.longitude})`);
                } else {
                    locationStatus.innerHTML = '<i class="bi bi-info-circle text-warning"></i> Location detected (no coordinates). You can edit if incorrect.';
                }
            } else {
                locationStatus.innerHTML = '<i class="bi bi-x-circle text-danger"></i> Could not detect location. Please enter manually.';
                console.warn('Failed to fetch location from IP:', geoData.reason || 'Unknown error');
            }
        } catch (error) {
            // Silently fail - location fetching is optional
            locationStatus.innerHTML = '<i class="bi bi-x-circle text-danger"></i> Could not detect location. Please enter manually.';
            console.warn('Could not auto-fetch location from IP:', error);
        }
    }
});

