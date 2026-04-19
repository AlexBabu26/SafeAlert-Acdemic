// UI utility functions

/** Display timezone for all client-side date formatting (Chennai / India Standard Time). */
const APP_DISPLAY_TIMEZONE = 'Asia/Kolkata';

/**
 * Parse API datetime strings into a correct JS Date (instant).
 * Django/DRF usually sends ISO-8601 with Z or +00:00. Flask/Marshmallow often
 * emits naive UTC as "YYYY-MM-DDTHH:mm:ss" with no zone — browsers treat that as
 * *local* time, which breaks IST display. Strings without a timezone are treated as UTC.
 */
function parseAppDate(dateString) {
    if (dateString == null || dateString === '') return null;
    let s = String(dateString).trim();
    if (!s) return null;

    if (/[zZ]$/.test(s)) {
        const d = new Date(s);
        return Number.isNaN(d.getTime()) ? null : d;
    }
    if (/[+-]\d{2}:\d{2}$/.test(s) || /[+-]\d{4}$/.test(s)) {
        const d = new Date(s);
        return Number.isNaN(d.getTime()) ? null : d;
    }

    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) {
        const d = new Date(s + 'T00:00:00Z');
        return Number.isNaN(d.getTime()) ? null : d;
    }

    if (/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}/.test(s)) {
        s = s.replace(' ', 'T', 1);
    }

    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s)) {
        const d = new Date(s.endsWith('Z') ? s : s + 'Z');
        return Number.isNaN(d.getTime()) ? null : d;
    }

    const d = new Date(s);
    return Number.isNaN(d.getTime()) ? null : d;
}

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
    const date = parseAppDate(dateString);
    if (!date) return '-';
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
    const date = parseAppDate(dateString);
    if (!date) return '-';
    return date.toLocaleDateString('en-IN', {
        timeZone: APP_DISPLAY_TIMEZONE,
        year: 'numeric',
        month: 'short',
        day: 'numeric',
    });
}

/** Time of day only in APP_DISPLAY_TIMEZONE. */
function formatTimeOnly(dateString) {
    const date = parseAppDate(dateString);
    if (!date) return '-';
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
