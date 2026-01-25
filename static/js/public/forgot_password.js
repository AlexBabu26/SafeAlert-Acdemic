/**
 * Forgot Password Page
 */

const API_BASE = '/api/auth';

document.getElementById('forgot-password-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value.trim();
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.spinner-border');
    
    // Show loading state
    submitBtn.disabled = true;
    btnText.classList.add('d-none');
    spinner.classList.remove('d-none');
    
    try {
        const response = await fetch(`${API_BASE}/forgot-password/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Show success message
            const successMsg = document.getElementById('success-message');
            const successText = document.getElementById('success-text');
            
            // For demo purposes, show the reset link if token is provided
            if (data.token && data.reset_url) {
                successText.innerHTML = `
                    Password reset link generated! 
                    <br><br>
                    <strong>Demo Mode:</strong> Click the link below to reset your password:
                    <br>
                    <a href="${data.reset_url}" class="alert-link">Reset Password</a>
                    <br><br>
                    <small class="text-muted">In production, this link would be sent to your email.</small>
                `;
            } else {
                successText.textContent = data.message;
            }
            
            successMsg.classList.remove('d-none');
            
            // Hide the form
            document.getElementById('forgot-password-form').style.display = 'none';
            
        } else {
            // Show error
            showError(data.email ? data.email[0] : data.detail || 'An error occurred');
        }
        
    } catch (error) {
        console.error('Error:', error);
        showError('Network error. Please try again.');
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        btnText.classList.remove('d-none');
        spinner.classList.add('d-none');
    }
});

function showError(message) {
    // Create and show error alert
    const form = document.getElementById('forgot-password-form');
    
    // Remove existing error if any
    const existingError = document.querySelector('.alert-danger');
    if (existingError) {
        existingError.remove();
    }
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'alert alert-danger';
    errorDiv.innerHTML = `<i class="bi bi-exclamation-triangle me-2"></i>${message}`;
    
    form.parentNode.insertBefore(errorDiv, form);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
}

