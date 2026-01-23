from django.db import models
from django.contrib.auth.models import User
from .constants import INCIDENT_STATUS_CHOICES, DEFAULT_STATUS


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class IncidentReport(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='incidents')
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='incidents')
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    location_text = models.CharField(max_length=500, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    status = models.CharField(max_length=20, choices=INCIDENT_STATUS_CHOICES, default=DEFAULT_STATUS)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.category.name} - {self.user.username} ({self.status})"


class IncidentAttachment(models.Model):
    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='incidents/%Y/%m/%d/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Attachment for {self.incident}"


class StatusHistory(models.Model):
    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE, related_name='status_history')
    old_status = models.CharField(max_length=20, choices=INCIDENT_STATUS_CHOICES, blank=True)
    new_status = models.CharField(max_length=20, choices=INCIDENT_STATUS_CHOICES)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='status_changes')
    changed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Status Histories'
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['-changed_at']),
            models.Index(fields=['incident', '-changed_at']),
        ]

    def __str__(self):
        return f"{self.incident} - {self.old_status} → {self.new_status}"

