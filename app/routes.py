"""
Frontend routes for serving HTML templates
"""
from flask import Blueprint, render_template, send_from_directory, current_app
from pathlib import Path

bp = Blueprint('frontend', __name__)


@bp.route('/')
def landing():
    """Landing page"""
    return render_template('public/landing.html')


@bp.route('/register')
def register_page():
    """Registration page"""
    return render_template('public/register.html')


@bp.route('/login')
def login_page():
    """Login page"""
    return render_template('public/login.html')


@bp.route('/forgot-password')
def forgot_password_page():
    """Forgot password page"""
    return render_template('public/forgot_password.html')


@bp.route('/reset-password')
def reset_password_page():
    """Reset password page"""
    return render_template('public/reset_password.html')


# ==================== User/Citizen Routes ====================

@bp.route('/reports')
def user_dashboard():
    """User dashboard"""
    return render_template('user/dashboard.html')


@bp.route('/report/new')
def report_new():
    """New report page"""
    return render_template('user/report_new.html')


@bp.route('/reports/<int:pk>')
def report_detail(pk):
    """Report detail page"""
    return render_template('user/report_detail.html')


@bp.route('/track')
def track_report():
    """Track anonymous report page"""
    return render_template('user/track.html')


# ==================== Responder Routes ====================

@bp.route('/responder/dashboard')
def responder_dashboard():
    """Responder dashboard"""
    return render_template('responder/dashboard.html')


@bp.route('/responder/assignments/<int:pk>')
def responder_assignment_detail(pk):
    """Responder assignment detail page"""
    return render_template('responder/assignment_detail.html')


# ==================== Department Routes ====================

@bp.route('/department/dashboard')
def department_dashboard():
    """Department command center"""
    return render_template('department/dashboard.html')


@bp.route('/department/incidents/<int:pk>')
def department_incident_detail(pk):
    """Department incident detail page"""
    return render_template('department/incident_detail.html')


@bp.route('/department/departments')
def department_departments():
    """Department overview page"""
    return render_template('department/departments.html')


@bp.route('/department/respondents')
def department_respondents():
    """Department respondent management page"""
    return render_template('department/respondents.html')


# ==================== Admin Routes ====================

@bp.route('/admin/dashboard')
def admin_dashboard():
    """Admin dashboard"""
    return render_template('adminpanel/dashboard.html')


@bp.route('/admin/reports/<int:pk>')
def admin_report_detail(pk):
    """Admin report detail page"""
    return render_template('adminpanel/report_detail.html')


@bp.route('/admin/analytics')
def admin_analytics():
    """Admin analytics page"""
    return render_template('adminpanel/analytics.html')


@bp.route('/admin/departments')
def admin_departments():
    """Admin department management page"""
    return render_template('adminpanel/departments.html')


@bp.route('/admin/users')
def admin_users():
    """Admin user management page"""
    return render_template('adminpanel/users.html')


# ==================== Static/Media Routes ====================

@bp.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory(current_app.config.get('STATIC_FOLDER', 'static'), filename)


@bp.route('/media/<path:filename>')
def media_files(filename):
    """Serve media files"""
    return send_from_directory(current_app.config.get('UPLOAD_FOLDER', 'media'), filename)
