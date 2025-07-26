from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q, Count
from django.core.files.storage import FileSystemStorage
from django.core.validators import URLValidator, FileExtensionValidator, MaxValueValidator
from core.validators import validate_image_size, validate_image_type, validate_image_dimensions, validate_url, validate_audio_size, validate_audio_type
from django.utils import timezone
from job.models import Job
from django.core.exceptions import ValidationError
import os

# Create a custom storage for conversation images
conversation_image_storage = FileSystemStorage(location='content/static/conversation_images/')

# Create a custom storage for conversation documents
conversation_document_storage = FileSystemStorage(
    location='content/media/conversation_documents/',
    base_url='/media/conversation_documents/'
)

def validate_document_size(value):
    filesize = value.size
    if filesize > 20 * 1024 * 1024:  # 20MB
        raise ValidationError("Document size cannot exceed 20 MB.")

class Conversation(models.Model):
    members = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    @property
    def last_message(self):
        return self.messages.order_by('-created_at').first()

    def unread_count_for_user(self, user):
        """
        Calculate unread messages more precisely
        """
        return self.messages.filter(
            ~Q(read_by=user) &  # Message not explicitly read by user
            ~Q(created_by=user)  # Exclude messages created by the user
        ).count()

    def get_other_member(self, current_user):
        """
        Retrieve the other conversation member
        """
        return self.members.exclude(id=current_user.id).first()

    def save(self, *args, **kwargs):
        # Only update modified_at if explicitly told to
        if kwargs.pop('update_modified', False):
            self.modified_at = timezone.now()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ('-modified_at',)
    
    def __str__(self):
        members = list(self.members.all())
        if len(members) >= 2:
            return f'Conversation between {members[0].username} and {members[1].username}'
        return f'Conversation {self.id}'

class ConversationMessage(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    content = models.TextField(max_length=1000, blank=True, null=True)
    image = models.ImageField(
        upload_to='conversation_images/',
        null=True,
        blank=True,
        validators=[validate_image_size, validate_image_type, validate_image_dimensions]
    )
    document = models.FileField(
        upload_to='conversation_documents/',
        null=True,
        blank=True,
        storage=conversation_document_storage,
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf']),
            validate_document_size
        ]
    )
    voice = models.FileField(
        upload_to='conversation_voices/',
        null=True,
        blank=True,
        validators=[validate_audio_size, validate_audio_type]
    )
    voice_duration = models.CharField(max_length=8, blank=True, null=True)  # Format: MM:SS
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='created_messages', on_delete=models.CASCADE)
    read_by = models.ManyToManyField(User, related_name='read_messages', blank=True)
    delivered_to = models.ManyToManyField(User, related_name='delivered_messages', blank=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if self.document and not is_new:
            # Delete old file if it exists
            old_instance = ConversationMessage.objects.get(pk=self.pk)
            if old_instance.document and old_instance.document != self.document:
                old_instance.document.delete(save=False)
        super().save(*args, **kwargs)
        if is_new:  # Only update conversation's modified_at for new messages
            # Update conversation's modified_at to match message creation time
            self.conversation.modified_at = self.created_at
            self.conversation.save(update_modified=True)
            # Auto-mark as delivered to all online members except sender
            for member in self.conversation.members.all():
                if member != self.created_by:
                    self.delivered_to.add(member)

    @property
    def is_read(self):
        """Check if message is read by all other members"""
        other_members = self.conversation.members.exclude(id=self.created_by.id)
        return all(self.read_by.filter(id=member.id).exists() for member in other_members)

    @property
    def is_delivered(self):
        """Check if message is delivered to all other members"""
        other_members = self.conversation.members.exclude(id=self.created_by.id)
        return all(self.delivered_to.filter(id=member.id).exists() for member in other_members)

    class Meta:
        ordering = ('created_at',)