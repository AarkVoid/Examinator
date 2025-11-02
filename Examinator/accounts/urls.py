from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('verify-email/<uuid:token>/', views.verify_email, name='verify_email'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),
    path('forgot-password/', auth_views.PasswordResetView.as_view(template_name='registrations/password_reset_form.html'), name='password_reset'),
    path('forgot-password/done/', auth_views.PasswordResetDoneView.as_view(template_name='registrations/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registrations/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='registrations/password_reset_complete.html'), name='password_reset_complete'),
    path('profile/update/', views.profile_update_view, name='profile_update'),
    path('add-to-student-group/<int:user_id>/', views.add_to_student_group, name='add_to_student_group'),
    path('users/', views.manage_users_view, name='manage_users'),
    path('users/<int:user_id>/edit/', views.edit_user_view, name='edit_user'),
    path('users/<int:user_id>/delete/', views.delete_user_view, name='delete_user'),
    # path('institute/teachers/add/', views.add_teacher_view, name='add_teacher'),
    # path('institute/users/', views.manage_institute_users_view, name='manage_institute_users'),
    # path('institute/users/edit/<int:user_id>/', views.edit_institute_user_view, name='edit_institute_user'),
    # path('institute/users/delete/<int:user_id>/', views.delete_institute_user_view, name='delete_institute_user'),
    path('UserPermission/<int:user_id>/',views.edit_user_permissions_and_groups, name='UserPermission'),
    path('institute-admin/UserPermissions/<int:user_id>/', views.edit_permissions_by_institute_admin, name='edit_permissions_by_institute_admin'),
    path('users/create/<int:org_pk>/', views.create_user_by_admin, name='create_user_by_admin'),
    path('view_organization_users/<int:org_pk>/', views.list_organization_users, name='view_organization_users_list'),
    path('organization/<int:org_pk>/users/<int:user_pk>/edit/', views.edit_organization_user, name='view_organization_users_edit'),
    path('manage/', views.manage_organization_groups, name='manage_groups'),
    # Path for editing an existing group
    path('manage/<int:group_id>/', views.manage_organization_groups, name='manage_groups'),
    # Path for deleting a group (requires a confirmation page/modal)
    path('delete/<int:group_id>/', views.delete_organization_group, name='delete_group'),
]