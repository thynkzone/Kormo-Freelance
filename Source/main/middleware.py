from django.utils import timezone
import pytz
from django.conf import settings

class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Always use Dhaka timezone
        timezone.activate(pytz.timezone('Asia/Dhaka'))
        return self.get_response(request) 