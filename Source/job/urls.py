# urls.py
from django.urls import path

from . import views

app_name = 'job'

urlpatterns = [
    path('', views.jobs, name='jobs'),
    path('new/', views.new_job, name='new'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/delete/', views.delete, name='delete'),
    path('<int:job_id>/proposals/', views.proposals, name='proposals'),
    path('<int:pk>/propose/', views.submit_proposal, name='submit_proposal'),
    path('<int:job_id>/hire/<int:freelancer_id>/', views.hire_freelancer, name='hire'),
    path('<int:job_id>/review/<int:for_user_id>/', views.add_review, name='create_review'),
    path('<int:pk>/social-media-image/', views.social_media_image, name='social_media_image'),
    path('<int:pk>/mark-complete/', views.mark_job_complete, name='mark_complete'),
    path('invite/<int:job_id>/<int:freelancer_id>/', views.invite_to_job, name='invite_to_job'),
    path('<int:job_id>/proposals/<int:proposal_id>/status/', views.update_proposal_status, name='update_proposal_status'),
    path('save/<int:job_id>/', views.save_job, name='save_job'),
    path('unsave/<int:job_id>/', views.unsave_job, name='unsave_job'),
    path('reports/submit/', views.submit_report, name='submit_report'),
    path('jobs/<int:job_id>/hire/<int:freelancer_id>/', views.create_contract, name='create_contract'),
    path('jobs/<int:job_id>/contract/<int:freelancer_id>/', views.view_contract, name='contract'),
    path('jobs/<int:job_id>/contract/<int:freelancer_id>/cancel/', views.cancel_contract, name='cancel_contract'),
    path('jobs/<int:job_id>/contract/<int:freelancer_id>/download/', views.download_contract, name='download_contract'),
    path('job/<int:job_id>/close/', views.close_job, name='close_job'),
    path('job/<int:job_id>/open/', views.open_job, name='open_job'),
    path('job/<int:job_id>/deposit/', views.deposit_funds, name='deposit_funds'),
    path('job/<int:job_id>/refund/', views.request_refund, name='request_refund'),
    path('admin/payment/<int:payment_id>/verify/', views.verify_payment, name='verify_payment'),
    path('admin/refund/<int:refund_id>/handle/', views.handle_refund, name='handle_refund'),
    path('admin/payout/<int:payout_id>/process/', views.process_payout, name='process_payout'),
    path('job/<int:job_id>/invoice/', views.download_invoice, name='download_invoice'),
]