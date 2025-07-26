from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# Create your models here.

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('message', 'Message'),
        ('proposal', 'Proposal'),
        ('hired', 'Hired'),
        ('review', 'Review'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_job = models.ForeignKey('job.Job', on_delete=models.CASCADE, null=True, blank=True)
    related_user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='related_notifications')
    related_conversation = models.ForeignKey('conversation.Conversation', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_notification_type_display()} for {self.user.username}"
