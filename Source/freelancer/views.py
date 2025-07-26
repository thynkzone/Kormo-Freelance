from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count, F, Exists, OuterRef, Sum
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.core.paginator import Paginator
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import qrcode
import os
import base64
from django.utils import timezone
from django.template.loader import render_to_string
from decimal import Decimal

from .forms import (
    NewFreelancerForm, EditFreelancerForm, FreelancerSkillForm, 
    FreelancerExperienceForm, FreelancerEducationForm, 
    FreelancerCertificationForm, FreelancerProjectForm, BkashForm
)
from .models import Category, Freelancer, FreelancerSkill, FreelancerExperience, FreelancerEducation, FreelancerCertification, FreelancerProject, SubscriptionPlan, Subscription
from job.models import Skill, Job, Review, Contract

def freelancers(request):
    query = request.GET.get('query', '')
    category_id = request.GET.get('category', 0)
    selected_skills = request.GET.getlist('skills', [])
    min_rating = request.GET.get('min_rating', 0)
    min_jobs_completed = request.GET.get('min_jobs_completed', 0)
    page = request.GET.get('page', 1)
    
    categories = Category.objects.all()
    all_skills = Skill.objects.all()
    freelancers = Freelancer.objects.filter(is_not_available=False)

    # Add completed jobs count annotation
    freelancers = freelancers.annotate(
        completed_jobs_count=Count(
            'user__hired_jobs',
            filter=Q(user__hired_jobs__completion_date__isnull=False),
            distinct=True
        )
    )

    # Calculate ratings for each freelancer
    for freelancer in freelancers:
        # Get freelancer reviews (only from clients)
        all_freelancer_reviews = Review.objects.filter(
            job__completion_date__isnull=False,
            for_user=freelancer.user,
            job__hired_freelancer=freelancer.user,  # Only get reviews from jobs where they were hired
            reviewer__in=freelancer.user.hired_jobs.values_list('created_by', flat=True)
        )
        
        # Only include reviews where both client and freelancer review exist
        freelancer_reviews = [
            review for review in all_freelancer_reviews
            if review.job.has_client_review and review.job.has_freelancer_review
        ]
        
        # Calculate freelancer average rating
        if freelancer_reviews:
            avg_rating = sum([
                (review.knowledge_depth + review.fast_turnaround + 
                 review.multiple_revisions + review.quality_of_work + 
                 review.responsiveness) / 5.0
                for review in freelancer_reviews
            ]) / len(freelancer_reviews)
            freelancer.rating = round(avg_rating, 1)
            freelancer.save()
        else:
            freelancer.rating = 0.00
            freelancer.save()
            
        # Calculate individual rating averages for the radar chart
        freelancer_avg_rating = {
            'avg_knowledge': 0,
            'avg_turnaround': 0,
            'avg_revisions': 0,
            'avg_quality': 0,
            'avg_responsiveness': 0,
            'avg_rating': 0
        }
        
        if freelancer_reviews:
            avg_knowledge = sum(review.knowledge_depth for review in freelancer_reviews) / len(freelancer_reviews)
            avg_turnaround = sum(review.fast_turnaround for review in freelancer_reviews) / len(freelancer_reviews)
            avg_revisions = sum(review.multiple_revisions for review in freelancer_reviews) / len(freelancer_reviews)
            avg_quality = sum(review.quality_of_work for review in freelancer_reviews) / len(freelancer_reviews)
            avg_responsiveness = sum(review.responsiveness for review in freelancer_reviews) / len(freelancer_reviews)
            
            freelancer_avg_rating = {
                'avg_knowledge': round(avg_knowledge, 1),
                'avg_turnaround': round(avg_turnaround, 1),
                'avg_revisions': round(avg_revisions, 1),
                'avg_quality': round(avg_quality, 1),
                'avg_responsiveness': round(avg_responsiveness, 1),
                'avg_rating': round(sum([
                    avg_knowledge,
                    avg_turnaround,
                    avg_revisions,
                    avg_quality,
                    avg_responsiveness
                ]) / 5, 1)
            }
            
        # Calculate job-specific averages for freelancer reviews
        freelancer_reviews_with_ratings = []
        for review in freelancer_reviews:
            review.rating = (
                review.knowledge_depth + 
                review.fast_turnaround + 
                review.multiple_revisions + 
                review.quality_of_work + 
                review.responsiveness
            ) / 5.0
            freelancer_reviews_with_ratings.append(review)

        # Get client reviews (reviews received when acting as a client)
        all_client_reviews = Review.objects.filter(
            job__completion_date__isnull=False,
            for_user=freelancer.user,
            job__created_by=freelancer.user  # Jobs where they were the client
        )
        
        # Only include reviews where both client and freelancer review exist
        client_reviews = [
            review for review in all_client_reviews
            if review.job.has_client_review and review.job.has_freelancer_review
        ]
        
        # Calculate client average ratings
        client_avg_rating = {
            'avg_communication': 0,
            'avg_timely_replies': 0,
            'avg_requirements': 0,
            'avg_feedback': 0,
            'avg_revisions': 0,
            'avg_rating': 0
        }
        if client_reviews:
            avg_communication = sum(r.communication for r in client_reviews) / len(client_reviews)
            avg_timely_replies = sum(r.timely_replies for r in client_reviews) / len(client_reviews)
            avg_requirements = sum(r.requirements_detail for r in client_reviews) / len(client_reviews)
            avg_feedback = sum(r.instant_feedback for r in client_reviews) / len(client_reviews)
            avg_revisions = sum(r.logical_revisions for r in client_reviews) / len(client_reviews)
            
            client_avg_rating = {
                'avg_communication': round(avg_communication, 1),
                'avg_timely_replies': round(avg_timely_replies, 1),
                'avg_requirements': round(avg_requirements, 1),
                'avg_feedback': round(avg_feedback, 1),
                'avg_revisions': round(avg_revisions, 1),
                'avg_rating': round(sum([
                    avg_communication,
                    avg_timely_replies,
                    avg_requirements,
                    avg_feedback,
                    avg_revisions
                ]) / 5, 1)
            }

        # Calculate job-specific averages for client reviews
        client_reviews_with_ratings = []
        for review in client_reviews:
            review.rating = sum([
                review.communication,
                review.timely_replies,
                review.requirements_detail,
                review.instant_feedback,
                review.logical_revisions
            ]) / 5
            client_reviews_with_ratings.append(review)

    if category_id:
        try:
            category_id = int(category_id)
            if category_id > 0:
                freelancers = freelancers.filter(category_id=category_id)
        except ValueError:
            messages.error(request, "Invalid category ID")

    if selected_skills:
        try:
            selected_skills = [int(skill_id) for skill_id in selected_skills]
            freelancers = freelancers.filter(skills__skill_id__in=selected_skills)
        except ValueError:
            messages.error(request, "Invalid skill ID")

    if query:
        freelancers = freelancers.filter(Q(fullname__icontains=query) | Q(description__icontains=query))
    
    # Filter by minimum rating
    if min_rating:
        try:
            min_rating = float(min_rating)
            # Get freelancers with average rating >= min_rating
            freelancers = freelancers.filter(rating__gte=min_rating)
        except ValueError:
            messages.error(request, "Invalid rating value")
    
    # Filter by minimum jobs completed
    if min_jobs_completed:
        try:
            min_jobs_completed = int(min_jobs_completed)
            # Get freelancers with completed jobs >= min_jobs_completed
            freelancers = freelancers.filter(completed_jobs_count__gte=min_jobs_completed)
        except ValueError:
            messages.error(request, "Invalid jobs completed value")
    
    # Order by creation date (newest first)
    freelancers = freelancers.order_by('-created_at')

    # Implement pagination
    paginator = Paginator(freelancers, 20)  # Show 20 freelancers per page
    freelancers_page = paginator.get_page(page)

    return render(request, 'freelancer/freelancers.html', {
        'freelancers': freelancers_page,
        'query': query,
        'categories': categories,
        'category_id': int(category_id),
        'all_skills': all_skills,
        'selected_skills': selected_skills,
        'min_rating': float(min_rating) if min_rating else 0,
        'min_jobs_completed': int(min_jobs_completed) if min_jobs_completed else 0
    })

