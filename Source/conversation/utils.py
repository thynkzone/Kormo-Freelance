from django.utils import timezone

def get_last_seen(dt):
    if not dt:
        return "never"

    now = timezone.now()
    delta = now - dt

    if delta.total_seconds() < 3600:
        return "less than an hour ago"
    
    hours = delta.days * 24 + delta.seconds // 3600
    if hours < 24:
        return f"{hours} hours ago"

    days = delta.days
    if days < 7:
        return f"{days} days ago"

    weeks = days // 7
    return f"{weeks} weeks ago" 