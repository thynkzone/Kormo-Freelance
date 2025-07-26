from django.contrib.auth import get_user_model
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator, RegexValidator
from core.validators import validate_image_size, validate_image_type, validate_image_dimensions, validate_url
from datetime import datetime, timedelta
from django.utils import timezone
from django.urls import reverse
from dashboard.views import create_notification
from django.db.models import Sum
from accounts.utils import send_subscription_activated_email
from decimal import Decimal
from django.conf import settings

User = get_user_model()

class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ('name',)

class SubscriptionPlan(models.Model):
    PLAN_CHOICES = [
        ('free', 'Free Plan'),
        ('member', 'Member Plan'),
        ('pro', 'Pro Plan'),
    ]
    
    name = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    proposal_limit = models.IntegerField(default=5)
    job_post_limit = models.IntegerField(default=5)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_days = models.IntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.get_name_display()

class Subscription(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey('SubscriptionPlan', on_delete=models.CASCADE, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s {self.plan.name} subscription"
    
    def save(self, *args, **kwargs):
        was_active = False
        if self.pk:
            old = Subscription.objects.filter(pk=self.pk).first()
            if old and old.status == 'active':
                was_active = True
        if self.status == 'active':
            if not self.verified_at:
                self.verified_at = timezone.now()
            if self.plan and self.verified_at:
                self.end_date = self.verified_at + timedelta(days=self.plan.duration_days)
            # Send notification if just activated
            if not was_active:
                try:
                    freelancer = getattr(self.user, 'freelancer', None)
                    if freelancer:
                        edit_url = reverse('freelancer:edit', kwargs={'pk': freelancer.pk})
                        message = f'<a href="{edit_url}" class="hover:underline">Your subscription has started.</a>'
                        create_notification(
                            user=self.user,
                            notification_type='message',
                            message=message
                        )
                        # Send email notification
                        from django.http import HttpRequest
                        request = HttpRequest()
                        request.META['HTTP_HOST'] = 'thynkzone.eu.org'
                        request.scheme = 'https'
                        send_subscription_activated_email(request, self)
                except Exception as e:
                    pass  # Optionally log the error
        elif self.status == 'rejected':
            try:
                plans_url = reverse('freelancer:plans')
                message = f'<a href="{plans_url}" class="hover:underline">Your payment could not be verified. Please try again with a valid transaction ID.</a>'
                create_notification(
                    user=self.user,
                    notification_type='message',
                    message=message
                )
            except Exception as e:
                pass  # Optionally log the error
        super().save(*args, **kwargs)

class Freelancer(models.Model):
    user = models.OneToOneField(User, related_name='freelancer', on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(Category, related_name='freelancers', on_delete=models.SET_NULL, null=True, blank=True)
    fullname = models.CharField(max_length=30)
    description = models.TextField(blank=True, null=True)
    hourly_rate = models.IntegerField(
        default=150,
        validators=[
            MinValueValidator(150),
            MaxValueValidator(9999)
        ]
    )
    profile_image = models.ImageField(
        upload_to='freelancer_images',
        blank=True,
        null=True,
        validators=[validate_image_size, validate_image_type, validate_image_dimensions]
    )
    is_not_available = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    bkash_account = models.CharField(max_length=11, blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    cv = models.FileField(upload_to='freelancer_cvs', blank=True, null=True)
    
    def __str__(self):
        return self.fullname

    def get_profile_completion(self):
        """Calculate profile completion percentage based on filled fields"""
        # Basic profile fields (40% of total)
        fields = [
            self.category,
            self.fullname,
            self.description,
            self.hourly_rate,
            self.profile_image,
        ]
        
        # Count basic profile fields
        filled_fields = sum(1 for field in fields if field)
        basic_completion = (filled_fields / len(fields)) * 40  # 40% weight
        
        # Skills section (10% of total)
        skills_count = self.skills.count()
        skills_completion = min((skills_count / 5) * 10, 10)  # 10% weight, max 5 skills
        
        # Experience section (10% of total)
        experience_completion = 10 if self.experiences.exists() else 0  # 10% weight
        
        # Education section (10% of total)
        education_count = min(self.education.count(), 3)  # Cap at 3 entries
        education_completion = 10 if education_count > 0 else 0  # 10% weight
        
        # Certifications section (10% of total)
        certifications_count = min(self.certifications.count(), 5)  # Cap at 5 entries
        certifications_completion = 10 if certifications_count > 0 else 0  # 10% weight
        
        # Projects section (20% of total)
        projects_count = min(self.projects.count(), 5)  # Cap at 5 entries
        projects_completion = 20 if projects_count > 0 else 0  # 20% weight
        
        # Calculate total completion
        total_completion = (
            basic_completion +
            skills_completion +
            experience_completion +
            education_completion +
            certifications_completion +
            projects_completion
        )
        
        return min(round(total_completion), 100)  # Ensure max is 100%

    def get_current_subscription(self):
        """Get the user's current active subscription, auto-expire if needed"""
        now = timezone.now()
        active_sub = Subscription.objects.filter(
            user=self.user,
            status='active'
        ).order_by('-created_at').first()
        if active_sub and active_sub.end_date and active_sub.end_date <= now:
            active_sub.status = 'expired'
            active_sub.save()
            return None
        if active_sub and (not active_sub.end_date or active_sub.end_date > now):
            return active_sub
        return None
    
    def get_proposal_limit(self):
        """Get the user's current proposal limit based on subscription"""
        subscription = self.get_current_subscription()
        if subscription:
            return subscription.plan.proposal_limit
        return 5  # Default free plan limit
    
    def get_job_post_limit(self):
        """Get the user's current job post limit based on subscription"""
        subscription = self.get_current_subscription()
        if subscription:
            return subscription.plan.job_post_limit
        return 5  # Default free plan limit
    
    def get_proposals_this_month(self):
        """Get count of proposals submitted this month"""
        first_day = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self.user.proposals.filter(created_at__gte=first_day).count()
    
    def get_jobs_posted_this_month(self):
        """Get count of jobs posted this month"""
        first_day = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return self.user.posted_jobs.filter(created_at__gte=first_day).count()

    def get_total_earnings(self):
        """Calculate total earnings from completed contracts of completed jobs"""
        from job.models import Contract
        
        contracts = Contract.objects.filter(
            freelancer=self.user,
            status='freelancer_signed',
            job__completion_date__isnull=False  # Only include completed jobs
        )
        
        total_earnings = 0
        for contract in contracts:
            platform_fee = int(round(contract.amount * 0.15, 0))  # 15% platform fee, rounded
            freelancer_amount = int(contract.amount - platform_fee)  # Amount after platform fee, ensure integer
            bkash_fee = int(round(freelancer_amount * 0.0185, 0))  # 1.85% bKash fee on freelancer amount, rounded
            freelancer_earnings = freelancer_amount + bkash_fee
            total_earnings += freelancer_earnings
            
        return total_earnings

    class Meta:
        ordering = ['-created_at']

class FreelancerSkill(models.Model):
    freelancer = models.ForeignKey(Freelancer, related_name='skills', on_delete=models.CASCADE)
    skill = models.ForeignKey('job.Skill', on_delete=models.CASCADE)
    level = models.CharField(max_length=20, choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert')
    ], default='intermediate')
    
    def __str__(self):
        return f"{self.skill.name} ({self.get_level_display()})"

    class Meta:
        unique_together = ('freelancer', 'skill')

class FreelancerExperience(models.Model):
    freelancer = models.ForeignKey(Freelancer, related_name='experiences', on_delete=models.CASCADE)
    company = models.CharField(max_length=255)
    position = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    current = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.position} at {self.company}"

class FreelancerEducation(models.Model):
    freelancer = models.ForeignKey(Freelancer, related_name='education', on_delete=models.CASCADE)
    institution = models.CharField(max_length=255)
    degree = models.CharField(max_length=255)
    field_of_study = models.CharField(max_length=255, blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    current = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.degree} from {self.institution}"

class FreelancerCertification(models.Model):
    freelancer = models.ForeignKey(Freelancer, related_name='certifications', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    issuing_organization = models.CharField(max_length=255)
    issue_date = models.DateField()
    expiry_date = models.DateField(blank=True, null=True)
    credential_id = models.CharField(max_length=100, blank=True, null=True)
    credential_url = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.name} from {self.issuing_organization}"

class FreelancerProject(models.Model):
    freelancer = models.ForeignKey(Freelancer, related_name='projects', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    url = models.URLField(max_length=200, blank=True, null=True, validators=[validate_url])
    image = models.ImageField(
        upload_to='project_images',
        blank=True,
        null=True,
        validators=[validate_image_size, validate_image_type, validate_image_dimensions]
    )
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    current = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title