def freelancer_detail(request, pk):
    try:
        freelancer = get_object_or_404(Freelancer, pk=pk)
        if freelancer.is_not_available and (not request.user.is_authenticated or freelancer.user != request.user):
            raise Http404("Freelancer profile is not available")
            
        skills = FreelancerSkill.objects.filter(freelancer=freelancer)
        experiences = FreelancerExperience.objects.filter(freelancer=freelancer)
        education = FreelancerEducation.objects.filter(freelancer=freelancer)
        certifications = FreelancerCertification.objects.filter(freelancer=freelancer)
        projects = FreelancerProject.objects.filter(freelancer=freelancer)
        
        # Get all jobs where the user is either the creator or hired freelancer
        user_jobs = freelancer.user.posted_jobs.all() | freelancer.user.hired_jobs.all()
        
        # Get current user's open jobs for the invite modal (only for authenticated users)
        open_jobs = Job.objects.filter(created_by=request.user, already_hired=False) if request.user.is_authenticated else None
        
        # Calculate completed jobs count
        completed_hired_jobs = freelancer.user.hired_jobs.filter(completion_date__isnull=False).count()
        completed_posted_jobs = freelancer.user.posted_jobs.filter(completion_date__isnull=False).count()
        
        # Calculate in-progress jobs count
        in_progress_hired_jobs = freelancer.user.hired_jobs.filter(completion_date__isnull=True).count()
        in_progress_posted_jobs = freelancer.user.posted_jobs.filter(completion_date__isnull=True).count()
        
        # Calculate total freelancers hired (both completed and in-progress)
        total_freelancers_hired = freelancer.user.posted_jobs.filter(hired_freelancer__isnull=False).count()
        
        # Calculate total spent on completed jobs with contracts
        completed_contracts_as_client = Contract.objects.filter(
            job__created_by=freelancer.user,
            status='freelancer_signed',
            job__completion_date__isnull=False
        ).distinct()
        
        total_spent = 0
        for contract in completed_contracts_as_client:
            bkash_fee = int(round(contract.amount * 0.0185, 0))  # 1.85% bKash fee on contract amount, rounded
            total_spent += contract.amount + bkash_fee
        
        # Get freelancer reviews (only from clients)
        all_freelancer_reviews = Review.objects.filter(
            job__completion_date__isnull=False,
            for_user=freelancer.user,
            job__hired_freelancer=freelancer.user,  # Only get reviews from jobs where they were hired
            reviewer__in=freelancer.user.hired_jobs.values_list('created_by', flat=True)
        )
        
        # Only include reviews where both client and freelancer review exist
        freelancer_reviews = [
            review for review in all_freelancer_reviews
            if review.job.has_client_review and review.job.has_freelancer_review
        ]
        
        # Calculate freelancer average rating
        if freelancer_reviews:
            avg_rating = sum([
                (review.knowledge_depth + review.fast_turnaround + 
                 review.multiple_revisions + review.quality_of_work + 
                 review.responsiveness) / 5.0
                for review in freelancer_reviews
            ]) / len(freelancer_reviews)
            freelancer.rating = round(avg_rating, 1)
            freelancer.save()
        else:
            freelancer.rating = 0.00
            freelancer.save()
            
        # Calculate individual rating averages for the radar chart
        freelancer_avg_rating = {
            'avg_knowledge': 0,
            'avg_turnaround': 0,
            'avg_revisions': 0,
            'avg_quality': 0,
            'avg_responsiveness': 0,
            'avg_rating': 0
        }
        
        if freelancer_reviews:
            avg_knowledge = sum(review.knowledge_depth for review in freelancer_reviews) / len(freelancer_reviews)
            avg_turnaround = sum(review.fast_turnaround for review in freelancer_reviews) / len(freelancer_reviews)
            avg_revisions = sum(review.multiple_revisions for review in freelancer_reviews) / len(freelancer_reviews)
            avg_quality = sum(review.quality_of_work for review in freelancer_reviews) / len(freelancer_reviews)
            avg_responsiveness = sum(review.responsiveness for review in freelancer_reviews) / len(freelancer_reviews)
            
            freelancer_avg_rating = {
                'avg_knowledge': round(avg_knowledge, 1),
                'avg_turnaround': round(avg_turnaround, 1),
                'avg_revisions': round(avg_revisions, 1),
                'avg_quality': round(avg_quality, 1),
                'avg_responsiveness': round(avg_responsiveness, 1),
                'avg_rating': round(sum([
                    avg_knowledge,
                    avg_turnaround,
                    avg_revisions,
                    avg_quality,
                    avg_responsiveness
                ]) / 5, 1)
            }
            
        # Calculate job-specific averages for freelancer reviews
        freelancer_reviews_with_ratings = []
        for review in freelancer_reviews:
            review.rating = (
                review.knowledge_depth + 
                review.fast_turnaround + 
                review.multiple_revisions + 
                review.quality_of_work + 
                review.responsiveness
            ) / 5.0
            freelancer_reviews_with_ratings.append(review)

        # Get client reviews (reviews received when acting as a client)
        all_client_reviews = Review.objects.filter(
            job__completion_date__isnull=False,
            for_user=freelancer.user,
            job__created_by=freelancer.user  # Jobs where they were the client
        )
        
        # Only include reviews where both client and freelancer review exist
        client_reviews = [
            review for review in all_client_reviews
            if review.job.has_client_review and review.job.has_freelancer_review
        ]
        
        # Calculate client average ratings
        client_avg_rating = {
            'avg_communication': 0,
            'avg_timely_replies': 0,
            'avg_requirements': 0,
            'avg_feedback': 0,
            'avg_revisions': 0,
            'avg_rating': 0
        }
        if client_reviews:
            avg_communication = sum(r.communication for r in client_reviews) / len(client_reviews)
            avg_timely_replies = sum(r.timely_replies for r in client_reviews) / len(client_reviews)
            avg_requirements = sum(r.requirements_detail for r in client_reviews) / len(client_reviews)
            avg_feedback = sum(r.instant_feedback for r in client_reviews) / len(client_reviews)
            avg_revisions = sum(r.logical_revisions for r in client_reviews) / len(client_reviews)
            
            client_avg_rating = {
                'avg_communication': round(avg_communication, 1),
                'avg_timely_replies': round(avg_timely_replies, 1),
                'avg_requirements': round(avg_requirements, 1),
                'avg_feedback': round(avg_feedback, 1),
                'avg_revisions': round(avg_revisions, 1),
                'avg_rating': round(sum([
                    avg_communication,
                    avg_timely_replies,
                    avg_requirements,
                    avg_feedback,
                    avg_revisions
                ]) / 5, 1)
            }

        # Calculate job-specific averages for client reviews
        client_reviews_with_ratings = []
        for review in client_reviews:
            review.rating = sum([
                review.communication,
                review.timely_replies,
                review.requirements_detail,
                review.instant_feedback,
                review.logical_revisions
            ]) / 5
            client_reviews_with_ratings.append(review)

        # Find similar freelancers
        similar_freelancers = Freelancer.objects.filter(
            is_not_available=False
        ).exclude(
            id=freelancer.id
        ).filter(
            Q(category=freelancer.category) |
            Q(skills__skill__in=freelancer.skills.values_list('skill', flat=True))
        ).distinct().order_by('-created_at')[:5]

        context = {
            'freelancer': freelancer,
            'skills': skills,
            'experiences': experiences,
            'education': education,
            'certifications': certifications,
            'projects': projects,
            'user_jobs': user_jobs,
            'open_jobs': open_jobs,
            'completed_hired_jobs': completed_hired_jobs,
            'completed_posted_jobs': completed_posted_jobs,
            'in_progress_hired_jobs': in_progress_hired_jobs,
            'in_progress_posted_jobs': in_progress_posted_jobs,
            'total_freelancers_hired': total_freelancers_hired,
            'total_spent': total_spent,
            'freelancer_reviews': freelancer_reviews_with_ratings,
            'client_reviews': client_reviews_with_ratings,
            'freelancer_avg_rating': freelancer_avg_rating,
            'client_avg_rating': client_avg_rating,
            'similar_freelancers': similar_freelancers,
        }
        return render(request, 'freelancer/detail.html', context)
    except Exception as e:
        messages.error(request, f"An error occurred: {str(e)}")
        return redirect('freelancer:freelancers')

