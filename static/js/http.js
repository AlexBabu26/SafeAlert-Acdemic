// HTTP client with JWT authentication and auto-refresh

async function apiRequest(url, options = {}) {
    const token = getAccessToken();
    
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    let response = await fetch(url, {
        ...options,
        headers,
    });

    // If 401, try to refresh token and retry once
    if (response.status === 401 && token) {
        try {
            const newToken = await refreshAccessToken();
            headers['Authorization'] = `Bearer ${newToken}`;
            response = await fetch(url, {
                ...options,
                headers,
            });
        } catch (error) {
            // Refresh failed, redirect to login
            clearTokens();
            if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                window.location.href = '/login';
            }
            throw error;
        }
    }

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'An error occurred' }));
        throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`);
    }

    return response.json();
}

async function apiGet(url, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const fullUrl = queryString ? `${url}?${queryString}` : url;
    return apiRequest(fullUrl, { method: 'GET' });
}

async function apiPost(url, data) {
    return apiRequest(url, {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

async function apiPatch(url, data) {
    return apiRequest(url, {
        method: 'PATCH',
        body: JSON.stringify(data),
    });
}

async function apiDelete(url) {
    return apiRequest(url, { method: 'DELETE' });
}

// For file uploads
async function apiPostFormData(url, formData) {
    const token = getAccessToken();
    const headers = {};
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    let response = await fetch(url, {
        method: 'POST',
        headers,
        body: formData,
    });

    if (response.status === 401 && token) {
        try {
            const newToken = await refreshAccessToken();
            headers['Authorization'] = `Bearer ${newToken}`;
            response = await fetch(url, {
                method: 'POST',
                headers,
                body: formData,
            });
        } catch (error) {
            clearTokens();
            if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                window.location.href = '/login';
            }
            throw error;
        }
    }

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'An error occurred' }));
        throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`);
    }

    return response.json();
}

