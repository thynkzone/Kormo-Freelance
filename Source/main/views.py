from django.views.generic import TemplateView
from django.shortcuts import render, redirect
from django.utils import timezone
import pytz
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Max, Subquery, OuterRef, Avg, F
from job.models import Job, Category, Skill, Review
from freelancer.models import Freelancer, FreelancerSkill
from django.core.paginator import Paginator


class IndexPageView(TemplateView):
    template_name = 'main/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        
        # Get view type
        view_type = request.GET.get('view_type', 'jobs')
        page = request.GET.get('page', 1)
        
        # Get filter parameters
        job_budget_min = request.GET.get('job_budget_min')
        job_budget_max = request.GET.get('job_budget_max')
        job_categories = request.GET.getlist('job_categories[]')
        job_skills = request.GET.getlist('job_skills[]')
        job_search = request.GET.get('job_search', '')
        
        freelancer_rate_min = request.GET.get('freelancer_rate_min')
        freelancer_rate_max = request.GET.get('freelancer_rate_max')
        freelancer_categories = request.GET.getlist('freelancer_categories[]')
        freelancer_skills = request.GET.getlist('freelancer_skills[]')
        freelancer_availability = request.GET.get('freelancer_availability')
        freelancer_search = request.GET.get('freelancer_search', '')
        skill_level = request.GET.get('skill_level', '')
        
        sort = request.GET.get('sort', 'recent')
        
        # Base querysets
        jobs = Job.objects.filter(already_hired=False, is_closed=False, is_active=True)
        freelancers = Freelancer.objects.filter(is_not_available=False)
        
        # Get saved job IDs for authenticated users
        saved_job_ids = []
        if request.user.is_authenticated:
            saved_job_ids = list(request.user.saved_jobs.values_list('job_id', flat=True))
        
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
                reviewer__in=freelancer.user.hired_jobs.values_list('created_by', flat=True)
            )
            
            # Only include reviews where both reviews exist for the job
            filtered_reviews = [
                review for review in all_freelancer_reviews
                if review.job.has_client_review and review.job.has_freelancer_review
            ]
            
            # Calculate average rating
            if filtered_reviews:
                avg_rating = sum([
                    (review.knowledge_depth + review.fast_turnaround + 
                     review.multiple_revisions + review.quality_of_work + 
                     review.responsiveness) / 5.0
                    for review in filtered_reviews
                ]) / len(filtered_reviews)
                freelancer.rating = round(avg_rating, 1)
                freelancer.save()  # Save the rating to the database
            else:
                freelancer.rating = 0.00
                freelancer.save()  # Save the rating to the database
        
        # Apply job filters
        if job_categories:
            jobs = jobs.filter(category_id__in=job_categories)
        if job_budget_min:
            jobs = jobs.filter(budget__gte=job_budget_min)
        if job_budget_max:
            jobs = jobs.filter(budget__lte=job_budget_max)
        if job_skills:
            jobs = jobs.filter(skills__name__in=job_skills).distinct()
        if job_search:
            jobs = jobs.filter(
                Q(title__icontains=job_search) |
                Q(description__icontains=job_search)
            )
            
        # Apply freelancer filters
        if freelancer_categories:
            freelancers = freelancers.filter(category_id__in=freelancer_categories)
        if freelancer_rate_min:
            freelancers = freelancers.filter(hourly_rate__gte=freelancer_rate_min)
        if freelancer_rate_max:
            freelancers = freelancers.filter(hourly_rate__lte=freelancer_rate_max)
        if freelancer_skills:
            # Get freelancers with matching skills
            skill_freelancers = FreelancerSkill.objects.filter(
                skill__name__in=freelancer_skills
            ).values_list('freelancer_id', flat=True).distinct()
            
            freelancers = freelancers.filter(id__in=skill_freelancers)
            
            if skill_level:
                # Further filter by skill level
                level_freelancers = FreelancerSkill.objects.filter(
                    freelancer_id__in=skill_freelancers,
                    skill__name__in=freelancer_skills,
                    level=skill_level
                ).values_list('freelancer_id', flat=True).distinct()
                
                freelancers = freelancers.filter(id__in=level_freelancers)
                
        if freelancer_availability == 'available':
            freelancers = freelancers.filter(is_not_available=False)
        if freelancer_search:
            freelancers = freelancers.filter(
                Q(fullname__icontains=freelancer_search) |
                Q(description__icontains=freelancer_search)
            )
        
        # Apply sorting
        if view_type == 'freelancers':
            if sort == 'rating_desc':
                # Sort by rating descending, but put freelancers with rating = 0 (N/A) at the end
                freelancers = freelancers.extra(
                    select={'rating_order': 'CASE WHEN rating = 0 THEN 1 ELSE 0 END'}
                ).order_by('rating_order', '-rating')
            elif sort == 'rating_asc':
                # Sort by rating ascending, put freelancers with rating = 0 (N/A) at the beginning
                freelancers = freelancers.extra(
                    select={'rating_order': 'CASE WHEN rating = 0 THEN 0 ELSE 1 END'}
                ).order_by('rating_order', 'rating')
            elif sort == 'hourly_rate_desc':
                freelancers = freelancers.order_by('-hourly_rate')
            elif sort == 'hourly_rate_asc':
                freelancers = freelancers.order_by('hourly_rate')
            elif sort == 'name_asc':
                freelancers = freelancers.order_by('fullname')
            elif sort == 'name_desc':
                freelancers = freelancers.order_by('-fullname')
            elif sort == 'skill_level':
                # Get the highest skill level for each freelancer
                highest_skill_level = FreelancerSkill.objects.filter(
                    freelancer=OuterRef('pk')
                ).order_by('-level').values('level')[:1]
                
                freelancers = freelancers.annotate(
                    highest_skill_level=Subquery(highest_skill_level)
                ).order_by('-highest_skill_level', '-created_at')
            else:  # recent
                freelancers = freelancers.order_by('-created_at')
        else:
            if sort == 'budget_desc':
                jobs = jobs.order_by('-budget')
            elif sort == 'budget_asc':
                jobs = jobs.order_by('budget')
            elif sort == 'proposals_desc':
                jobs = jobs.annotate(proposals_count=Count('proposals')).order_by('-proposals_count')
            elif sort == 'proposals_asc':
                jobs = jobs.annotate(proposals_count=Count('proposals')).order_by('proposals_count')
            else:  # recent
                jobs = jobs.order_by('-created_at')
        
        # Add proposal range label to each job
        if view_type != 'freelancers':
            # Annotate all jobs with proposal count if not already done
            if not any(hasattr(job, 'proposals_count') for job in jobs):
                jobs = jobs.annotate(proposals_count=Count('proposals'))
            
            # Add proposal range label
            for job in jobs:
                if job.proposals_count < 10:
                    job.proposal_range = "<10 proposals"
                elif job.proposals_count < 20:
                    job.proposal_range = "<20 proposals"
                elif job.proposals_count < 50:
                    job.proposal_range = "<50 proposals"
                else:
                    job.proposal_range = "50+ proposals"
        
        # Implement pagination
        if view_type == 'freelancers':
            paginator = Paginator(freelancers, 20)  # Show 20 freelancers per page
            freelancers_page = paginator.get_page(page)
            context['freelancers'] = freelancers_page
        else:
            paginator = Paginator(jobs, 20)  # Show 20 jobs per page
            jobs_page = paginator.get_page(page)
            context['jobs'] = jobs_page
        
        # Get all categories and skills for filters
        context.update({
            'view_type': view_type,
            'categories': Category.objects.all(),
            'skills': Skill.objects.all(),
            'skill_levels': FreelancerSkill._meta.get_field('level').choices,
            'saved_job_ids': saved_job_ids,  # Add saved job IDs to context
            
            # Pass filter values back to template
            'active_filters': {
                'view_type': view_type,
                'sort': sort,
                'job_budget_min': job_budget_min,
                'job_budget_max': job_budget_max,
                'job_skills': job_skills,
                'job_search': job_search,
                'categories': job_categories if view_type == 'jobs' else freelancer_categories,
                'skills': job_skills if view_type == 'jobs' else freelancer_skills,
                'freelancer_rate_min': freelancer_rate_min,
                'freelancer_rate_max': freelancer_rate_max,
                'freelancer_availability': freelancer_availability,
                'freelancer_search': freelancer_search,
                'skill_level': skill_level,
            }
        })
        
        return context


class ChangeLanguageView(TemplateView):
    template_name = 'main/change_language.html'
