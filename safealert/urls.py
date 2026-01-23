"""
URL configuration for safealert project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    # API routes
    path('api/auth/', include('apps.accounts.urls')),
    path('api/categories/', include('apps.incidents.urls_category')),
    path('api/incidents/', include('apps.incidents.urls')),
    path('api/admin/', include('apps.incidents.urls_admin')),
    path('api/admin/analytics/', include('apps.analytics.urls')),
    path('api/incidents/<int:incident_id>/messages/', include('apps.messages.urls')),
    
    # Custom admin frontend routes (must come before Django admin)
    path('admin/dashboard', TemplateView.as_view(template_name='adminpanel/dashboard.html'), name='admin_dashboard'),
    path('admin/reports/<int:pk>', TemplateView.as_view(template_name='adminpanel/report_detail.html'), name='admin_report_detail'),
    path('admin/analytics', TemplateView.as_view(template_name='adminpanel/analytics.html'), name='admin_analytics'),
    
    # Django admin (catch-all for other admin routes)
    path('admin/', admin.site.urls),
    
    # Frontend routes
    path('', TemplateView.as_view(template_name='public/landing.html'), name='landing'),
    path('register', TemplateView.as_view(template_name='public/register.html'), name='register'),
    path('login', TemplateView.as_view(template_name='public/login.html'), name='login'),
    path('reports', TemplateView.as_view(template_name='user/dashboard.html'), name='user_dashboard'),
    path('report/new', TemplateView.as_view(template_name='user/report_new.html'), name='report_new'),
    path('reports/<int:pk>', TemplateView.as_view(template_name='user/report_detail.html'), name='report_detail'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

