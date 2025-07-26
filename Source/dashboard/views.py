from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from job.models import Job, Proposal, Contract
from django.http import JsonResponse
from .models import Notification
from conversation.models import ConversationMessage

def create_notification(user, notification_type, message, related_job=None, related_user=None, related_conversation=None):
    """Helper function to create notifications"""
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        message=message,
        related_job=related_job,
        related_user=related_user,
        related_conversation=related_conversation
    )
    return notification

@login_required
def central(request):
    # Get notifications
    notifications = Notification.objects.filter(user=request.user)
    unread_notifications_count = notifications.filter(is_read=False).count()

    # Get posted jobs
    posted_jobs = Job.objects.filter(created_by=request.user).order_by('-created_at')
    completed_posted_jobs = posted_jobs.filter(completion_date__isnull=False).count()
    active_posted_jobs = posted_jobs.filter(completion_date__isnull=True).count()
    
    # Get hired jobs
    hired_jobs = Job.objects.filter(hired_freelancer=request.user).order_by('-created_at')
    completed_hired_jobs = hired_jobs.filter(completion_date__isnull=False).count()
    active_hired_jobs = hired_jobs.filter(completion_date__isnull=True).count()
    
    # Get proposals with contract information
    proposals = Proposal.objects.filter(freelancer=request.user).order_by('-created_at')
    for proposal in proposals:
        # Get the most recent active contract
        proposal.active_contract = Contract.objects.filter(
            job=proposal.job,
            freelancer=request.user,
            status__in=['freelancer_signed', 'completed']
        ).order_by('-created_at').first()

    # Get saved jobs
    saved_jobs = Job.objects.filter(saved_by__user=request.user).order_by('-saved_by__created_at')

    # Get pending contracts that need freelancer's signature
    pending_contracts = Contract.objects.filter(
        freelancer=request.user,
        status='client_signed'
    ).select_related('job', 'job__created_by').order_by('-created_at')

    return render(request, 'dashboard/central.html', {
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
        'posted_jobs': posted_jobs,
        'hired_jobs': hired_jobs,
        'proposals': proposals,
        'saved_jobs': saved_jobs,
        'completed_posted_jobs': completed_posted_jobs,
        'active_posted_jobs': active_posted_jobs,
        'completed_hired_jobs': completed_hired_jobs,
        'active_hired_jobs': active_hired_jobs,
        'pending_contracts': pending_contracts,
    })

@login_required
def mark_notification_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'success': True})
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

@login_required
def mark_all_notifications_read(request):
    if request.method == 'POST':
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

@login_required
def notifications(request):
    # Get notifications
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    unread_notifications_count = notifications.filter(is_read=False).count()

    return render(request, 'dashboard/notifications.html', {
        'notifications': notifications,
        'unread_notifications_count': unread_notifications_count,
    })
