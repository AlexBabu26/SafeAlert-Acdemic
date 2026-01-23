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

        try {
            showLoader();
            const response = await apiPost(API_ENDPOINTS.auth.register, data);

            setTokens(response.access, response.refresh);
            setUserInfo(response.user);

            showToast('Registration successful!', 'success');
            
            setTimeout(() => {
                window.location.href = '/reports';
            }, 500);
        } catch (error) {
            showToast(error.message || 'Registration failed. Please try again.', 'error');
        } finally {
            hideLoader();
        }
    });
});

