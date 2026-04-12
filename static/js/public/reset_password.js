/**
 * Reset Password Page
 */

const API_BASE = '/api/auth';

// Get token from URL
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

document.addEventListener('DOMContentLoaded', async () => {
    setupPasswordToggle('new_password', 'toggle-new-password');
    setupPasswordToggle('confirm_password', 'toggle-confirm-password');

    if (!token) {
        showError('Invalid reset link. Please request a new password reset.');
        document.getElementById('reset-password-form').style.display = 'none';
        return;
    }
    
    // Set token in hidden field
    document.getElementById('token').value = token;
    
    // Verify token is valid
    try {
        const response = await fetch(`${API_BASE}/verify-reset-token/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ token })
        });
        
        const data = await response.json();
        
        if (!data.valid) {
            showError(data.message || 'Invalid or expired reset token.');
            document.getElementById('reset-password-form').style.display = 'none';
        }
        
    } catch (error) {
        console.error('Error verifying token:', error);
        showError('Error verifying reset link. Please try again.');
    }
});

document.getElementById('reset-password-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const newPassword = document.getElementById('new_password').value;
    const confirmPassword = document.getElementById('confirm_password').value;
    const token = document.getElementById('token').value;
    
    // Validate password strength (mirrors backend rules)
    if (newPassword.length < 8) {
        showError('Password must be at least 8 characters long.');
        return;
    }
    if (!/[a-zA-Z]/.test(newPassword) || !/[0-9]/.test(newPassword)) {
        showError('Password must contain at least one letter and one digit.');
        return;
    }
    const commonPasswords = ['password','password1','12345678','123456789','qwerty123','qwertyui',
        'abc12345','abc123456','iloveyou','admin123','letmein1','welcome1','monkey123','dragon123'];
    if (commonPasswords.includes(newPassword.toLowerCase())) {
        showError('This password is too common. Please choose a stronger one.');
        return;
    }

    // Validate passwords match
    if (newPassword !== confirmPassword) {
        showError('Passwords do not match.');
        return;
    }
    
    const submitBtn = e.target.querySelector('button[type="submit"]');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.spinner-border');
    
    // Show loading state
    submitBtn.disabled = true;
    btnText.classList.add('d-none');
    spinner.classList.remove('d-none');
    
    try {
        const response = await fetch(`${API_BASE}/reset-password/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                token: token,
                new_password: newPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Show success message and redirect to login
            showSuccess(data.message);
            
            // Redirect to login after 2 seconds
            setTimeout(() => {
                window.location.href = '/login';
            }, 2000);
            
        } else {
            showError(data.new_password ? data.new_password[0] : data.detail || 'An error occurred');
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
    const errorMsg = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    
    errorText.textContent = message;
    errorMsg.classList.remove('d-none');
    
    // Scroll to top to show error
    window.scrollTo(0, 0);
}

function showSuccess(message) {
    // Create success alert
    const form = document.getElementById('reset-password-form');
    
    const successDiv = document.createElement('div');
    successDiv.className = 'alert alert-success';
    successDiv.innerHTML = `
        <i class="bi bi-check-circle me-2"></i>
        ${message}
        <br><small class="text-muted">Redirecting to login page...</small>
    `;
    
    form.parentNode.insertBefore(successDiv, form);
    
    // Hide the form
    form.style.display = 'none';
}

function setupPasswordToggle(inputId, buttonId) {
    const input = document.getElementById(inputId);
    const button = document.getElementById(buttonId);
    if (!input || !button) return;

    button.addEventListener('click', function() {
        const icon = button.querySelector('i');
        const isHidden = input.type === 'password';
        input.type = isHidden ? 'text' : 'password';
        icon.className = isHidden ? 'bi bi-eye' : 'bi bi-eye-slash';
        button.setAttribute('aria-label', isHidden ? 'Hide password' : 'Show password');
    });
}

