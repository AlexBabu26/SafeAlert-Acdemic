// UI utility functions

/** Display timezone for all client-side date formatting (Chennai / India Standard Time). */
const APP_DISPLAY_TIMEZONE = 'Asia/Kolkata';

function showToast(message, type = 'info', delay = 5000) {
    const toast = document.getElementById('toast');
    const toastBody = document.getElementById('toast-body');
    const toastTitle = document.getElementById('toast-title');
    
    const types = {
        success: { title: 'Success', class: 'text-success' },
        error: { title: 'Error', class: 'text-danger' },
        warning: { title: 'Warning', class: 'text-warning' },
        info: { title: 'Info', class: 'text-info' },
    };

    const config = types[type] || types.info;
    toastTitle.textContent = config.title;
    toastTitle.className = `me-auto ${config.class}`;
    toastBody.textContent = message;
    
    const bsToast = bootstrap.Toast.getOrCreateInstance(toast, { delay });
    bsToast.show();
}

function showLoader() {
    document.getElementById('loader').style.display = 'flex';
}

function hideLoader() {
    document.getElementById('loader').style.display = 'none';
}

function formatDate(dateString) {
    if (dateString == null || dateString === '') return '-';
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return '-';
    return date.toLocaleString('en-IN', {
        timeZone: APP_DISPLAY_TIMEZONE,
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
    });
}

/** Calendar date only (e.g. joined date) in APP_DISPLAY_TIMEZONE. */
function formatDateOnly(dateString) {
    if (dateString == null || dateString === '') return '-';
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return '-';
    return date.toLocaleDateString('en-IN', {
        timeZone: APP_DISPLAY_TIMEZONE,
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}

/** Time of day only in APP_DISPLAY_TIMEZONE. */
function formatTimeOnly(dateString) {
    if (dateString == null || dateString === '') return '-';
    const date = new Date(dateString);
    if (Number.isNaN(date.getTime())) return '-';
    return date.toLocaleTimeString('en-IN', {
        timeZone: APP_DISPLAY_TIMEZONE,
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
    });
}

function formatStatus(status) {
    const badges = {
        PENDING: '<span class="badge bg-warning">Pending</span>',
        VERIFIED: '<span class="badge bg-info">Verified</span>',
        RESOLVED: '<span class="badge bg-success">Resolved</span>',
    };
    return badges[status] || status;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
