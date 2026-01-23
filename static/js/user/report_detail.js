document.addEventListener('DOMContentLoaded', function() {
    if (!requireAuth()) return;

    const reportId = window.location.pathname.split('/').pop();
    
    loadReport();
    loadMessages();

    async function loadReport() {
        const container = document.getElementById('report-detail');
        
        try {
            const incident = await apiGet(`${API_ENDPOINTS.incidents}${reportId}/`);
            
            container.innerHTML = `
                <div class="card-header bg-light">
                    <div class="d-flex justify-content-between align-items-center">
                        <h4 class="mb-0">${escapeHtml(incident.title || 'Incident Report')}</h4>
                        ${formatStatus(incident.status)}
                    </div>
                </div>
                <div class="card-body">
                    <dl class="row">
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
        } catch (error) {
            container.innerHTML = `<div class="alert alert-danger">${escapeHtml(error.message)}</div>`;
            console.error('Failed to load report:', error);
        }
    }

    async function loadMessages() {
        const container = document.getElementById('messages-list');
        
        try {
            const messages = await apiGet(`${API_ENDPOINTS.incidents}${reportId}/messages/`);
            
            if (messages.results && messages.results.length === 0) {
                container.innerHTML = '<div class="text-center py-3"><p class="text-muted">No messages yet.</p></div>';
                return;
            }

            let html = '';
            const msgs = messages.results || messages;
            msgs.forEach(msg => {
                const isAdmin = msg.sender_role === 'admin';
                html += `
                    <div class="mb-3 ${isAdmin ? 'border-start border-primary border-3 ps-3' : ''}">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <strong>${escapeHtml(msg.sender_username)}</strong>
                            <small class="text-muted">${formatDate(msg.created_at)}</small>
                        </div>
                        <p class="mb-0">${escapeHtml(msg.message).replace(/\n/g, '<br>')}</p>
                    </div>
                `;
            });
            
            container.innerHTML = html;
        } catch (error) {
            container.innerHTML = `<div class="alert alert-danger">${escapeHtml(error.message)}</div>`;
            console.error('Failed to load messages:', error);
        }
    }
});

