// API Configuration
const API_BASE_URL = '/api';

// API Endpoints
const API_ENDPOINTS = {
    auth: {
        register: `${API_BASE_URL}/auth/register/`,
        login: `${API_BASE_URL}/auth/token/`,
        refresh: `${API_BASE_URL}/auth/token/refresh/`,
        me: `${API_BASE_URL}/auth/me/`,
    },
    categories: `${API_BASE_URL}/categories/`,
    incidents: `${API_BASE_URL}/incidents/`,
    admin: {
        incidents: `${API_BASE_URL}/admin/incidents/`,
        analytics: {
            summary: `${API_BASE_URL}/admin/analytics/summary/`,
            timeseries: `${API_BASE_URL}/admin/analytics/timeseries/`,
        }
    }
};