@login_required
def new(request):
    if Freelancer.objects.filter(user=request.user).exists():
        messages.warning(request, "You already have a freelancer profile")
        return redirect('freelancer:edit', pk=request.user.freelancer.id)

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'bkash':
            # Handle bKash form submission
            bkash_account = request.POST.get('bkash_account')
            if not bkash_account:
                messages.error(request, "bKash account number is required")
            elif not bkash_account.isdigit() or not bkash_account.startswith('01') or len(bkash_account) != 11:
                messages.error(request, "Invalid bKash account number. Must be 11 digits starting with 01")
            else:
                # Create a new freelancer with just the bKash account
                freelancer = Freelancer.objects.create(
                    user=request.user,
                    category=Category.objects.first(),  # Default category
                    fullname=request.user.get_full_name() or request.user.username,
                    hourly_rate=0,
                    bkash_account=bkash_account
                )
                messages.success(request, "bKash account added successfully")
                return redirect('freelancer:edit', pk=freelancer.id)
        elif form_type == 'main':
            # Handle main form submission
            form = NewFreelancerForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    freelancer = form.save(commit=False)
                    freelancer.user = request.user
                    freelancer.save()
                    messages.success(request, "Freelancer profile created successfully")
                    return redirect('freelancer:detail', pk=freelancer.id)
                except Exception as e:
                    messages.error(request, f"Error creating profile: {str(e)}")
            else:
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
    else:
        # Pre-fill the form with the user's name from Google authentication
        initial_data = {'fullname': request.user.get_full_name() or request.user.username}
        form = NewFreelancerForm(initial=initial_data)

    return render(request, 'freelancer/form.html', {
        'form': form,
        'title': 'New Profile',
    })

