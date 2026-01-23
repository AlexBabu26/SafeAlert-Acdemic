from rest_framework import permissions


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners to view their own incidents.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for the owner
        if request.method in permissions.SAFE_METHODS:
            return obj.user == request.user
        return obj.user == request.user


class IsAdminUser(permissions.BasePermission):
    """
    Permission check for admin users (is_staff=True).
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff

