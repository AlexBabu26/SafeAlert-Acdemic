from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IncidentMessageViewSet

router = DefaultRouter()
router.register(r'', IncidentMessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
]

