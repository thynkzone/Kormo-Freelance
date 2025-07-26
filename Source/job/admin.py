from django.contrib import admin
from django.utils import timezone
from django.http import HttpRequest
from accounts.utils import send_payment_verified_email
import logging

logger = logging.getLogger(__name__)

from .models import Category, Job, Skill, Review, Report, SavedJob, Proposal, Contract, Payment, RefundRequest, FreelancerPayout

admin.site.register(Category)
admin.site.register(Job)
admin.site.register(Skill)
admin.site.register(Review)
admin.site.register(Report)
admin.site.register(SavedJob)
admin.site.register(Proposal)
admin.site.register(Contract)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'amount', 'status', 'created_at', 'verified_at')
    list_filter = ('status', 'created_at', 'verified_at')
    search_fields = ('job__title', 'transaction_id', 'client_bkash_number')
    readonly_fields = ('amount', 'bkash_fee', 'total_amount')
    fieldsets = (
        ('Job Information', {
            'fields': ('job',)
        }),
        ('Payment Details', {
            'fields': ('amount', 'bkash_fee', 'total_amount', 'transaction_id', 'client_bkash_number')
        }),
        ('Status', {
            'fields': ('status', 'verified_at')
        }),
    )

    def save_model(self, request, obj, form, change):
        """Handle saving individual payment objects"""
        if change:  # Only process if this is an update
            old_obj = Payment.objects.get(pk=obj.pk)
            if old_obj.status != obj.status and obj.status == 'verified':
                # Update job payment status
                job = obj.job
                job.payment_verified = True
                job.save()
                
                # Send email notification
                try:
                    logger.info(f"Sending payment verification email for payment {obj.id}")
                    result = send_payment_verified_email(request, obj)
                    if result:
                        logger.info(f"Successfully sent payment verification email for payment {obj.id}")
                    else:
                        logger.warning(f"Email sending returned False for payment {obj.id}")
                except Exception as e:
                    logger.error(f"Failed to send email for payment {obj.id}: {str(e)}", exc_info=True)
                    self.message_user(request, f"Warning: Could not send email: {str(e)}", level='warning')
        
        super().save_model(request, obj, form, change)

@admin.register(RefundRequest)
class RefundRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'payment', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at', 'updated_at')
    search_fields = ('job__title', 'reason')
    readonly_fields = ('job', 'payment', 'reason', 'created_at', 'updated_at')
    fieldsets = (
        ('Job Information', {
            'fields': ('job', 'payment')
        }),
        ('Refund Details', {
            'fields': ('reason', 'status')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(FreelancerPayout)
class FreelancerPayoutAdmin(admin.ModelAdmin):
    list_display = ('id', 'job', 'freelancer_bkash_number', 'amount', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'created_at', 'completed_at')
    search_fields = ('job__title', 'freelancer_bkash_number', 'transaction_id')
    readonly_fields = ('amount', 'platform_fee', 'bkash_cashout_fee', 'total_amount')
    fieldsets = (
        ('Job Information', {
            'fields': ('job', 'payment')
        }),
        ('Payout Details', {
            'fields': ('amount', 'platform_fee', 'bkash_cashout_fee', 'total_amount', 'freelancer_bkash_number', 'transaction_id')
        }),
        ('Status', {
            'fields': ('status', 'completed_at')
        }),
    )