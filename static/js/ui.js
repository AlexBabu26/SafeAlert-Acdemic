// UI utility functions

function showToast(message, type = 'info') {
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
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
}

function showLoader() {
    document.getElementById('loader').style.display = 'flex';
}

function hideLoader() {
    document.getElementById('loader').style.display = 'none';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
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