@login_required
def edit(request, pk):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    # Calculate earnings from completed jobs with contracts
    completed_contracts_as_freelancer = Contract.objects.filter(
        freelancer=freelancer.user,
        status__in=['completed', 'freelancer_signed'],
        job__completion_date__isnull=False  # Only include completed jobs
    )
    
    total_earned = 0
    for contract in completed_contracts_as_freelancer:
        platform_fee = int(round(contract.amount * 0.15, 0))  # 15% platform fee, rounded
        freelancer_amount = int(contract.amount - platform_fee)  # Amount after platform fee, ensure integer
        bkash_fee = int(round(freelancer_amount * 0.0185, 0))  # 1.85% bKash fee on freelancer amount, rounded
        freelancer_earnings = freelancer_amount + bkash_fee
        total_earned += freelancer_earnings
    
    # Calculate pending earnings from contracts that are signed by both but job isn't complete
    pending_contracts = Contract.objects.filter(
        freelancer=freelancer.user,
        status='freelancer_signed',
        job__completion_date__isnull=True  # Only include jobs that aren't completed yet
    )
    
    pending_earnings = 0
    for contract in pending_contracts:
        platform_fee = int(round(contract.amount * 0.15, 0))  # 15% platform fee, rounded
        freelancer_amount = int(contract.amount - platform_fee)  # Amount after platform fee, ensure integer
        bkash_fee = int(round(freelancer_amount * 0.0185, 0))  # 1.85% bKash fee on freelancer amount, rounded
        freelancer_earnings = freelancer_amount + bkash_fee
        pending_earnings += freelancer_earnings

    # Calculate expenses when user is the client
    completed_contracts_as_client = Contract.objects.filter(
        job__created_by=freelancer.user,
        status='freelancer_signed',
        job__completion_date__isnull=False
    ).distinct()
    
    total_job_expenses = 0
    for contract in completed_contracts_as_client:
        bkash_fee = int(round(contract.amount * 0.0185, 0))  # 1.85% bKash fee, rounded
        total_job_expenses += contract.amount + bkash_fee
    
    # Calculate subscription expenses
    subscriptions = Subscription.objects.filter(user=freelancer.user)
    total_subscription_expenses = int(sum(subscription.plan.price for subscription in subscriptions))
    
    # Total expenses
    total_expenses = total_job_expenses + total_subscription_expenses

    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        form = EditFreelancerForm(instance=freelancer)
        bkash_form = BkashForm(instance=freelancer)
        
        if form_type == 'bkash':
            # Handle bKash form submission
            bkash_form = BkashForm(request.POST, instance=freelancer)
            if bkash_form.is_valid():
                try:
                    bkash_form.save()
                    messages.success(request, "bKash account updated successfully")
                except Exception as e:
                    messages.error(request, f"Error updating bKash account: {str(e)}")
            else:
                for field, errors in bkash_form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            return redirect('freelancer:edit', pk=freelancer.id)
        elif form_type == 'main':
            # Handle main form submission
            form = EditFreelancerForm(request.POST, request.FILES, instance=freelancer)
            if form.is_valid():
                try:
                    form.save()
                    messages.success(request, "Profile updated successfully")
                    return redirect('freelancer:edit', pk=freelancer.id)
                except Exception as e:
                    messages.error(request, f"Error updating profile: {str(e)}")
            else:
                # Log form errors for debugging
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
    else:
        form = EditFreelancerForm(instance=freelancer)
        bkash_form = BkashForm(instance=freelancer)

    return render(request, 'freelancer/edit.html', {
        'form': form,
        'bkash_form': bkash_form,
        'freelancer': freelancer,
        'total_earned': total_earned,
        'pending_earnings': pending_earnings,
        'total_expenses': total_expenses,
    })

