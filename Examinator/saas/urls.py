from django.urls import path
from . import views

app_name = 'saas'

urlpatterns = [
    # URL for the Organization's License and Usage Dashboard
    # Example access: /saas/dashboard/ or /account/licenses/
    path('dashboard/', views.license_dashboard, name='license_dashboard'),
    path('Create/', views.create_license_view, name='create_dashboard'),
    path('license/<int:pk>/edit/', views.edit_license, name='license_edit'),
    path('license/<int:pk>/delete/', views.delete_license, name='license_delete'),
    path('CreateClientOrgination/', views.create_client_and_organization_view, name='create_ClientOrgination'),
    path('CreateOrganizationAndAdmin/', views.create_organization_and_admin_view, name='create_organization_and_admin_view'),
    path('organizations/', views.organization_list, name='organization_list'),
    path('organizations/<int:pk>/edit/', views.edit_organization, name='organization_edit'),
    path('organization/<int:org_id>/licenses/', views.manage_licenses, name='manage_licenses'),
    path('Createorganizations/', views.create_organization, name='create_organization'),
    path('organizations/<int:org_id>/usage/papers/', views.update_max_question_papers, name='update_max_question_papers'),
    
]  
