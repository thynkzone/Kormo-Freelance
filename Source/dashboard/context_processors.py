from .models import Notification

def notification_count(request):
    """Context processor to add unread notification count to all templates."""
    if request.user.is_authenticated:
        unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
        return {'unread_notifications_count': unread_notifications_count}
    return {'unread_notifications_count': 0} 