@login_required
def delete(request, pk):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        try:
            freelancer.delete()
            messages.success(request, "Your profile has been successfully deleted.")
            return redirect('dashboard:dashboard')
        except Exception as e:
            messages.error(request, "An error occurred while deleting your profile. Please try again.")
            return redirect('dashboard:dashboard')
    return render(request, 'freelancer/confirm_delete.html', {'freelancer': freelancer})

# Skill views
@login_required
def add_skill(request, pk):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = FreelancerSkillForm(request.POST, freelancer=freelancer)
        if form.is_valid():
            try:
                skill = form.save(commit=False)
                skill.freelancer = freelancer
                skill.save()
                messages.success(request, 'Skill added successfully')
                return redirect('freelancer:edit', pk=pk)
            except Exception as e:
                messages.error(request, f"Error adding skill: {str(e)}")
    else:
        form = FreelancerSkillForm(freelancer=freelancer)
    return render(request, 'freelancer/skill_form.html', {'form': form, 'freelancer': freelancer})

@login_required
def edit_skill(request, pk, skill_id):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    skill = get_object_or_404(FreelancerSkill, pk=skill_id, freelancer=freelancer)
    if request.method == 'POST':
        form = FreelancerSkillForm(request.POST, instance=skill)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Skill updated successfully')
                return redirect('freelancer:edit', pk=pk)
            except Exception as e:
                messages.error(request, f"Error updating skill: {str(e)}")
    else:
        form = FreelancerSkillForm(instance=skill)
    return render(request, 'freelancer/skill_form.html', {'form': form, 'freelancer': freelancer})

