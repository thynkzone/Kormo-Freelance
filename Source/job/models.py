from django.contrib.auth.models import User
from django.db import models
from core.validators import validate_image_size, validate_image_type, validate_image_dimensions
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError
from decimal import Decimal
from django.urls import reverse

def create_job_notification(user, message, related_job=None, related_user=None):
    """Helper function to create notifications for job-related events"""
    from dashboard.views import create_notification
    return create_notification(
        user=user,
        notification_type='message',
        message=message,
        related_job=related_job,
        related_user=related_user
    )

class Category(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name

class Skill(models.Model):
    name = models.CharField(max_length=255, unique=True)
    
    def __str__(self):
        return self.name
    
    def __str__(self):
        return self.name

# Update Job model
class Job(models.Model):
    # Existing fields
    category = models.ForeignKey(Category, related_name='jobs', on_delete=models.CASCADE)
    title = models.CharField(max_length=30)
    description = models.TextField(null=True, blank=True)
    budget = models.IntegerField(
        validators=[
            MinValueValidator(300),
            MaxValueValidator(9999)
        ]
    )
    deadline = models.PositiveIntegerField(null=True, blank=True, help_text='Deadline in days')
    image = models.ImageField(
        upload_to='job_images',
        blank=True,
        null=True,
        validators=[validate_image_size, validate_image_type, validate_image_dimensions]
    )
    already_hired = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_jobs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    is_closed = models.BooleanField(default=False)
    
    # New fields
    skills = models.ManyToManyField(Skill, related_name='jobs')
    payment_status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('complete', 'Fully Paid')
    ], default='pending')
    hired_freelancer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='hired_jobs')
    completion_date = models.DateTimeField(null=True, blank=True)
    payment_verified = models.BooleanField(default=False)
    refund_requested = models.BooleanField(default=False)
    refund_accepted = models.BooleanField(default=False)
    
    class Meta:
        ordering = ('-created_at',)
        verbose_name_plural = 'Jobs'
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['already_hired']),
            models.Index(fields=['category']),
            models.Index(fields=['created_by']),
            models.Index(fields=['hired_freelancer']),
        ]
    
    def __str__(self):
        return self.title
        
    @property
    def active_contract(self):
        """Get the active contract for this job"""
        return self.contracts.filter(
            status__in=['pending', 'client_signed', 'freelancer_signed']
        ).order_by('-created_at').first()
        
    @property
    def has_client_review(self):
        if not self.hired_freelancer:
            return False
        return Review.objects.filter(
            job=self,
            reviewer=self.created_by,
            for_user=self.hired_freelancer
        ).exists()
        
    @property
    def has_freelancer_review(self):
        if not self.hired_freelancer:
            return False
        return Review.objects.filter(
            job=self,
            reviewer=self.hired_freelancer,
            for_user=self.created_by
        ).exists()
        
    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return None
            
        total_rating = sum(review.rating for review in reviews if review.rating is not None)
        review_count = sum(1 for review in reviews if review.rating is not None)
        
        if review_count == 0:
            return None
            
        return round(total_rating / review_count, 1)

    @property
    def client_average_rating(self):
        """Average rating given by the client to the freelancer"""
        client_review = self.reviews.filter(reviewer=self.created_by).first()
        if client_review:
            return client_review.rating
        return None

    @property
    def freelancer_average_rating(self):
        """Average rating given by the freelancer to the client"""
        freelancer_review = self.reviews.filter(reviewer=self.hired_freelancer).first()
        if freelancer_review:
            return freelancer_review.rating
        return None

    def calculate_payment_amount(self):
        """Calculate the total amount including bKash fees"""
        contract_amount = self.active_contract.amount if self.active_contract else 0
        bkash_fee = int(round(contract_amount * 0.0185, 0))  # 1.85% bKash fee
        return {
            'amount': contract_amount,
            'bkash_fee': bkash_fee,
            'total_amount': contract_amount + bkash_fee
        }

    def calculate_payout_amount(self):
        """Calculate the freelancer payout amount after fees"""
        contract_amount = self.active_contract.amount if self.active_contract else 0
        platform_fee = int(round(contract_amount * 0.15, 0))  # 15% platform fee
        bkash_cashout_fee = 5  # 5 BDT bKash cashout fee (as integer)
        return {
            'amount': contract_amount,
            'platform_fee': platform_fee,
            'bkash_cashout_fee': bkash_cashout_fee,
            'total_amount': contract_amount - platform_fee - bkash_cashout_fee
        }

