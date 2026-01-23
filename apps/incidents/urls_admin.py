from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminIncidentReportViewSet

router = DefaultRouter()
router.register(r'incidents', AdminIncidentReportViewSet, basename='admin-incident')

urlpatterns = [
    path('', include(router.urls)),
]