@login_required
def delete_skill(request, pk, skill_id):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    skill = get_object_or_404(FreelancerSkill, pk=skill_id, freelancer=freelancer)
    if request.method == 'POST':
        try:
            skill.delete()
            messages.success(request, 'Skill deleted successfully')
        except Exception as e:
            messages.error(request, f"Error deleting skill: {str(e)}")
    return redirect('freelancer:edit', pk=pk)

# Experience views
@login_required
def add_experience(request, pk):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = FreelancerExperienceForm(request.POST, freelancer=freelancer)
        if form.is_valid():
            try:
                experience = form.save(commit=False)
                experience.freelancer = freelancer
                experience.save()
                messages.success(request, 'Experience added successfully')
                return redirect('freelancer:edit', pk=pk)
            except Exception as e:
                messages.error(request, f"Error adding experience: {str(e)}")
    else:
        form = FreelancerExperienceForm(freelancer=freelancer)
    return render(request, 'freelancer/experience_form.html', {'form': form, 'freelancer': freelancer})

@login_required
def edit_experience(request, pk, experience_id):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    experience = get_object_or_404(FreelancerExperience, pk=experience_id, freelancer=freelancer)
    if request.method == 'POST':
        form = FreelancerExperienceForm(request.POST, instance=experience)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Experience updated successfully')
                return redirect('freelancer:edit', pk=pk)
            except Exception as e:
                messages.error(request, f"Error updating experience: {str(e)}")
    else:
        form = FreelancerExperienceForm(instance=experience)
    return render(request, 'freelancer/experience_form.html', {'form': form, 'freelancer': freelancer})

@login_required
def delete_experience(request, pk, experience_id):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    experience = get_object_or_404(FreelancerExperience, pk=experience_id, freelancer=freelancer)
    if request.method == 'POST':
        try:
            experience.delete()
            messages.success(request, 'Experience deleted successfully')
        except Exception as e:
            messages.error(request, f"Error deleting experience: {str(e)}")
    return redirect('freelancer:edit', pk=pk)

# Education views
@login_required
def add_education(request, pk):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = FreelancerEducationForm(request.POST, freelancer=freelancer)
        if form.is_valid():
            try:
                education = form.save(commit=False)
                education.freelancer = freelancer
                education.save()
                messages.success(request, 'Education added successfully')
                return redirect('freelancer:edit', pk=pk)
            except Exception as e:
                messages.error(request, f"Error adding education: {str(e)}")
    else:
        form = FreelancerEducationForm(freelancer=freelancer)
    return render(request, 'freelancer/education_form.html', {'form': form, 'freelancer': freelancer})

@login_required
def edit_education(request, pk, education_id):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    education = get_object_or_404(FreelancerEducation, pk=education_id, freelancer=freelancer)
    if request.method == 'POST':
        form = FreelancerEducationForm(request.POST, instance=education)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Education updated successfully')
                return redirect('freelancer:edit', pk=pk)
            except Exception as e:
                messages.error(request, f"Error updating education: {str(e)}")
    else:
        form = FreelancerEducationForm(instance=education)
    return render(request, 'freelancer/education_form.html', {'form': form, 'freelancer': freelancer})

@login_required
def delete_education(request, pk, education_id):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    education = get_object_or_404(FreelancerEducation, pk=education_id, freelancer=freelancer)
    if request.method == 'POST':
        try:
            education.delete()
            messages.success(request, 'Education deleted successfully')
        except Exception as e:
            messages.error(request, f"Error deleting education: {str(e)}")
    return redirect('freelancer:edit', pk=pk)

# Certification views
@login_required
def add_certification(request, pk):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = FreelancerCertificationForm(request.POST, freelancer=freelancer)
        if form.is_valid():
            try:
                certification = form.save(commit=False)
                certification.freelancer = freelancer
                certification.save()
                messages.success(request, 'Certification added successfully')
                return redirect('freelancer:edit', pk=pk)
            except Exception as e:
                messages.error(request, f"Error adding certification: {str(e)}")
    else:
        form = FreelancerCertificationForm(freelancer=freelancer)
    return render(request, 'freelancer/certification_form.html', {'form': form, 'freelancer': freelancer})

