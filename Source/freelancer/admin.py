from django.contrib import admin
from django.utils import timezone
from django.http import HttpRequest
from accounts.utils import send_subscription_activated_email
import logging

logger = logging.getLogger(__name__)

from .models import Category, Freelancer, FreelancerSkill, FreelancerExperience, FreelancerEducation, FreelancerCertification, FreelancerProject, Subscription, SubscriptionPlan

admin.site.register(Category)
admin.site.register(Freelancer)
admin.site.register(FreelancerSkill)
admin.site.register(FreelancerExperience)
admin.site.register(FreelancerEducation)
admin.site.register(FreelancerCertification)
admin.site.register(FreelancerProject)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'created_at', 'end_date')
    list_filter = ('status', 'created_at', 'end_date')
    search_fields = ('user__username', 'transaction_id')
    readonly_fields = ('created_at', 'updated_at', 'verified_at', 'end_date')
    actions = ['mark_as_verified', 'mark_as_rejected']

    def save_model(self, request, obj, form, change):
        """Handle saving individual subscription objects"""
        if change:  # Only process if this is an update
            old_obj = Subscription.objects.get(pk=obj.pk)
            if old_obj.status != obj.status and obj.status == 'active':
                # Deactivate previous active subscriptions
                Subscription.objects.filter(user=obj.user, status='active').exclude(pk=obj.pk).update(status='expired')
                
                # Send email notification
                try:
                    logger.info(f"Sending activation email for subscription {obj.id}")
                    result = send_subscription_activated_email(request, obj)
                    if result:
                        logger.info(f"Successfully sent activation email for subscription {obj.id}")
                    else:
                        logger.warning(f"Email sending returned False for subscription {obj.id}")
                except Exception as e:
                    logger.error(f"Failed to send email for subscription {obj.id}: {str(e)}", exc_info=True)
                    self.message_user(request, f"Warning: Could not send email: {str(e)}", level='warning')
        
        super().save_model(request, obj, form, change)

    def mark_as_verified(self, request, queryset):
        for subscription in queryset.filter(status='pending'):
            try:
                logger.info(f"Processing subscription {subscription.id} for user {subscription.user.email}")
                
                # Deactivate previous active subscriptions for this user
                Subscription.objects.filter(user=subscription.user, status='active').update(status='expired')
                subscription.verified_at = timezone.now()
                subscription.status = 'active'
                subscription.save()  # This should trigger the model's save logic
                
                # Send email notification
                try:
                    # Create a request object with the correct host
                    email_request = HttpRequest()
                    email_request.META['HTTP_HOST'] = 'thynkzone.eu.org'
                    email_request.scheme = 'https'
                    logger.info(f"Sending activation email for subscription {subscription.id}")
                    result = send_subscription_activated_email(email_request, subscription)
                    if result:
                        logger.info(f"Successfully sent activation email for subscription {subscription.id}")
                    else:
                        logger.warning(f"Email sending returned False for subscription {subscription.id}")
                except Exception as e:
                    logger.error(f"Failed to send email for subscription {subscription.id}: {str(e)}", exc_info=True)
                    self.message_user(request, f"Warning: Could not send email for subscription {subscription.id}: {str(e)}", level='warning')
                
                # Reload from DB to ensure values are set
                sub = Subscription.objects.get(pk=subscription.pk)
                logger.info(f"Successfully processed subscription {subscription.id}")
                
            except Exception as e:
                logger.error(f"Error processing subscription {subscription.id}: {str(e)}", exc_info=True)
                self.message_user(request, f"Error processing subscription {subscription.id}: {str(e)}", level='error')
                
        self.message_user(request, "Selected subscriptions marked as verified and activated.")
    mark_as_verified.short_description = "Mark selected subscriptions as Verified (Activate)"

    def mark_as_rejected(self, request, queryset):
        updated = queryset.filter(status='pending').update(status='rejected')
        self.message_user(request, f"{updated} subscriptions marked as rejected.")
    mark_as_rejected.short_description = "Mark selected subscriptions as Rejected"

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days', 'created_at')
    search_fields = ('name',)