class Review(models.Model):
    job = models.ForeignKey(Job, related_name='reviews', on_delete=models.CASCADE)
    reviewer = models.ForeignKey(User, related_name='given_reviews', on_delete=models.CASCADE)
    for_user = models.ForeignKey(User, related_name='received_reviews', on_delete=models.CASCADE)
    
    # Freelancer review criteria
    knowledge_depth = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3)
    fast_turnaround = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3)
    multiple_revisions = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3)
    quality_of_work = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3)
    responsiveness = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3)
    
    # Client review criteria
    communication = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3)
    timely_replies = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3)
    requirements_detail = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3)
    instant_feedback = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3)
    logical_revisions = models.IntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')], default=3)
    
    # Overall rating (calculated as average)
    rating = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('job', 'reviewer', 'for_user')
        
    def __str__(self):
        return f"Review by {self.reviewer} for {self.for_user} on {self.job}"
    
    def save(self, *args, **kwargs):
        # Calculate the average rating before saving
        if self.reviewer == self.job.created_by:  # Client reviewing freelancer
            total = sum([
                self.knowledge_depth,
                self.fast_turnaround,
                self.multiple_revisions,
                self.quality_of_work,
                self.responsiveness
            ])
            self.rating = round(total / 5.0, 1)
        else:  # Freelancer reviewing client
            total = sum([
                self.communication,
                self.timely_replies,
                self.requirements_detail,
                self.instant_feedback,
                self.logical_revisions
            ])
            self.rating = round(total / 5.0, 1)
        super().save(*args, **kwargs)

class Proposal(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('shortlisted', 'Shortlisted'),
        ('messaged', 'Messaged'),
        ('archived', 'Archived'),
        ('hired', 'Hired'),
        ('rejected', 'Rejected'),
    ]

    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='proposals')
    freelancer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='proposals')
    proposed_amount = models.IntegerField(
        validators=[
            MinValueValidator(300),
            MaxValueValidator(9999)
        ]
    )
    cover_letter = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['job', 'freelancer']  # One proposal per job per freelancer

    def __str__(self):
        return f"Proposal for {self.job.title} by {self.freelancer.username}"

class SavedJob(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'job')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} saved {self.job}"

