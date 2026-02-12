// HTTP client with JWT authentication and auto-refresh

function extractApiErrorMessage(errorData, fallbackMessage) {
    if (!errorData || typeof errorData !== 'object') {
        return fallbackMessage;
    }

    if (typeof errorData.detail === 'string' && errorData.detail.trim()) {
        return errorData.detail;
    }

    if (typeof errorData.message === 'string' && errorData.message.trim()) {
        return errorData.message;
    }

    const messages = [];
    Object.entries(errorData).forEach(([field, value]) => {
        if (field === 'detail' || field === 'message') {
            return;
        }

        const fieldLabel = `${field}: `;

        if (Array.isArray(value) && value.length) {
            messages.push(`${fieldLabel}${value.join(', ')}`);
            return;
        }

        if (typeof value === 'string' && value.trim()) {
            messages.push(`${fieldLabel}${value}`);
        }
    });

    if (messages.length) {
        return messages.join(' ');
    }

    return fallbackMessage;
}

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
        const fallbackMessage = `HTTP ${response.status}`;
        const errorData = await response.json().catch(() => null);
        throw new Error(extractApiErrorMessage(errorData, fallbackMessage));
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
        const fallbackMessage = `HTTP ${response.status}`;
        const errorData = await response.json().catch(() => null);
        throw new Error(extractApiErrorMessage(errorData, fallbackMessage));
    }

    return response.json();
}

