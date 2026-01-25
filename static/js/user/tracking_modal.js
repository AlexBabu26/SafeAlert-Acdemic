/**
 * Tracking Code Modal
 * Shows tracking code after report submission
 */

function showTrackingCodeModal(trackingCode, incidentId) {
    // Create modal HTML
    const modalHTML = `
        <div class="modal fade" id="trackingCodeModal" tabindex="-1" data-bs-backdrop="static" data-bs-keyboard="false">
            <div class="modal-dialog modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header bg-success text-white">
                        <h5 class="modal-title">
                            <i class="bi bi-check-circle me-2"></i>Report Submitted Successfully!
                        </h5>
                    </div>
                    <div class="modal-body text-center py-4">
                        <div class="mb-3">
                            <i class="bi bi-shield-check text-success" style="font-size: 48px;"></i>
                        </div>
                        <h6 class="mb-3">Your Tracking Code</h6>
                        <div class="alert alert-info mb-3">
                            <div class="d-flex align-items-center justify-content-center gap-2">
                                <code class="fs-4 fw-bold text-primary" id="tracking-code-display">${trackingCode}</code>
                                <button class="btn btn-sm btn-outline-primary" onclick="copyTrackingCode('${trackingCode}')" title="Copy to clipboard">
                                    <i class="bi bi-clipboard"></i>
                                </button>
                            </div>
                        </div>
                        <p class="text-muted small mb-3">
                            <i class="bi bi-info-circle me-1"></i>
                            Save this tracking code to check your report status anytime, even without logging in.
                        </p>
                        <div class="d-grid gap-2">
                            <a href="/track" class="btn btn-outline-secondary">
                                <i class="bi bi-search"></i> Track Report Now
                            </a>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" onclick="goToReportDetail(${incidentId})">
                            View Report Details
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Remove existing modal if any
    const existingModal = document.getElementById('trackingCodeModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // Append modal to body
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Show modal
    const modalElement = document.getElementById('trackingCodeModal');
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

function copyTrackingCode(trackingCode) {
    navigator.clipboard.writeText(trackingCode).then(() => {
        showToast('Tracking code copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy. Please copy manually.', 'error');
    });
}

function goToReportDetail(incidentId) {
    window.location.href = `/reports/${incidentId}`;
}