class Report(models.Model):
    REPORT_TYPES = [
        ('job', 'Job'),
        ('freelancer', 'Freelancer'),
    ]
    
    REPORT_REASONS = [
        ('inappropriate_content', 'Inappropriate Content'),
        ('spam', 'Spam or Scam'),
        ('fake_profile', 'Fake Profile'),
        ('harassment', 'Harassment'),
        ('other', 'Other'),
    ]
    
    reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    reported_job = models.ForeignKey(Job, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    reported_freelancer = models.ForeignKey('freelancer.Freelancer', on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    reason = models.CharField(max_length=50, choices=REPORT_REASONS)
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        if self.report_type == 'job':
            return f"Report on Job: {self.reported_job.title}"
        return f"Report on Freelancer: {self.reported_freelancer.fullname}"
    
    def clean(self):
        if self.report_type == 'job' and not self.reported_job:
            raise ValidationError('Job must be specified for job reports')
        if self.report_type == 'freelancer' and not self.reported_freelancer:
            raise ValidationError('Freelancer must be specified for freelancer reports')

class Contract(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('client_signed', 'Client Signed'),
        ('freelancer_signed', 'Freelancer Signed'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='contracts')
    freelancer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='contracts_as_freelancer')
    amount = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    client_signature = models.CharField(max_length=255, blank=True, null=True)
    freelancer_signature = models.CharField(max_length=255, blank=True, null=True)
    client_signed_at = models.DateTimeField(null=True, blank=True)
    freelancer_signed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['job', 'freelancer']  # One contract per job per freelancer

    def __str__(self):
        return f"Contract for {self.job.title} between {self.freelancer.username}"

    @property
    def is_completed(self):
        return self.status == 'completed'

    @property
    def is_cancelled(self):
        return self.status == 'cancelled'

    @property
    def is_pending(self):
        return self.status == 'pending'

    @property
    def is_client_signed(self):
        return self.status == 'client_signed'

    @property
    def is_freelancer_signed(self):
        return self.status == 'freelancer_signed'

class Payment(models.Model):
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    bkash_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100)
    client_bkash_number = models.CharField(max_length=15)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending Verification'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='verified_payments')

    def __str__(self):
        return f"Payment for {self.job.title} - {self.transaction_id}"

    def save(self, *args, **kwargs):
        if self.pk:  # Only check for status changes on existing payments
            old_payment = Payment.objects.get(pk=self.pk)
            if old_payment.status != self.status:
                job_url = reverse('job:detail', kwargs={'pk': self.job.id})
                if self.status == 'verified':
                    # Notify client
                    message = f'<a href="{job_url}" class="hover:underline">Your payment of {self.amount} BDT for {self.job.title} has been verified.</a>'
                    create_job_notification(
                        user=self.job.created_by,
                        message=message,
                        related_job=self.job
                    )
                    # Only notify hired freelancer if payment is verified
                    if self.job.hired_freelancer:
                        message = f'<a href="{job_url}" class="hover:underline">Payment of {self.amount} BDT for {self.job.title} has been verified.</a>'
                        create_job_notification(
                            user=self.job.hired_freelancer,
                            message=message,
                            related_job=self.job
                        )
                elif self.status == 'rejected':
                    # Notify client
                    message = f'<a href="{job_url}" class="hover:underline">Your payment of {self.amount} BDT for {self.job.title} could not be verified. Please try again with a valid transaction ID.</a>'
                    create_job_notification(
                        user=self.job.created_by,
                        message=message,
                        related_job=self.job
                    )
                    # Also notify hired freelancer about payment rejection
                    if self.job.hired_freelancer:
                        message = f'<a href="{job_url}" class="hover:underline">Payment of {self.amount} BDT for {self.job.title} could not be verified. The client will need to try again.</a>'
                        create_job_notification(
                            user=self.job.hired_freelancer,
                            message=message,
                            related_job=self.job
                        )
        super().save(*args, **kwargs)

class RefundRequest(models.Model):
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='refund_requests')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refund_requests')
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending Investigation'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    handled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='handled_refunds')
    handled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Refund Request for {self.job.title}"

    def save(self, *args, **kwargs):
        if self.pk:  # Only check for status changes on existing refund requests
            old_refund = RefundRequest.objects.get(pk=self.pk)
            if old_refund.status != self.status:
                job_url = reverse('job:detail', kwargs={'pk': self.job.id})
                # Only notify client for refund status changes
                if self.status == 'accepted':
                    message = f'<a href="{job_url}" class="hover:underline">Your refund request for {self.job.title} has been accepted.</a>'
                    create_job_notification(
                        user=self.job.created_by,
                        message=message,
                        related_job=self.job
                    )
                elif self.status == 'rejected':
                    message = f'<a href="{job_url}" class="hover:underline">Your refund request for {self.job.title} has been rejected.</a>'
                    create_job_notification(
                        user=self.job.created_by,
                        message=message,
                        related_job=self.job
                    )
        super().save(*args, **kwargs)

class FreelancerPayout(models.Model):
    job = models.ForeignKey('Job', on_delete=models.CASCADE, related_name='payouts')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='payouts')
    freelancer_bkash_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2)
    bkash_cashout_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='pending')
    transaction_id = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payout for {self.job.title} - {self.freelancer_bkash_number}"