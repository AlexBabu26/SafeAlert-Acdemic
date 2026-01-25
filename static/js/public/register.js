document.addEventListener('DOMContentLoaded', function() {
    // Redirect if already logged in
    if (isAuthenticated()) {
        window.location.href = '/reports';
        return;
    }

    const form = document.getElementById('register-form');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const password = document.getElementById('password').value;
        const password2 = document.getElementById('password2').value;

        if (password !== password2) {
            showToast('Passwords do not match.', 'error');
            return;
        }

        const data = {
            username: document.getElementById('username').value,
            email: document.getElementById('email').value,
            first_name: document.getElementById('first_name').value,
            last_name: document.getElementById('last_name').value,
            password: password,
            password2: password2,
        };

        // Check for role selection if exists
        const roleSelect = document.getElementById('role');
        if (roleSelect) {
            data.role = roleSelect.value;
        }

        // Check for department selection if exists
        const departmentSelect = document.getElementById('department_id');
        if (departmentSelect && departmentSelect.value) {
            data.department_id = parseInt(departmentSelect.value);
        }

        try {
            showLoader();
            const response = await apiPost(API_ENDPOINTS.auth.register, data);

            // All users now require admin approval - show pending message
            if (response.pending_approval) {
                showToast(response.message || 'Registration successful! Your account is pending approval.', 'success');
                
                // Show a modal or alert with the pending message
                setTimeout(() => {
                    alert(response.message || 'Your account has been created and is pending approval. You will be notified once your account is activated by an administrator.');
                    window.location.href = '/login';
                }, 1000);
            } else if (response.access && response.refresh) {
                // If tokens are returned (shouldn't happen with new flow, but keep for backward compatibility)
                setTokens(response.access, response.refresh);
                setUserInfo(response.user);

                showToast('Registration successful!', 'success');
                
                setTimeout(() => {
                    window.location.href = '/reports';
                }, 500);
            } else {
                // Default: redirect to login
                showToast('Registration successful! Please wait for admin approval.', 'success');
                setTimeout(() => {
                    window.location.href = '/login';
                }, 1500);
            }
        } catch (error) {
            showToast(error.message || 'Registration failed. Please try again.', 'error');
        } finally {
            hideLoader();
        }
    });
});

