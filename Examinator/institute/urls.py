# institute/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Institution URLs (assuming this is the root of your 'institute' app)
    path('', views.institution_list, name='institution_list'),
    path('create/', views.institution_create, name='institution_create'),
    path('<int:pk>/', views.institution_detail, name='institution_detail'),
    path('<int:pk>/update/', views.institution_update, name='institution_update'),
    path('<int:pk>/delete/', views.institution_delete, name='institution_delete'),

    # InstitutionPasskey URLs
    path('passkeys/', views.passkey_list, name='passkey_list'),
    path('passkeys/create/', views.passkey_create, name='passkey_create'),
    path('passkeys/<int:pk>/', views.passkey_detail, name='passkey_detail'),
    path('passkeys/<int:pk>/update/', views.passkey_update, name='passkey_update'),
    path('passkeys/<int:pk>/delete/', views.passkey_delete, name='passkey_delete'), # Corrected this line

    # Institute Application URLs
    # e.g., /institute/apply/
    path('apply/', views.apply_for_institute, name='apply_for_institute'),
    path('applications/', views.manage_applications, name='manage_applications'),
    path('applications/status/', views.student_applications_status, name='student_applications_status'), # NEWLY ADDED
    path('applications/<int:pk>/detail/', views.application_detail, name='application_detail'),
    path('applications/<int:pk>/approve/', views.approve_application, name='approve_application'),
    path('applications/<int:pk>/reject/', views.reject_application, name='reject_application'),

    # get institute
    path('get-classes-for-institution/', views.get_classes_for_institution, name='get_classes_for_institution'),
    # New URL to list all groups
    path('groups/', views.list_institution_groups, name='list-institution-groups'),
    path('group/create/', views.manage_institution_group, name='create-institution-group'),
    path('groups/<int:pk>/delete/', views.delete_institution_group, name='delete-institution-group'),
    path('group/edit/<int:pk>/', views.manage_institution_group, name='edit-institution-group'),


    path('institution-groups/<int:group_id>/manage/', views.manage_institution_group_view, name='manage_institution_group'),
]
