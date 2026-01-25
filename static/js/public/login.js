document.addEventListener('DOMContentLoaded', function() {
    // Redirect if already logged in
    if (isAuthenticated()) {
        const userInfo = getUserInfo();
        redirectBasedOnRole(userInfo);
        return;
    }

    const form = document.getElementById('login-form');
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            showLoader();
            const data = await apiPost(API_ENDPOINTS.auth.login, {
                username,
                password,
            });

            setTokens(data.access, data.refresh);
            
            // Get user info
            const userInfo = await apiGet(API_ENDPOINTS.auth.me);
            setUserInfo(userInfo);

            showToast('Login successful!', 'success');
            
            // Redirect based on role
            setTimeout(() => {
                redirectBasedOnRole(userInfo);
            }, 500);
        } catch (error) {
            showToast(error.message || 'Login failed. Please check your credentials.', 'error');
        } finally {
            hideLoader();
        }
    });
});

function redirectBasedOnRole(userInfo) {
    if (!userInfo) {
        window.location.href = '/reports';
        return;
    }
    
    if (userInfo.is_staff) {
        window.location.href = '/admin/dashboard';
    } else if (userInfo.is_department) {
        window.location.href = '/department/dashboard';
    } else if (userInfo.is_responder) {
        window.location.href = '/responder/dashboard';
    } else {
        window.location.href = '/reports';
    }
}
