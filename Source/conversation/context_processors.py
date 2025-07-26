from django.db.models import Q, Count
from .models import Conversation, ConversationMessage

def unread_messages_count(request):
    if not request.user.is_authenticated:
        return {'total_unread': 0}
    
    # Get conversations where user is a member
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    
    # Count unread messages in a single query
    total_unread = ConversationMessage.objects.filter(
        conversation__in=conversations
    ).filter(
        ~Q(read_by=request.user) & ~Q(created_by=request.user)
    ).count()
    
    return {'total_unread': total_unread} 