from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.urls import reverse
from django.contrib import messages
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
import json
from django.core.exceptions import ValidationError, PermissionDenied
from django.core.paginator import Paginator
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)

from .forms import NewJobForm, EditJobForm, ReviewForm, ProposalForm, ContractForm, PaymentForm, RefundRequestForm, PayoutForm
from .models import Category, Job, Skill, Review, Proposal, SavedJob, Report, Contract, Payment, RefundRequest, FreelancerPayout
from django.contrib.auth.models import User
from conversation.models import Conversation
import datetime
from django.utils import timezone
from datetime import timedelta

from dashboard.views import create_notification
from django.views.decorators.http import require_POST, require_http_methods
from freelancer.models import Freelancer
from accounts.utils import send_contract_to_sign_email, send_contract_signed_email, send_job_reviewed_email, send_payment_verified_email, send_job_invite_email
from django.contrib.admin.views.decorators import user_passes_test

def jobs(request):
    query = request.GET.get('query', '')
    category_id = request.GET.get('category', 0)
    selected_skills = request.GET.getlist('skills', [])
    min_client_rating = request.GET.get('min_client_rating', 0)
    min_client_reviews = request.GET.get('min_client_reviews', 0)
    page = request.GET.get('page', 1)
    
    categories = Category.objects.all()
    all_skills = Skill.objects.all()
    jobs = Job.objects.filter(already_hired=False, is_closed=False, is_active=True)

    if category_id:
        jobs = jobs.filter(category_id=category_id)
    
    if selected_skills:
        jobs = jobs.filter(skills__id__in=selected_skills)

    if query:
        jobs = jobs.filter(
            Q(title__icontains=query) | 
            Q(description__icontains=query)
        ).distinct()
    
    # Filter by minimum client rating
    if min_client_rating:
        try:
            min_client_rating = float(min_client_rating)
            jobs = jobs.annotate(
                client_avg_rating=Avg('created_by__received_reviews__rating')
            ).filter(client_avg_rating__gte=min_client_rating)
        except ValueError:
            messages.error(request, "Invalid client rating value")
    
    # Filter by minimum client reviews
    if min_client_reviews:
        try:
            min_client_reviews = int(min_client_reviews)
            jobs = jobs.annotate(
                client_reviews_count=Count('created_by__received_reviews')
            ).filter(client_reviews_count__gte=min_client_reviews)
        except ValueError:
            messages.error(request, "Invalid client reviews value")
    
    # Order by creation date (newest first)
    jobs = jobs.annotate(proposals_count=Count('proposals')).order_by('-created_at')

    # Add proposal range label to each job
    for job in jobs:
        if job.proposals_count < 10:
            job.proposal_range = "<10 proposals"
        elif job.proposals_count < 20:
            job.proposal_range = "<20 proposals"
        elif job.proposals_count < 50:
            job.proposal_range = "<50 proposals"
        else:
            job.proposal_range = "50+ proposals"

    # Add saved_job_ids for the current user
    saved_job_ids = []
    if request.user.is_authenticated:
        saved_job_ids = list(map(int, SavedJob.objects.filter(user=request.user).values_list('job_id', flat=True)))

    # Implement pagination
    paginator = Paginator(jobs, 20)  # Show 20 jobs per page
    jobs_page = paginator.get_page(page)

    return render(request, 'job/jobs.html', {
        'jobs': jobs_page,
        'query': query,
        'categories': categories,
        'category_id': int(category_id),
        'all_skills': all_skills,
        'selected_skills': selected_skills,
        'min_client_rating': float(min_client_rating) if min_client_rating else 0,
        'min_client_reviews': int(min_client_reviews) if min_client_reviews else 0,
        'saved_job_ids': saved_job_ids,
    })

@login_required
def add_review(request, job_id, for_user_id):
    job = get_object_or_404(Job, id=job_id)
    for_user = get_object_or_404(User, id=for_user_id)
    
    # Check if user is authorized to review
    if request.user != job.created_by and request.user != job.hired_freelancer:
        messages.error(request, 'You are not authorized to review this job.')
        return redirect('job:detail', pk=job_id)
    
    # Check if user is reviewing the correct person
    if request.user == job.created_by and for_user != job.hired_freelancer:
        messages.error(request, 'You can only review the hired freelancer.')
        return redirect('job:detail', pk=job_id)
    elif request.user == job.hired_freelancer and for_user != job.created_by:
        messages.error(request, 'You can only review the client.')
        return redirect('job:detail', pk=job_id)
    
    # Check if user has already reviewed
    existing_review = Review.objects.filter(job=job, reviewer=request.user, for_user=for_user).first()
    
    if request.method == 'POST':
        if existing_review:
            # Update existing review
            form = ReviewForm(request.POST, instance=existing_review, job=job, reviewer=request.user)
        else:
            # Create new review
            form = ReviewForm(request.POST, job=job, reviewer=request.user)
        
        if form.is_valid():
            review = form.save(commit=False)
            review.job = job
            review.reviewer = request.user
            review.for_user = for_user
            review.save()
            
            # Create notification for the reviewed user
            create_notification(
                user=review.for_user,
                notification_type='review',
                message=f'Your job {job.title} has been reviewed by {request.user.username}, give your review to see what you got!',
                related_job=job,
                related_user=request.user
            )
            
            # Send email notification
            send_job_reviewed_email(request, review)
            
            messages.success(request, 'Your review has been submitted successfully.')
            return redirect('job:detail', pk=job_id)
    else:
        if existing_review:
            # Pre-fill form with existing review data
            form = ReviewForm(instance=existing_review, job=job, reviewer=request.user)
        else:
            # New review form
            form = ReviewForm(job=job, reviewer=request.user)
    
    return render(request, 'job/review.html', {
        'form': form,
        'job': job,
        'for_user': for_user,
        'review': existing_review,
        'reviewer': request.user
    })

@login_required
def mark_job_complete(request, pk):
    job = get_object_or_404(Job, pk=pk)
    
    # Only job creator can mark it complete
    if request.user != job.created_by:
        return redirect('job:detail', pk=pk)
    
    job.already_hired = True
    job.completion_date = datetime.date.today()
    job.save()
    
    return redirect('job:detail', pk=pk)

def detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    related_jobs = Job.objects.filter(category=job.category, already_hired=False).exclude(pk=pk)[0:3]

    # Get all conversations for the current user with freelancers
    all_conversations = None
    if request.user == job.created_by:
        all_conversations = Conversation.objects.filter(members=request.user)
    
    # Get client and freelancer reviews
    client_review = None
    freelancer_review = None
    
    if job.has_client_review:
        client_review = Review.objects.get(
            job=job,
            reviewer=job.created_by,
            for_user=job.hired_freelancer
        )
    
    if job.has_freelancer_review:
        freelancer_review = Review.objects.get(
            job=job,
            reviewer=job.hired_freelancer,
            for_user=job.created_by
        )
    
    # Add saved_job_ids for the current user
    saved_job_ids = []
    if request.user.is_authenticated:
        saved_job_ids = list(map(int, SavedJob.objects.filter(user=request.user).values_list('job_id', flat=True)))

    # Check for pending payments
    pending_payment = False
    has_rejected_payment = False
    if job.already_hired:
        pending_payment = Payment.objects.filter(job=job, status='pending').exists()
        has_rejected_payment = Payment.objects.filter(job=job, status='rejected').exists()
        # If there's a verified payment, update the job's payment_verified status
        if Payment.objects.filter(job=job, status='verified').exists():
            job.payment_verified = True
            job.save()

    # Check refund request status
    refund_request = job.refund_requests.first()
    if refund_request:
        if refund_request.status == 'accepted':
            job.refund_accepted = True
            job.refund_requested = False
            job.save()
        elif refund_request.status == 'rejected':
            job.refund_requested = False
            job.refund_accepted = False
            job.save()
        elif refund_request.status == 'pending':
            job.refund_requested = True
            job.refund_accepted = False
            job.save()

    return render(request, 'job/detail.html', {
        'job': job,
        'related_jobs': related_jobs,
        'all_conversations': all_conversations,
        'client_review': client_review,
        'freelancer_review': freelancer_review,
        'saved_job_ids': saved_job_ids,
        'pending_payment': pending_payment,
        'has_rejected_payment': has_rejected_payment,
    })

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Job, Skill
from .forms import NewJobForm, EditJobForm

@login_required
def new_job(request):
    # Enforce job post limit
    job_post_limit = 5
    jobs_posted_this_month = 0
    if hasattr(request.user, 'freelancer') and request.user.freelancer:
        jobs_posted_this_month = request.user.freelancer.get_jobs_posted_this_month()
        job_post_limit = request.user.freelancer.get_job_post_limit()
    else:
        # For users without a freelancer profile (e.g. companies), count jobs posted this month
        first_day = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        jobs_posted_this_month = Job.objects.filter(created_by=request.user, created_at__gte=first_day).count()
    if jobs_posted_this_month >= job_post_limit:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': {'__all__': [f'You have reached your monthly job post limit ({job_post_limit}). Upgrade your plan to post more jobs.']}
            }, status=400)
        messages.error(request, f'You have reached your monthly job post limit ({job_post_limit}). Upgrade your plan to post more jobs.')
        return redirect('job:jobs')

    if request.method == 'POST':
        # Check if this is an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # If it's not an AJAX request, return an error
        if not is_ajax:
            return JsonResponse({
                'success': False,
                'errors': {'__all__': ['Invalid request type']}
            }, status=400)
            
        form = NewJobForm(request.POST, request.FILES)
        
        if form.is_valid():
            try:
                job = form.save(commit=False)
                job.created_by = request.user
                job.save()  # Save the job first
                
                # Save many-to-many fields (skills)
                form.save_m2m()
                
                messages.success(request, 'Job posted successfully!')
                
                return JsonResponse({
                    'success': True,
                    'redirect_url': reverse('job:detail', kwargs={'pk': job.id})
                })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'errors': {'__all__': [str(e)]}
                }, status=400)
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    else:
        form = NewJobForm()
    
    categories = Category.objects.all()
    skills = Skill.objects.all()
    
    context = {
        'form': form,
        'categories': categories,
        'skills': skills,
    }
    
    return render(request, 'job/form.html', context)

@login_required
def edit(request, pk):
    job = get_object_or_404(Job, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        form = EditJobForm(request.POST, request.FILES, instance=job)
        
        if form.is_valid():
            try:
                job = form.save(commit=False)
                
                # Handle image field
                if 'image-clear' in request.POST and request.POST['image-clear'] == 'true':
                    # User wants to remove the image
                    job.image = None
                elif 'image' not in request.FILES and job.image:
                    # No new image uploaded and there's an existing image - keep it
                    form.cleaned_data['image'] = job.image
                # If new image is uploaded, it's automatically handled by form.save()
                
                job.save()
                form.save_m2m()  # Save many-to-many fields (skills)
                
                messages.success(request, 'Job updated successfully!')
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'redirect_url': reverse('job:detail', kwargs={'pk': job.id})
                    })
                return redirect('job:detail', pk=job.id)
                
            except Exception as e:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'errors': {'__all__': [str(e)]}
                    }, status=400)
                messages.error(request, f"Error updating job: {str(e)}")
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
            messages.error(request, "Please correct the errors below.")
    else:
        form = EditJobForm(instance=job)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'errors': {'__all__': ['Invalid request method']}
        }, status=400)
    
    return render(request, 'job/form.html', {
        'form': form,
        'job': job,
        'title': f'Edit {job.title}'
    })

@login_required
def delete(request, pk):
    job = get_object_or_404(Job, pk=pk, created_by=request.user)
    job.delete()

    return redirect('dashboard:index')

@login_required
def submit_proposal(request, pk):
    job = get_object_or_404(Job, pk=pk)
    
    # Check if job is closed or already hired
    if job.is_closed or job.already_hired:
        messages.error(request, 'This job is no longer accepting proposals.')
        return redirect('job:detail', pk=pk)
    
    # Check if user already submitted a proposal
    existing_proposal = Proposal.objects.filter(job=job, freelancer=request.user).first()
    if existing_proposal:
        messages.error(request, 'You have already submitted a proposal for this job.')
        return redirect('job:detail', pk=pk)
    
    # Enforce proposal limit
    try:
        freelancer_profile = request.user.freelancer
        proposals_this_month = freelancer_profile.get_proposals_this_month()
        proposal_limit = freelancer_profile.get_proposal_limit()
        if proposals_this_month >= proposal_limit:
            messages.error(request, f'You have reached your monthly proposal limit ({proposal_limit}). Upgrade your plan to submit more proposals.')
            return redirect('job:detail', pk=pk)
    except Exception:
        # If user has no freelancer profile, do not allow proposal
        messages.error(request, 'You must have a freelancer profile to submit proposals.')
        return redirect('job:detail', pk=pk)

    if request.method == 'POST':
        form = ProposalForm(request.POST)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.job = job
            proposal.freelancer = request.user
            proposal.save()
            
            # Create notification for the job owner
            create_notification(
                user=job.created_by,
                notification_type='proposal',
                message=f'New proposal for {job.title}',
                related_job=job,
                related_user=request.user
            )
            
            messages.success(request, 'Your proposal has been submitted successfully!')
            return redirect('job:detail', pk=pk)
    else:
        form = ProposalForm(initial={'proposed_amount': job.budget})
    
    return render(request, 'job/submit_proposal.html', {
        'form': form,
        'job': job
    })

