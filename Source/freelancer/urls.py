from django.urls import path

from . import views

app_name = 'freelancer'

urlpatterns = [
    path('', views.freelancers, name='freelancers'),
    path('new/', views.new, name='new'),
    path('<int:pk>/', views.freelancer_detail, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('<int:pk>/delete/', views.delete, name='delete'),
    path('<int:pk>/download-earnings/', views.download_earnings_statement, name='download_earnings'),
    path('<int:pk>/download-expenses/', views.download_expenses_statement, name='download_expenses'),
    
    # Skill URLs
    path('<int:pk>/skill/add/', views.add_skill, name='add_skill'),
    path('<int:pk>/skill/<int:skill_id>/edit/', views.edit_skill, name='edit_skill'),
    path('<int:pk>/skill/<int:skill_id>/delete/', views.delete_skill, name='delete_skill'),
    
    # Experience URLs
    path('<int:pk>/experience/add/', views.add_experience, name='add_experience'),
    path('<int:pk>/experience/<int:experience_id>/edit/', views.edit_experience, name='edit_experience'),
    path('<int:pk>/experience/<int:experience_id>/delete/', views.delete_experience, name='delete_experience'),
    
    # Education URLs
    path('<int:pk>/education/add/', views.add_education, name='add_education'),
    path('<int:pk>/education/<int:education_id>/edit/', views.edit_education, name='edit_education'),
    path('<int:pk>/education/<int:education_id>/delete/', views.delete_education, name='delete_education'),
    
    # Certification URLs
    path('<int:pk>/certification/add/', views.add_certification, name='add_certification'),
    path('<int:pk>/certification/<int:certification_id>/edit/', views.edit_certification, name='edit_certification'),
    path('<int:pk>/certification/<int:certification_id>/delete/', views.delete_certification, name='delete_certification'),
    
    # Project URLs
    path('<int:pk>/project/add/', views.add_project, name='add_project'),
    path('<int:pk>/project/<int:project_id>/edit/', views.edit_project, name='edit_project'),
    path('<int:pk>/project/<int:project_id>/delete/', views.delete_project, name='delete_project'),
    path('<int:pk>/qr-code/', views.generate_qr_code, name='qr_code'),
    path('plans/', views.plans, name='plans'),
]
