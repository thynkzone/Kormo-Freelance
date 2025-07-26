from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.central, name='dashboard'),
    path('notifications/', views.notifications, name='notifications'),
    path('mark-notification-read/<int:notification_id>/', views.mark_notification_read, name='mark_notification_read'),
    path('mark-all-notifications-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]