def get_remaining_cancel_time(contract):
    """Calculate remaining time before contract can be cancelled"""
    if contract.status != 'client_signed':
        return None
    
    time_since_signed = timezone.now() - contract.client_signed_at
    hours_remaining = 24 - time_since_signed.total_seconds() / 3600
    
    if hours_remaining <= 0:
        return 0
    return round(hours_remaining, 1)

@login_required
def cancel_contract(request, job_id, freelancer_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is the job creator
    if request.user != job.created_by:
        raise PermissionDenied("You don't have permission to cancel this contract.")
    
    contract = get_object_or_404(Contract, job=job, freelancer_id=freelancer_id)
    
    # Check if contract is in client_signed state
    if contract.status != 'client_signed':
        messages.error(request, 'This contract cannot be cancelled.')
        return redirect('job:proposals', job_id=job.id)
    
    # Check if 24 hours have passed since client signed
    time_since_signed = timezone.now() - contract.client_signed_at
    if time_since_signed < timedelta(hours=24):
        hours_remaining = round(24 - time_since_signed.total_seconds() / 3600, 1)
        messages.error(request, f'You can cancel this contract in {hours_remaining} hours.')
        return redirect('job:proposals', job_id=job.id)
    
    if request.method == 'POST':
        contract.status = 'cancelled'
        contract.save()
        
        # Create notification for freelancer
        create_notification(
            user=contract.freelancer,
            notification_type='contract_cancelled',
            message=f'The contract for "{job.title}" has been cancelled by the client.',
            related_job=job,
            related_user=request.user
        )
        
        messages.success(request, 'Contract has been cancelled successfully.')
        return redirect('job:proposals', job_id=job.id)
    
    return render(request, 'job/cancel_contract.html', {
        'job': job,
        'contract': contract,
        'freelancer': contract.freelancer
    })

@login_required
def proposals(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is the job creator
    if request.user != job.created_by:
        raise PermissionDenied("You don't have permission to view these proposals.")
    
    # Get all proposals for this job
    proposals = Proposal.objects.filter(job=job).select_related('freelancer', 'freelancer__freelancer')
    
    # Get all conversations where the client is a member
    client_conversations = Conversation.objects.filter(members=request.user)
    # Get all freelancers who are members of these conversations
    messaged_freelancers = User.objects.filter(
        conversations__in=client_conversations
    ).exclude(id=request.user.id).distinct()
    
    # Get counts for different statuses BEFORE filtering
    total_count = proposals.count()
    shortlisted_count = proposals.filter(status='shortlisted').count()
    messaged_count = proposals.filter(freelancer__in=messaged_freelancers).count()
    archived_count = proposals.filter(status='archived').count()
    
    # Get current status filter
    current_status = request.GET.get('status', 'all')
    if current_status != 'all':
        if current_status == 'messaged':
            proposals = proposals.filter(freelancer__in=messaged_freelancers)
        else:
            proposals = proposals.filter(status=current_status)
    
    # Get current sort
    current_sort = request.GET.get('sort', 'best_match')
    if current_sort == 'newest':
        proposals = proposals.order_by('-created_at')
    elif current_sort == 'oldest':
        proposals = proposals.order_by('created_at')
    elif current_sort == 'lowest_bid':
        proposals = proposals.order_by('proposed_amount')
    elif current_sort == 'highest_bid':
        proposals = proposals.order_by('-proposed_amount')
    
    # Get search query
    search_query = request.GET.get('q', '')
    if search_query:
        proposals = proposals.filter(
            Q(freelancer__username__icontains=search_query) |
            Q(freelancer__freelancer__fullname__icontains=search_query) |
            Q(cover_letter__icontains=search_query)
        )
    
    # Get contract counts and status for each proposal
    for proposal in proposals:
        # Get all contracts for this proposal
        contracts = Contract.objects.filter(job=job, freelancer=proposal.freelancer)
        proposal.contract_count = contracts.count()
        
        # Get the most recent active contract
        proposal.active_contract = contracts.filter(
            status__in=['pending', 'client_signed', 'freelancer_signed']
        ).order_by('-created_at').first()
        
        # Add remaining time for cancellation if contract is client_signed
        if proposal.active_contract and proposal.active_contract.status == 'client_signed':
            proposal.remaining_cancel_time = get_remaining_cancel_time(proposal.active_contract)
        
        # Mark proposal as messaged if freelancer is in conversations
        proposal.is_messaged = proposal.freelancer in messaged_freelancers
        
        # Get completed jobs count for each freelancer
        proposal.freelancer_completed_jobs = Job.objects.filter(
            hired_freelancer=proposal.freelancer,
            already_hired=True
        ).count()
    
    context = {
        'job': job,
        'proposals': proposals,
        'total_count': total_count,
        'shortlisted_count': shortlisted_count,
        'messaged_count': messaged_count,
        'archived_count': archived_count,
        'current_status': current_status,
        'current_sort': current_sort,
        'search_query': search_query,
    }
    
    return render(request, 'job/proposals.html', context)

@login_required
def hire_freelancer(request, job_id, freelancer_id):
    job = get_object_or_404(Job, id=job_id, created_by=request.user)
    freelancer = get_object_or_404(User, id=freelancer_id)
    
    # Check if the freelancer has a proposal for this job
    proposal = get_object_or_404(Proposal, job=job, freelancer=freelancer)
    
    # Check if a contract already exists
    if Contract.objects.filter(job=job, freelancer=freelancer).exists():
        messages.error(request, 'A contract already exists for this job and freelancer.')
        return redirect('job:detail', pk=job_id)
    
    # Redirect to contract creation
    return redirect('job:create_contract', job_id=job_id, freelancer_id=freelancer_id)

@login_required
def my_proposals(request):
    # Get status filter from query params
    status = request.GET.get('status', 'all')
    search_query = request.GET.get('q', '')
    
    # Base queryset for user's proposals
    proposals = Proposal.objects.filter(freelancer=request.user).select_related('job', 'job__category', 'job__created_by')
    
    # Get pending contracts that need freelancer's signature
    pending_contracts = Contract.objects.filter(
        freelancer=request.user,
        status='client_signed'
    ).select_related('job', 'job__created_by')
    
    # Apply status filter
    if status != 'all':
        proposals = proposals.filter(status=status)
    
    # Apply search filter
    if search_query:
        proposals = proposals.filter(
            Q(job__title__icontains=search_query) |
            Q(job__description__icontains=search_query) |
            Q(cover_letter__icontains=search_query)
        )
    
    # Get counts for each status
    total_count = Proposal.objects.filter(freelancer=request.user).count()
    shortlisted_count = Proposal.objects.filter(freelancer=request.user, status='shortlisted').count()
    messaged_count = Proposal.objects.filter(freelancer=request.user, status='messaged').count()
    archived_count = Proposal.objects.filter(freelancer=request.user, status='archived').count()
    
    context = {
        'proposals': proposals,
        'pending_contracts': pending_contracts,
        'current_status': status,
        'search_query': search_query,
        'total_count': total_count,
        'shortlisted_count': shortlisted_count,
        'messaged_count': messaged_count,
        'archived_count': archived_count,
    }
    
    return render(request, 'job/my_proposals.html', context)

@login_required
def social_media_image(request, pk):
    job = get_object_or_404(Job, pk=pk)
    
    # Image size
    width, height = 800, 800
    bg_color = (245, 247, 250)  # Light background
    card_color = (255, 255, 255)
    shadow_color = (220, 224, 230)
    green_color = (50, 205, 50)  # #32CD32
    text_color = (30, 32, 34)
    pill_bg = (245, 247, 250)
    pill_border = (220, 224, 230)
    salary_color = green_color
    brand_color = green_color
    company_color = (120, 120, 120)
    
    # Create base image
    image = Image.new('RGBA', (width, height), bg_color + (255,))
    draw = ImageDraw.Draw(image)
    
    # Fonts
    try:
        headline_font = ImageFont.truetype("arialbd.ttf", 54)
        subhead_font = ImageFont.truetype("arial.ttf", 28)
        title_font = ImageFont.truetype("arialbd.ttf", 44)
        company_font = ImageFont.truetype("arial.ttf", 28)
        pill_font = ImageFont.truetype("arial.ttf", 26)
        label_font = ImageFont.truetype("arialbd.ttf", 26)
        salary_font = ImageFont.truetype("arialbd.ttf", 36)
        info_font = ImageFont.truetype("arial.ttf", 24)
        brand_font = ImageFont.truetype("arialbd.ttf", 28)
    except:
        headline_font = ImageFont.load_default()
        subhead_font = ImageFont.load_default()
        title_font = ImageFont.load_default()
        company_font = ImageFont.load_default()
        pill_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        salary_font = ImageFont.load_default()
        info_font = ImageFont.load_default()
        brand_font = ImageFont.load_default()
    
    # Card dimensions
    card_w, card_h = 700, 600
    card_x = (width - card_w) // 2
    card_y = 120
    card_radius = 40
    shadow_offset = 10
    
    # Draw card shadow
    shadow_box = (card_x + shadow_offset, card_y + shadow_offset, card_x + card_w + shadow_offset, card_y + card_h + shadow_offset)
    draw.rounded_rectangle(shadow_box, card_radius, fill=shadow_color + (120,))
    
    # Draw card (rounded rectangle)
    draw.rounded_rectangle((card_x, card_y, card_x+card_w, card_y+card_h), card_radius, fill=card_color)
    
    # Draw headline
    headline = "HIRING!"
    headline_bbox = draw.textbbox((0,0), headline, font=headline_font)
    headline_w = headline_bbox[2] - headline_bbox[0]
    draw.text(((width-headline_w)//2, 40), headline, font=headline_font, fill=green_color)
    
    # Draw subheadline
    subheadline = "Project Based Part-Time Remote Job"
    subhead_bbox = draw.textbbox((0,0), subheadline, font=subhead_font)
    subhead_w = subhead_bbox[2] - subhead_bbox[0]
    subhead_y = 120 + headline_bbox[3] - headline_bbox[1] + 10
    draw.text(((width-subhead_w)//2, subhead_y), subheadline, font=subhead_font, fill=company_color)
    
    # Card content padding
    pad_x = card_x + 48
    pad_y = card_y + 130  # Increased gap below subheadline
    
    # Company logo (if available)
    logo_size = 64
    logo_pad = 8
    logo_x = pad_x
    logo_y = pad_y
    if hasattr(job, 'company_logo') and job.company_logo:
        try:
            from PIL import Image as PILImage
            import requests
            from io import BytesIO as PILBytesIO
            logo_img = PILImage.open(PILBytesIO(requests.get(job.company_logo.url).content)).convert('RGBA')
            logo_img = logo_img.resize((logo_size, logo_size))
            image.paste(logo_img, (logo_x, logo_y), logo_img)
            text_x = logo_x + logo_size + logo_pad
        except:
            text_x = pad_x
    else:
        text_x = pad_x
    
    # Job title
    job_title = job.title
    title_bbox = draw.textbbox((0,0), job_title, font=title_font)
    draw.text((text_x, pad_y), job_title, font=title_font, fill=green_color)
    
    # Company name
    company = job.company_name if hasattr(job, 'company_name') and job.company_name else (job.created_by.get_full_name() or job.created_by.username)
    company_bbox = draw.textbbox((0,0), company, font=company_font)
    draw.text((text_x, pad_y + title_bbox[3] - title_bbox[1] + 6), company, font=company_font, fill=company_color)
    
    # Pills (job type, remote, exp, education, location, up to 3 skills)
    pills = []
    if hasattr(job, 'job_type') and job.job_type:
        pills.append(str(job.job_type))
    if hasattr(job, 'is_remote') and job.is_remote:
        pills.append("Remote")
    if hasattr(job, 'experience') and job.experience:
        pills.append(str(job.experience))
    if hasattr(job, 'education') and job.education:
        pills.append(str(job.education))
    if hasattr(job, 'location') and job.location:
        pills.append(str(job.location))
    # Always add up to 5 skills
    skills = [s.name for s in job.skills.all()[:5]]
    for skill in skills:
        pills.append(skill)
    
    # Pills layout: wrap to next line if needed
    pill_y = pad_y + max(title_bbox[3] - title_bbox[1], logo_size) + company_bbox[3] - company_bbox[1] + 32
    pill_x = pad_x
    pill_pad_x = 22
    pill_pad_y = 10
    pill_gap = 18
    max_pill_row_w = card_w - 2 * (pad_x - card_x)
    row_pills = []
    row_w = 0
    # Add 'Skills Required' label above skills
    skills_label = "Skills Required"
    skills_label_bbox = draw.textbbox((0,0), skills_label, font=label_font)
    draw.text((pad_x, pill_y), skills_label, font=label_font, fill=text_color)
    pill_y += skills_label_bbox[3] - skills_label_bbox[1] + 10
    for pill in pills:
        pill_bbox = draw.textbbox((0,0), pill, font=pill_font)
        pill_w = pill_bbox[2] - pill_bbox[0] + pill_pad_x*2
        pill_h = pill_bbox[3] - pill_bbox[1] + pill_pad_y*2
        if row_w + pill_w > max_pill_row_w and row_pills:
            # Draw current row
            px = pad_x
            for p, pw, ph in row_pills:
                draw.rounded_rectangle((px, pill_y, px+pw, pill_y+ph), 18, fill=pill_bg, outline=pill_border, width=2)
                draw.text((px+pill_pad_x, pill_y+pill_pad_y-2), p, font=pill_font, fill=text_color)
                px += pw + pill_gap
            pill_y += pill_h + 10
            row_pills = []
            row_w = 0
        row_pills.append((pill, pill_w, pill_h))
        row_w += pill_w + pill_gap
    # Draw last row
    px = pad_x
    for p, pw, ph in row_pills:
        draw.rounded_rectangle((px, pill_y, px+pw, pill_y+ph), 18, fill=pill_bg, outline=pill_border, width=2)
        draw.text((px+pill_pad_x, pill_y+pill_pad_y-2), p, font=pill_font, fill=text_color)
        px += pw + pill_gap
    pill_y += pill_h + 30
    
    # Payment label above salary
    payment_label = "Payment"
    payment_label_bbox = draw.textbbox((0,0), payment_label, font=label_font)
    salary_x = pad_x
    salary_y = card_y + card_h - 90
    draw.text((salary_x, salary_y - payment_label_bbox[3] + payment_label_bbox[1] - 10), payment_label, font=label_font, fill=text_color)
    
    # Salary (no symbol before amount)
    salary = f"{job.budget:,} BDT" if hasattr(job, 'budget') else "Salary: N/A"
    salary_bbox = draw.textbbox((0,0), salary, font=salary_font)
    draw.text((salary_x, salary_y), salary, font=salary_font, fill=green_color)
    
    # "Project Posted:" and date on the same line (right side)
    posted_label = "Project Posted: "
    date_str = job.created_at.strftime('%d %b, %Y') if hasattr(job, 'created_at') else ""
    full_text = posted_label + date_str
    full_text_bbox = draw.textbbox((0,0), full_text, font=info_font)
    text_x = card_x + card_w - (full_text_bbox[2] - full_text_bbox[0]) - 40
    text_y = salary_y
    draw.text((text_x, text_y), full_text, font=info_font, fill=company_color)
    
    # Deadline (below the "Project Posted: date" line)
    if job.deadline:
        deadline_str = f"Deadline: {job.deadline} days"
        deadline_bbox = draw.textbbox((0,0), deadline_str, font=info_font)
        deadline_x = card_x + card_w - (deadline_bbox[2] - deadline_bbox[0]) - 40
        deadline_y = text_y + full_text_bbox[3] - full_text_bbox[1] + 5
        draw.text((deadline_x, deadline_y), deadline_str, font=info_font, fill=company_color)
    
    # Branding at the bottom (Kormo, no emoji)
    brand = "Kormo"
    brand_bbox = draw.textbbox((0,0), brand, font=brand_font)
    brand_x = (width - (brand_bbox[2] - brand_bbox[0])) // 2
    brand_y = height - 60
    draw.text((brand_x, brand_y), brand, font=brand_font, fill=green_color)
    
    # Save the image
    out = Image.new('RGB', (width, height), bg_color)
    out.paste(image, (0,0), image)
    buffer = BytesIO()
    out.save(buffer, format='PNG')
    image_data = buffer.getvalue()
    response = HttpResponse(image_data, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="job_{pk}_social.png"'
    return response

@login_required
def create_proposal(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user already has a proposal for this job
    if Proposal.objects.filter(job=job, freelancer=request.user).exists():
        messages.error(request, 'You have already submitted a proposal for this job.')
        return redirect('job:detail', job_id=job_id)
    
    if request.method == 'POST':
        form = ProposalForm(request.POST)
        if form.is_valid():
            proposal = form.save(commit=False)
            proposal.job = job
            proposal.freelancer = request.user
            proposal.save()
            
            # Create notification for the job owner
            create_notification(
                user=job.created_by,
                notification_type='proposal',
                message=f'New proposal for {job.title}',
                related_job=job,
                related_user=request.user
            )
            
            messages.success(request, 'Your proposal has been submitted successfully!')
            return redirect('job:detail', job_id=job_id)
    else:
        form = ProposalForm()
    
    return render(request, 'job/create_proposal.html', {
        'form': form,
        'job': job
    })

@login_required
def create_review(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is authorized to review
    if request.user != job.created_by and request.user != job.hired_freelancer:
        messages.error(request, 'You are not authorized to review this job.')
        return redirect('job:detail', job_id=job_id)
    
    # Check if user has already reviewed
    if Review.objects.filter(job=job, reviewer=request.user).exists():
        messages.error(request, 'You have already reviewed this job.')
        return redirect('job:detail', job_id=job_id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.job = job
            review.reviewer = request.user
            review.for_user = job.hired_freelancer if request.user == job.created_by else job.created_by
            review.save()
            
            # Create notification for the reviewed user
            create_notification(
                user=review.for_user,
                notification_type='review',
                message=f'Your job {job.title} has been reviewed by {request.user.username}, give your review to see what you got!',
                related_job=job,
                related_user=request.user
            )
            
            messages.success(request, 'Your review has been submitted successfully!')
            return redirect('job:detail', job_id=job_id)
    else:
        form = ReviewForm()
    
    return render(request, 'job/create_review.html', {
        'form': form,
        'job': job
    })

@login_required
def invite_to_job(request, job_id, freelancer_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'})
    
    job = get_object_or_404(Job, id=job_id, created_by=request.user)
    freelancer = get_object_or_404(User, id=freelancer_id)
    
    # Check if job is already hired
    if job.already_hired:
        return JsonResponse({'success': False, 'message': 'This job is already hired'})
    
    # Check if freelancer already has a proposal
    if Proposal.objects.filter(job=job, freelancer=freelancer).exists():
        return JsonResponse({'success': False, 'message': 'Freelancer already has a proposal for this job'})
    
    # Create notification for the freelancer
    create_notification(
        user=freelancer,
        notification_type='proposal',
        message=f'You\'ve been invited to apply for the job: {job.title}',
        related_job=job,
        related_user=request.user
    )
    
    # Send email notification
    send_job_invite_email(request, job, freelancer)
    
    return JsonResponse({'success': True, 'message': 'Invitation sent successfully'})

@login_required
@require_POST
def save_job(request, job_id):
    job = get_object_or_404(Job, pk=job_id)
    obj, created = SavedJob.objects.get_or_create(user=request.user, job=job)
    return JsonResponse({'success': True, 'saved': True})

@login_required
@require_POST
def unsave_job(request, job_id):
    try:
        SavedJob.objects.get(user=request.user, job_id=job_id).delete()
        return JsonResponse({'success': True, 'saved': False})
    except SavedJob.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'})

@require_http_methods(["POST"])
@login_required
def submit_report(request):
    try:
        data = json.loads(request.body)
        report_type = data.get('report_type')
        report_id = data.get('report_id')
        reason = data.get('reason')
        explanation = data.get('explanation')
        
        if not all([report_type, report_id, reason, explanation]):
            return JsonResponse({'success': False, 'error': 'All fields are required'})
        
        report = Report(
            reporter=request.user,
            report_type=report_type,
            reason=reason,
            explanation=explanation
        )
        
        if report_type == 'job':
            job = Job.objects.get(pk=report_id)
            if job.created_by == request.user:
                return JsonResponse({'success': False, 'error': "You can't report your own job."})
            # Prevent duplicate job report
            if Report.objects.filter(reporter=request.user, report_type='job', reported_job_id=report_id).exists():
                return JsonResponse({'success': False, 'error': "You have already reported this job."})
            report.reported_job_id = report_id
        else:
            # Prevent duplicate freelancer report
            if Report.objects.filter(reporter=request.user, report_type='freelancer', reported_freelancer_id=report_id).exists():
                return JsonResponse({'success': False, 'error': "You have already reported this profile."})
            report.reported_freelancer_id = report_id
        
        report.full_clean()  # Validate the model
        report.save()
        
        return JsonResponse({'success': True})
    except ValidationError as e:
        return JsonResponse({'success': False, 'error': str(e)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': 'An error occurred while submitting your report'})

@login_required
def create_contract(request, job_id, freelancer_id):
    job = get_object_or_404(Job, id=job_id, created_by=request.user)
    freelancer = get_object_or_404(User, id=freelancer_id)
    
    # Check if job is already hired
    if job.already_hired:
        messages.error(request, 'This job is already hired')
        return redirect('job:detail', pk=job_id)
    
    # Get the proposal
    proposal = get_object_or_404(Proposal, job=job, freelancer=freelancer)
    
    # Check if a contract already exists
    existing_contract = Contract.objects.filter(job=job, freelancer=freelancer).first()
    if existing_contract:
        if existing_contract.status == 'client_signed':
            messages.info(request, 'Contract already exists and is waiting for freelancer signature.')
            return redirect('job:contract', job_id=job_id, freelancer_id=freelancer_id)
        elif existing_contract.status == 'freelancer_signed':
            messages.info(request, 'Contract has already been signed by both parties.')
            return redirect('job:detail', pk=job_id)
        elif existing_contract.status == 'cancelled':
            messages.info(request, 'Previous contract was cancelled. Creating a new one.')
            existing_contract.delete()
    
    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid():
            contract = form.save(commit=False)
            contract.job = job
            contract.freelancer = freelancer
            contract.amount = form.cleaned_data.get('amount', proposal.proposed_amount)
            contract.client_signature = form.cleaned_data['signature']
            contract.client_signed_at = timezone.now()
            contract.status = 'client_signed'
            contract.save()
            
            # Create notification for the freelancer
            create_notification(
                user=freelancer,
                notification_type='contract',
                message=f'You have a new contract to sign for {job.title}',
                related_job=job,
                related_user=request.user
            )
            
            # Send email notification
            send_contract_to_sign_email(request, contract)
            
            messages.success(request, 'Contract created successfully. Waiting for freelancer to sign.')
            return redirect('job:contract', job_id=job_id, freelancer_id=freelancer_id)
    else:
        form = ContractForm(initial={'amount': proposal.proposed_amount})
    
    return render(request, 'job/contract.html', {
        'job': job,
        'freelancer': freelancer,
        'form': form,
        'is_client': True
    })

@login_required
def sign_contract(request, job_id, freelancer_id):
    contract = get_object_or_404(Contract, job_id=job_id, freelancer_id=freelancer_id)
    
    if request.user != contract.freelancer:
        raise PermissionDenied
    
    if contract.status != 'client_signed':
        messages.error(request, 'This contract is not ready for your signature')
        return redirect('job:detail', pk=job_id)
    
    if request.method == 'POST':
        form = ContractForm(request.POST)
        if form.is_valid():
            contract.freelancer_signature = form.cleaned_data['signature']
            contract.freelancer_signed_at = timezone.now()
            contract.status = 'freelancer_signed'
            contract.save()
            # Update job status
            job = contract.job
            job.hired_freelancer = contract.freelancer
            job.already_hired = True
            job.save()
            # Update proposal status
            proposal = get_object_or_404(Proposal, job=job, freelancer=contract.freelancer)
            proposal.status = 'hired'
            proposal.save()
            # Create notification for the client
            create_notification(
                user=job.created_by,
                notification_type='contract',
                message=f'Freelancer has signed the contract for {job.title}',
                related_job=job,
                related_user=request.user
            )
            # Send email notification
            try:
                logger.info(f"Attempting to send contract signed email for contract {contract.id}")
                send_contract_signed_email(request, contract, request.user)
                logger.info(f"Contract signed email sent successfully for contract {contract.id}")
            except Exception as e:
                logger.error(f"Failed to send contract signed email for contract {contract.id}: {str(e)}")
                messages.error(request, 'Contract signed but failed to send email notification')
            messages.success(request, 'Contract signed successfully.')
            return redirect('job:detail', pk=job_id)
    else:
        form = ContractForm()
    
    return render(request, 'job/contract.html', {
        'job': contract.job,
        'freelancer': contract.freelancer,
        'form': form,
        'is_client': False
    })

@login_required
def view_contract(request, job_id, freelancer_id):
    job = get_object_or_404(Job, id=job_id)
    freelancer = get_object_or_404(User, id=freelancer_id)
    
    # Get bKash accounts using the same method as the template
    freelancer_bkash = freelancer.freelancer.bkash_account if hasattr(freelancer, 'freelancer') else None
    client_bkash = job.created_by.freelancer.bkash_account if hasattr(job.created_by, 'freelancer') else None
    
    # Check if the user is either the client or freelancer
    if request.user not in [job.created_by, freelancer]:
        raise PermissionDenied
    
    contract = get_object_or_404(Contract, job=job, freelancer=freelancer)
    is_client = request.user == job.created_by
    
    # Ensure contract amount is set from proposal if not already set
    if not contract.amount:
        proposal = get_object_or_404(Proposal, job=job, freelancer=freelancer)
        contract.amount = proposal.proposed_amount
        contract.save()
    
    # Prevent signing if bkash_account is not set
    bkash_required_error = None
    if request.method == 'POST':
        form = ContractForm(request.POST, instance=contract)
        if is_client and contract.status == 'pending':
            if not client_bkash:
                bkash_required_error = 'You must add your bKash account number in your profile before signing the contract.'
            elif form.is_valid():
                contract.client_signature = form.cleaned_data['signature']
                contract.client_signed_at = timezone.now()
                contract.status = 'client_signed'
                if form.cleaned_data.get('amount'):
                    contract.amount = form.cleaned_data['amount']
                contract.save()
                # Create notification for the freelancer
                create_notification(
                    user=freelancer,
                    notification_type='contract',
                    message=f'Client has signed the contract for {job.title}',
                    related_job=job,
                    related_user=request.user
                )
                messages.success(request, 'Contract signed successfully.')
                return redirect('job:detail', pk=job_id)
        elif not is_client and contract.status == 'client_signed':
            if not freelancer_bkash:
                bkash_required_error = 'You must add your bKash account number in your profile before signing the contract.'
            elif client_bkash and freelancer_bkash == client_bkash:
                bkash_required_error = 'Your bKash account number cannot be the same as the client\'s. Please update your bKash account number to proceed.'
            elif form.is_valid():
                contract.freelancer_signature = form.cleaned_data['signature']
                contract.freelancer_signed_at = timezone.now()
                contract.status = 'freelancer_signed'
                contract.save()
                # Update job status
                job.hired_freelancer = freelancer
                job.already_hired = True
                job.save()
                # Update proposal status
                proposal = get_object_or_404(Proposal, job=job, freelancer=freelancer)
                proposal.status = 'hired'
                proposal.save()
                # Create notification for the client
                create_notification(
                    user=job.created_by,
                    notification_type='contract',
                    message=f'Freelancer has signed the contract for {job.title}',
                    related_job=job,
                    related_user=request.user
                )
                # Send email notification
                try:
                    logger.info(f"Attempting to send contract signed email for contract {contract.id}")
                    send_contract_signed_email(request, contract, request.user)
                    logger.info(f"Contract signed email sent successfully for contract {contract.id}")
                except Exception as e:
                    logger.error(f"Failed to send contract signed email for contract {contract.id}: {str(e)}")
                    messages.error(request, 'Contract signed but failed to send email notification')
                messages.success(request, 'Contract signed successfully.')
                return redirect('job:detail', pk=job_id)
        else:
            # If form validation fails, create a new form with the POST data
            form = ContractForm(request.POST)
            # Set the initial amount from the contract
            form.initial['amount'] = contract.amount
    else:
        form = ContractForm(instance=contract)
        # Ensure the amount is set in the form's initial data
        form.initial['amount'] = contract.amount
    
    # Set the appropriate bKash account based on who is viewing
    bkash_account = client_bkash if is_client else freelancer_bkash
    
    return render(request, 'job/contract.html', {
        'job': job,
        'freelancer': freelancer,
        'contract': contract,
        'form': form,
        'is_client': is_client,
        'bkash_account': bkash_account,
        'bkash_required_error': bkash_required_error,
        'download_mode': False
    })

@login_required
def update_proposal_status(request, job_id, proposal_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
    
    try:
        job = get_object_or_404(Job, pk=job_id)
        proposal = get_object_or_404(Proposal, pk=proposal_id, job=job)
        
        # Only allow job owner to update proposal status
        if request.user != job.created_by:
            return JsonResponse({'error': 'Permission denied. Only the job owner can update proposal status.'}, status=403)
        
        new_status = request.POST.get('status')
        if not new_status:
            return JsonResponse({'error': 'Status parameter is required'}, status=400)
            
        if new_status not in dict(Proposal.STATUS_CHOICES):
            return JsonResponse({
                'error': f'Invalid status. Allowed values are: {", ".join(dict(Proposal.STATUS_CHOICES).keys())}',
                'received_status': new_status
            }, status=400)
        
        try:
            proposal.status = new_status
            proposal.save()
            
            # Recalculate messaged count
            # Get all conversations where the client is a member
            client_conversations = Conversation.objects.filter(members=request.user)
            # Get all freelancers who are members of these conversations
            messaged_freelancers = User.objects.filter(
                conversations__in=client_conversations
            ).exclude(id=request.user.id).distinct()
            # Count proposals from these freelancers for this job
            messaged_count = Proposal.objects.filter(
                job=job,
                freelancer__in=messaged_freelancers
            ).count()
            
            # Add success message for status update
            status_display = dict(Proposal.STATUS_CHOICES)[new_status]
            messages.success(request, f'Proposal status updated to {status_display}.')
            
            return JsonResponse({'status': 'success', 'messaged_count': messaged_count})
        except Exception as e:
            return JsonResponse({
                'error': 'Failed to update proposal status',
                'details': str(e)
            }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }, status=500)

@login_required
def download_invoice(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is the client
    if request.user != job.created_by:
        raise PermissionDenied("Only the client can download this invoice.")
    
    # Get payment details
    payment = job.payments.order_by('-created_at').first()
    payment_details = job.calculate_payment_amount()
    
    # If no payment exists, create a temporary payment object for the invoice
    if not payment:
        payment = {
            'amount': payment_details['amount'],
            'bkash_fee': payment_details['bkash_fee'],
            'total_amount': payment_details['total_amount'],
            'transaction_id': 'Pending',
            'client_bkash_number': job.created_by.freelancer.bkash_account if hasattr(job.created_by, 'freelancer') else 'Not provided',
            'status': 'pending',
            'created_at': timezone.now(),
            'verified_at': None
        }
    
    # Render the invoice template
    html_content = render_to_string('job/invoice_download.html', {
        'job': job,
        'payment': payment,
        'freelancer': job.hired_freelancer,
        'client': job.created_by,
        'is_client': True,  # Since only client can access this view
        'is_pending': not isinstance(payment, Payment)
    })
    
    # Create the response
    response = HttpResponse(html_content, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="invoice_{job.id}.html"'
    
    return response

@login_required
def download_contract(request, job_id, freelancer_id):
    job = get_object_or_404(Job, id=job_id)
    freelancer = get_object_or_404(User, id=freelancer_id)

    # Check if the user is either the client or freelancer
    if request.user not in [job.created_by, freelancer]:
        raise PermissionDenied("You don't have permission to download this contract.")

    contract = Contract.objects.filter(job=job, freelancer=freelancer).first()
    if not contract:
        return render(request, 'job/contract_not_found.html', {
            'job': job,
            'freelancer': freelancer,
        }, status=404)
    is_client = request.user == job.created_by

    # Render contract as HTML (download version)
    html_content = render_to_string('job/contract_download.html', {
        'job': job,
        'freelancer': freelancer,
        'contract': contract,
        'is_client': is_client,
    })

    response = HttpResponse(html_content, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="contract_{job.id}_{freelancer.id}.html"'
    return response

@login_required
def close_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is the job creator
    if job.created_by != request.user:
        return HttpResponseForbidden("You don't have permission to close this job.")
    
    # Check if job is already hired
    if job.already_hired:
        return HttpResponseForbidden("Cannot close a job that has already hired a freelancer.")
    
    # Mark job as closed
    job.is_closed = True
    job.save()
    
    messages.success(request, "Job has been marked as closed.")
    return redirect('job:detail', pk=job.id)

@login_required
def open_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    if job.created_by != request.user:
        return HttpResponseForbidden("You don't have permission to open this job.")
    if not job.is_closed:
        messages.info(request, "Job is already open.")
        return redirect('job:detail', pk=job.id)
    job.is_closed = False
    job.save()
    messages.success(request, "Job has been marked as open.")
    return redirect('job:detail', pk=job.id)

def job_grid(request):
    jobs = Job.objects.filter(
        is_closed=False,  # Only show non-closed jobs
        already_hired=False,  # Only show jobs that haven't been hired for
        is_active=True  # Only show active jobs
    ).order_by('-created_at')
    
    # Get all categories for the filter
    categories = Category.objects.all()
    
    # Get filter parameters
    category = request.GET.get('category')
    search = request.GET.get('search')
    
    # Apply filters
    if category:
        jobs = jobs.filter(category__name=category)
    if search:
        jobs = jobs.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(category__name__icontains=search)
        )
    
    context = {
        'jobs': jobs,
        'categories': categories,
        'selected_category': category,
        'search_query': search,
    }
    return render(request, 'job/grid.html', context)

@login_required
def deposit_funds(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is the job creator
    if request.user != job.created_by:
        messages.error(request, "You don't have permission to deposit funds for this job.")
        return redirect('job:detail', pk=job.id)
    
    # Check if job is already hired
    if not job.already_hired:
        messages.error(request, "You can only deposit funds for a job after hiring a freelancer.")
        return redirect('job:detail', pk=job.id)
    
    # Check for pending payments
    pending_payment = Payment.objects.filter(job=job, status='pending').exists()
    if pending_payment:
        messages.warning(request, "You already have a pending payment for this job.")
        return redirect('job:detail', pk=job.id)
    
    # Check for rejected payments
    has_rejected_payment = Payment.objects.filter(job=job, status='rejected').exists()
    
    # Only check payment_verified if there are no rejected payments
    if not has_rejected_payment and job.payment_verified:
        messages.error(request, "Payment has already been verified for this job.")
        return redirect('job:detail', pk=job.id)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.job = job
            payment.status = 'pending'
            payment.save()
            messages.success(request, "Payment submitted successfully. Please wait for verification.")
            return redirect('job:detail', pk=job.id)
    else:
        # Calculate payment amounts
        payment_details = job.calculate_payment_amount()
        initial_data = {
            'amount': round(payment_details['amount']),
            'bkash_fee': round(payment_details['bkash_fee']),
            'total_amount': round(payment_details['total_amount'])
        }
        form = PaymentForm(initial=initial_data)
    
    return render(request, 'job/deposit_funds.html', {
        'job': job,
        'form': form,
        'payment_details': {
            'amount': round(payment_details['amount']),
            'bkash_fee': round(payment_details['bkash_fee']),
            'total_amount': round(payment_details['total_amount']),
        },
        'platform_bkash': '01812345678',
        'pending_payment': pending_payment,
        'has_rejected_payment': has_rejected_payment
    })

@login_required
def request_refund(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Check if user is the job creator
    if job.created_by != request.user:
        return HttpResponseForbidden("You don't have permission to request a refund for this job.")
    
    # Check if payment is verified
    if not job.payment_verified:
        return HttpResponseForbidden("Cannot request refund for a job with unverified payment.")
    
    # Check if job is already completed
    if job.completion_date:
        return HttpResponseForbidden("Cannot request refund for a completed job.")
    
    # Check if refund is already requested or accepted
    if job.refund_requested or job.refund_accepted:
        return HttpResponseForbidden("A refund request is already pending or has been accepted for this job.")
    
    # Check if there's a rejected refund request
    has_rejected_refund = job.refund_requests.filter(status='rejected').exists()
    if has_rejected_refund:
        return HttpResponseForbidden("Your previous refund request was rejected. Please contact support for assistance.")
    
    # Get the payment object
    payment = job.payments.first()
    if not payment:
        return HttpResponseForbidden("No payment found for this job.")
    
    if request.method == 'POST':
        form = RefundRequestForm(request.POST)
        if form.is_valid():
            refund_request = form.save(commit=False)
            refund_request.job = job
            refund_request.payment = payment
            refund_request.save()
            
            # Update job status
            job.refund_requested = True
            job.save()
            
            messages.success(request, "Refund request submitted successfully. Our team will investigate your request.")
            return redirect('job:detail', pk=job.id)
    else:
        form = RefundRequestForm()
    
    return render(request, 'job/request_refund.html', {
        'job': job,
        'form': form,
        'payment': payment
    })

# Admin views for payment verification and refund handling
@login_required
@user_passes_test(lambda u: u.is_staff)
def verify_payment(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    
    if request.method == 'POST':
        payment.status = 'verified'
        payment.verified_at = timezone.now()
        payment.save()
        
        # Update job payment status
        job = payment.job
        job.payment_verified = True
        job.save()
        
        # Create notification for the client
        create_notification(
            user=job.created_by,
            notification_type='payment',
            message=f'Your payment of {payment.amount} BDT for {job.title} has been verified.',
            related_job=job
        )
        
        # Create notification for the freelancer
        if job.hired_freelancer:
            create_notification(
                user=job.hired_freelancer,
                notification_type='payment',
                message=f'Payment of {payment.amount} BDT for {job.title} has been verified.',
                related_job=job
            )
        
        # Send email notifications
        send_payment_verified_email(request, payment)
        
        messages.success(request, 'Payment verified successfully')
        return redirect('job:detail', pk=job.id)
    
    return render(request, 'job/verify_payment.html', {
        'payment': payment
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def handle_refund(request, refund_id):
    refund = get_object_or_404(RefundRequest, id=refund_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'accept':
            refund.status = 'accepted'
            refund.handled_by = request.user
            refund.handled_at = timezone.now()
            refund.save()
            
            # Update job status
            refund.job.refund_accepted = True
            refund.job.save()
            
            messages.success(request, "Refund request accepted.")
        elif action == 'reject':
            refund.status = 'rejected'
            refund.handled_by = request.user
            refund.handled_at = timezone.now()
            refund.save()
            
            messages.success(request, "Refund request rejected.")
        
        return redirect('admin:refund_list')
    
    return render(request, 'admin/handle_refund.html', {
        'refund': refund
    })

@login_required
@user_passes_test(lambda u: u.is_staff)
def process_payout(request, payout_id):
    payout = get_object_or_404(FreelancerPayout, id=payout_id)
    
    if request.method == 'POST':
        form = PayoutForm(request.POST, instance=payout)
        if form.is_valid():
            payout = form.save(commit=False)
            payout.status = 'completed'
            payout.completed_at = timezone.now()
            payout.save()
            
            messages.success(request, "Payout processed successfully.")
            return redirect('admin:payout_list')
    else:
        form = PayoutForm(instance=payout)
    
    return render(request, 'admin/process_payout.html', {
        'payout': payout,
        'form': form
    })