@login_required
def edit_certification(request, pk, certification_id):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    certification = get_object_or_404(FreelancerCertification, pk=certification_id, freelancer=freelancer)
    if request.method == 'POST':
        form = FreelancerCertificationForm(request.POST, instance=certification)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Certification updated successfully')
                return redirect('freelancer:edit', pk=pk)
            except Exception as e:
                messages.error(request, f"Error updating certification: {str(e)}")
    else:
        form = FreelancerCertificationForm(instance=certification)
    return render(request, 'freelancer/certification_form.html', {'form': form, 'freelancer': freelancer})

@login_required
def delete_certification(request, pk, certification_id):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    certification = get_object_or_404(FreelancerCertification, pk=certification_id, freelancer=freelancer)
    if request.method == 'POST':
        try:
            certification.delete()
            messages.success(request, 'Certification deleted successfully')
        except Exception as e:
            messages.error(request, f"Error deleting certification: {str(e)}")
    return redirect('freelancer:edit', pk=pk)

# Project views
@login_required
def add_project(request, pk):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    if request.method == 'POST':
        form = FreelancerProjectForm(request.POST, request.FILES, freelancer=freelancer)
        if form.is_valid():
            try:
                project = form.save(commit=False)
                project.freelancer = freelancer
                project.save()
                messages.success(request, 'Project added successfully')
                return redirect('freelancer:edit', pk=pk)
            except Exception as e:
                messages.error(request, f"Error adding project: {str(e)}")
    else:
        form = FreelancerProjectForm(freelancer=freelancer)
    return render(request, 'freelancer/project_form.html', {'form': form, 'freelancer': freelancer})

@login_required
def edit_project(request, pk, project_id):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    project = get_object_or_404(FreelancerProject, pk=project_id, freelancer=freelancer)
    if request.method == 'POST':
        form = FreelancerProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, 'Project updated successfully')
                return redirect('freelancer:edit', pk=pk)
            except Exception as e:
                messages.error(request, f"Error updating project: {str(e)}")
    else:
        form = FreelancerProjectForm(instance=project)
    return render(request, 'freelancer/project_form.html', {'form': form, 'freelancer': freelancer})

@login_required
def delete_project(request, pk, project_id):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    project = get_object_or_404(FreelancerProject, pk=project_id, freelancer=freelancer)
    if request.method == 'POST':
        try:
            project.delete()
            messages.success(request, 'Project deleted successfully')
        except Exception as e:
            messages.error(request, f"Error deleting project: {str(e)}")
    return redirect('freelancer:edit', pk=pk)

