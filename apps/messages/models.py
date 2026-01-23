from django.db import models
from django.contrib.auth.models import User
from apps.incidents.models import IncidentReport


class IncidentMessage(models.Model):
    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['incident', 'created_at']),
        ]

    def __str__(self):
        return f"Message from {self.sender.username} on {self.incident}"

    @property
    def sender_role(self):
        return 'admin' if self.sender.is_staff else 'user'

