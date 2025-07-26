from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse

from job.models import Job
from freelancer.models import Freelancer

from .forms import ConversationMessageForm
from .models import Conversation, ConversationMessage
from .utils import get_last_seen
from dashboard.views import create_notification

@login_required
def new_conversation(request, object_type, object_pk):
    """Handles new conversations between users."""
    
    if object_type == "freelancer":
        obj = get_object_or_404(Freelancer, pk=object_pk)
        recipient = obj.user
    else:
        obj = get_object_or_404(Job, pk=object_pk)
        recipient = obj.created_by

    # Prevent messaging yourself
    if recipient == request.user:
        return redirect('dashboard:dashboard')

    # Check if conversation already exists
    conversations = Conversation.objects.filter(members__in=[request.user.id]).filter(members__in=[recipient.id])

    if conversations.exists():
        return redirect('conversation:detail', pk=conversations.first().id)

    if request.method == 'POST':
        form = ConversationMessageForm(request.POST, request.FILES)
        if form.is_valid():
            conversation = Conversation.objects.create()
            conversation.members.add(request.user, recipient)
            conversation.save()

            conversation_message = form.save(commit=False)
            conversation_message.conversation = conversation
            conversation_message.created_by = request.user
            conversation_message.save()

            # Create notification for the recipient
            create_notification(
                user=recipient,
                notification_type='message',
                message=f'New message from {request.user.username}',
                related_user=request.user,
                related_conversation=conversation
            )

            # Handle JSON response for AJAX requests
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'conversation_id': conversation.id
                })

            return redirect('conversation:detail', pk=conversation.id)
    else:
        # Get initial message from URL parameter
        initial_message = request.GET.get('message', '')
        form = ConversationMessageForm(initial={'content': initial_message})
    
    return render(request, 'conversation/new.html', {
        'form': form,
        'recipient': recipient,
        'object_type': object_type,
        'object': obj
    })

@login_required
def detail(request, pk):
    # Get conversations ordered by last message
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    current_conversation = get_object_or_404(Conversation, pk=pk, members__in=[request.user.id])
    other_user = current_conversation.get_other_member(request.user)

    # Calculate unread counts and sort by last message
    for conversation in conversations:
        conversation.unread_count = conversation.unread_count_for_user(request.user)
    
    conversations = sorted(
        conversations,
        key=lambda c: c.last_message.created_at if c.last_message else c.created_at,
        reverse=True
    )

    # Mark messages as delivered and read
    unread_messages = current_conversation.messages.filter(
        ~Q(created_by=request.user),  # Messages not created by current user
        ~Q(read_by=request.user)      # Messages not already read by current user
    )
    
    for message in unread_messages:
        # Mark as delivered first
        message.delivered_to.add(request.user)
        # Then mark as read
        message.read_by.add(request.user)
        message.save()

    # Reset conversation modified time to reflect the latest action
    current_conversation.save(update_modified=True)

    if request.method == 'POST':
        form = ConversationMessageForm(request.POST, request.FILES)

        if form.is_valid():
            conversation_message = form.save(commit=False)
            conversation_message.conversation = current_conversation
            conversation_message.created_by = request.user
            conversation_message.save()
            
            # Auto-mark as delivered for online users
            other_member = current_conversation.get_other_member(request.user)
            if other_member:
                conversation_message.delivered_to.add(other_member)
                conversation_message.save()
                
                # Create notification for the other user
                create_notification(
                    user=other_member,
                    notification_type='message',
                    message=f'New message from {request.user.username}',
                    related_user=request.user,
                    related_conversation=current_conversation
                )
            
            return redirect('conversation:detail', pk=pk)
    else:
        form = ConversationMessageForm()

    # Get the last login time for the other user
    if other_user:
        other_user.last_login = other_user.last_login or timezone.now()

    return render(request, 'conversation/detail.html', {
        'conversation': current_conversation,
        'conversations': conversations,
        'form': form,
        'other_user': other_user,
        'pk': pk,
        'last_seen': get_last_seen(other_user.last_login if other_user else None)
    })

@login_required
def inbox(request):
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    
    # Calculate unread counts for each conversation
    for conversation in conversations:
        conversation.unread_count = conversation.unread_count_for_user(request.user)
    
    # Sort conversations by last message timestamp only
    conversations = sorted(
        conversations, 
        key=lambda c: c.last_message.created_at if c.last_message else c.created_at, 
        reverse=True
    )
    
    # Get the current conversation if it exists in the URL
    current_conversation = None
    if 'conversation_id' in request.GET:
        try:
            current_conversation = conversations.get(id=request.GET['conversation_id'])
        except (Conversation.DoesNotExist, AttributeError):
            pass
    
    return render(request, 'conversation/inbox.html', {
        'conversations': conversations,
        'current_conversation': current_conversation,
        'total_unread': sum(c.unread_count for c in conversations)
    })