@login_required
def generate_qr_code(request, pk):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    
    # Create QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=20,
        border=4,
    )
    
    # Add the freelancer profile URL
    profile_url = request.build_absolute_uri(f'/freelancers/{freelancer.id}/')
    qr.add_data(profile_url)
    qr.make(fit=True)
    
    # Create QR code image with green color
    qr_image = qr.make_image(fill_color=(50, 205, 50), back_color=(255, 255, 255))
    
    # Convert PIL Image to a format we can draw on
    qr_image = qr_image.convert('RGBA')
    
    # Create a new image with space for the name
    width, height = qr_image.size
    new_height = height + 60  # Add space for name
    final_image = Image.new('RGBA', (width, new_height), (255, 255, 255, 255))
    
    # Paste QR code
    final_image.paste(qr_image, (0, 0))
    
    # Add freelancer name
    try:
        # Try to load a font, fall back to default if not available
        font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    # Create a drawing context
    draw = ImageDraw.Draw(final_image)
    
    # Calculate text position to center it
    text = freelancer.fullname
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_position = ((width - text_width) // 2, height + 10)
    
    # Draw the text
    draw.text(text_position, text, fill=(50, 205, 50), font=font)
    
    # Save the final image to a BytesIO object
    buffer = BytesIO()
    final_image.save(buffer, format='PNG')
    qr_code_data = buffer.getvalue()
    
    # Check if download is requested
    if request.GET.get('download') == 'true':
        # Return the QR code as a downloadable file
        response = HttpResponse(qr_code_data, content_type='image/png')
        response['Content-Disposition'] = f'attachment; filename="kormo_freelancer_{freelancer.id}_qr.png"'
        return response
    
    # Convert the QR code image to a base64 string for embedding in HTML
    qr_code_base64 = base64.b64encode(qr_code_data).decode()
    qr_code_url = f"data:image/png;base64,{qr_code_base64}"
    
    # Show the HTML version
    return render(request, 'freelancer/qr_code.html', {
        'freelancer': freelancer,
        'qr_code_url': qr_code_url
    })

@login_required
def plans(request):
    user = request.user
    freelancer = getattr(user, 'freelancer', None)
    current_subscription = None
    current_plan = 'free'
    pending = False
    error = None

    if freelancer:
        current_subscription = freelancer.get_current_subscription()
        if current_subscription and current_subscription.plan:
            current_plan = current_subscription.plan.name
        # Check for pending subscription
        pending_subscription = Subscription.objects.filter(user=user, status='pending').order_by('-created_at').first()
        if pending_subscription:
            pending = True

    if request.method == 'POST':
        plan_name = request.POST.get('plan')
        transaction_id = request.POST.get('transaction_id')
        # Validate plan
        plan = SubscriptionPlan.objects.filter(name=plan_name).first()
        if not plan:
            error = 'Invalid plan selected.'
        elif not transaction_id or not transaction_id.isdigit() or len(transaction_id) != 10:
            error = 'Transaction ID must be exactly 10 digits.'
        elif Subscription.objects.filter(user=user, status='pending').exists():
            error = 'You already have a pending payment. Please wait for admin verification.'
        else:
            # Create pending subscription
            Subscription.objects.create(
                user=user,
                plan=plan,
                status='pending',
                transaction_id=transaction_id
            )
            pending = True
    
    return render(request, 'freelancer/plans.html', {
        'current_plan': current_plan,
        'pending': pending,
        'error': error,
    })

@login_required
def download_earnings_statement(request, pk):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    # Get all completed contracts for completed jobs
    contracts = Contract.objects.filter(
        freelancer=freelancer.user,
        status__in=['completed', 'freelancer_signed'],
        job__completion_date__isnull=False  # Only include completed jobs
    ).select_related('job', 'job__created_by').order_by('-job__completion_date')

    # Calculate earnings for each contract and total
    total_earnings = 0
    total_contract_amount = 0
    total_platform_fee = 0
    total_bkash_fee = 0
    
    for contract in contracts:
        platform_fee = int(round(contract.amount * 0.15, 0))  # 15% platform fee, rounded
        freelancer_amount = int(contract.amount - platform_fee)  # Amount after platform fee, ensure integer
        bkash_fee = int(round(freelancer_amount * 0.0185, 0))  # 1.85% bKash fee on freelancer amount, rounded
        contract.freelancer_earnings = freelancer_amount + bkash_fee
        contract.platform_fee = platform_fee
        contract.bkash_fee = bkash_fee
        
        total_contract_amount += contract.amount
        total_platform_fee += platform_fee
        total_bkash_fee += bkash_fee
        total_earnings += contract.freelancer_earnings

    # Render the earnings statement template
    html_content = render_to_string('freelancer/earnings_statement.html', {
        'freelancer': freelancer,
        'contracts': contracts,
        'total_earnings': total_earnings,
        'total_contract_amount': total_contract_amount,
        'total_platform_fee': total_platform_fee,
        'total_bkash_fee': total_bkash_fee,
        'generated_date': timezone.now(),
    })

    # Create the response
    response = HttpResponse(html_content, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="earnings_statement_{timezone.now().strftime("%Y%m%d")}.html"'

    return response

@login_required
def download_expenses_statement(request, pk):
    freelancer = get_object_or_404(Freelancer, pk=pk)
    if freelancer.user != request.user:
        raise PermissionDenied

    # Get all completed contracts where user is the client
    completed_contracts = Contract.objects.filter(
        job__created_by=freelancer.user,
        status__in=['completed', 'freelancer_signed'],
        job__completion_date__isnull=False  # Only include completed jobs
    ).select_related('job', 'freelancer').order_by('-job__completion_date')

    # Calculate bKash fees and total paid for each contract
    for contract in completed_contracts:
        bkash_fee = int(round(contract.amount * 0.0185, 0))  # 1.85% bKash fee, rounded
        contract.bkash_fee = bkash_fee
        contract.total_paid = contract.amount + bkash_fee

    # Calculate total job expenses
    total_job_expenses = sum(contract.total_paid for contract in completed_contracts)

    # Get all subscriptions for the user
    subscriptions = Subscription.objects.filter(
        user=freelancer.user
    ).select_related('plan').order_by('-created_at')

    # Calculate total subscription expenses
    total_subscription_expenses = int(sum(subscription.plan.price for subscription in subscriptions))

    # Calculate total expenses
    total_expenses = total_job_expenses + total_subscription_expenses

    # Render the expenses statement template
    html_content = render_to_string('freelancer/expenses_statement.html', {
        'freelancer': freelancer,
        'completed_contracts': completed_contracts,
        'subscriptions': subscriptions,
        'total_job_expenses': total_job_expenses,
        'total_subscription_expenses': total_subscription_expenses,
        'total_expenses': total_expenses,
        'generated_date': timezone.now()
    })

    # Create the response
    response = HttpResponse(html_content, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="expenses_statement_{timezone.now().strftime("%Y%m%d")}.html"'

    return response