from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Permission check for admin users (is_staff=True).
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff

