from .forms import RegistrationForm, ProfileForm, UserEditForm, \
    AdminUserCreationForm,GroupForm,ProfileEditForm,TeacherCreationForm, \
        InstituteUserEditForm,InstituteProfileEditForm,UserPermissionForm,GroupAdminUserCreationForm,OrganizationUserCreationForm, \
            OrganizationGroupForm,OrgUserAdminForm, OrgProfileAdminForm,DjangoGroupForm,PermissionCreateForm
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required,permission_required,user_passes_test

# --- UPDATED IMPORTS FOR NEW DATA MODEL ---
from curritree.models import TreeNode # For academic_stream options
from saas.models import OrganizationProfile ,OrganizationProfile, LicenseGrant# For client organization management
# Removed imports: from education.models import Board, StudentClass, Division
# Removed imports: from institute.models import Institution
# ------------------------------------------

from django.db.models import F, Window,Count
from django.db.models.functions import Rank
from django.db import transaction
from datetime import date
from django.urls import reverse



from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission


from .models import EmailVerificationToken, User,Profile,OrganizationGroup

from django.core.mail import send_mail
from django.conf import settings
import uuid
from django.utils import timezone
from datetime import timedelta
from collections import defaultdict
from django.db.models import Q

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator


User = get_user_model()

today = date.today()


def is_superuser_check(user):
    """Returns True if the user is a superuser, False otherwise."""
    return user.is_superuser

# Decorator that combines login check and superuser check
superuser_required = user_passes_test(
    is_superuser_check, 
    # Use a safe fallback for the login URL
    login_url='/login/' 
)

def is_staff_check(user):
    """Returns True if the user is a superuser, False otherwise."""
    return user.is_superuser

staff_required = user_passes_test(
    is_staff_check, 
    # Use a safe fallback for the login URL
    login_url='profile_update' 
)

# Create your views here.
@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful. Please check your email to verify your account.")
            return redirect('home')
        else:
            
            print(form.errors)
            messages.error(request, form.errors) 
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})


def verify_email(request, token):
    token_obj = get_object_or_404(EmailVerificationToken, token=token)

    if not token_obj.is_valid():
        messages.error(request, "This verification link has expired or is invalid.")
        return render(request, 'accounting/verification_failed.html')

    user = token_obj.user
    user.email_verified = True
    user.is_active = True
    user.save()
    token_obj.delete()

    messages.success(request, "✅ Your email has been verified successfully!")
    return render(request, 'accounting/verification_success.html')

# accounts/views.py
def resend_verification(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email, is_active=False)
            token, created = EmailVerificationToken.objects.update_or_create(
                user=user,
                defaults={'token': uuid.uuid4(), 'expires_at': timezone.now() + timedelta(hours=24)}
            )

            verification_link = f"{settings.SITE_URL}/verify-email/{token.token}"
            send_mail(
                "Verify Your Email",
                f"Click the link below to verify your email:\n\n{verification_link}",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False
            )
            messages.success(request, "A new verification email has been sent.")
        except User.DoesNotExist:
            messages.error(request, "No unverified account found with that email.")

    return render(request, 'accounting/resend_verification.html')


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, "credentials correct")
            return redirect('profile_update')
        else:
            messages.error(request, "Invalid credentials")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')


# @login_required
# def profile_update_view(request):
#     profile = request.user.profile
    
#     # 1. Fetch current stream and options (assuming TreeNode is defined/imported)
#     current_stream_manager = profile.academic_stream
#     current_stream_instance = current_stream_manager.first() 
    
#     try:
#         # Assuming TreeNode model is available
#         stream_options = TreeNode.objects.filter(
#             node_type__in=['board', 'competitive', 'class', 'subject']
#         ).order_by('node_type', 'name')
#     except NameError:
#         # Fallback if TreeNode model is not defined/imported
#         stream_options = []


#     if request.method == 'POST':
#         # --- 2. Update User Model Fields (first_name, last_name) ---
#         # The user's first name and last name are typically stored on the User model
#         request.user.first_name = request.POST.get('FirstName')
#         request.user.last_name = request.POST.get('Surname')
        
#         # --- 3. Update Profile Model Fields (using snake_case) ---
#         profile.address = request.POST.get('address')
#         profile.middle_name = request.POST.get('MiddleName') # Renamed from MiddleName
        
#         # Renamed from Contact to phone_number
#         phone_number_value = request.POST.get('contact')
#         if phone_number_value:
#             profile.phone_number = phone_number_value
#         else:
#             profile.phone_number = None

#         # Renamed from BirthDate to birth_date
#         birth_date_str = request.POST.get('BirthDate')
#         if birth_date_str:
#             try:
#                 # Parse date string from HTML input (YYYY-MM-DD)
#                 profile.birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
#             except ValueError:
#                 messages.error(request, "Invalid Date of Birth format. Please use YYYY-MM-DD.")
#         else:
#             profile.birth_date = None


#         # --- 4. CRITICAL FIX: Saving the ManyToMany field (treating it as single select) ---
#         stream_id = request.POST.get('academic_stream') 
        
#         if stream_id:
#             # If an ID is provided, set the M2M field to include only that ID
#             profile.academic_stream.set([stream_id])
#         else:
#             # If no ID is provided (e.g., the user cleared the selection), clear the field
#             profile.academic_stream.clear()
        
#         # --- 5. File Upload ---
#         if request.FILES.get('pic'):
#             profile.pic = request.FILES['pic']
#         elif 'pic-clear' in request.POST:
#             profile.pic = None

#         # Save both the user and the profile objects
#         request.user.save()
#         profile.save()

#         messages.success(request, "Profile updated successfully.")
#         return redirect('profile_update')

#     # --- Context for Rendering the Form ---
#     # Prepare the context data, ensuring we pull name fields from the User object
#     return render(request, 'profile_update.html', {
#         # Pass User model fields under the old names so the template works without changes
#         'profile': {
#             'Name': request.user.first_name,
#             'Surname': request.user.last_name,
#             'MiddleName': profile.MiddleName, # Updated to use new model field
#             'Contact': profile.user.phone_number,   # Updated to use new model field
#             'BirthDate': profile.BirthDate,   # Updated to use new model field
#             'address': profile.address,
#             'pic': profile.pic,
#             'organization_profile': profile.organization_profile,
#             # Placeholder for 'stream_or_department' which might be needed for the template
#             'stream_or_department': getattr(profile, 'stream_or_department', None) 
#         },
#         'stream_options': stream_options, 
#         'current_stream_id': current_stream_instance.id if current_stream_instance else None,
#         # 'score' and 'rank' are expected to be available in context, keeping placeholders
#         'score': getattr(profile, 'score', 'N/A'),
#         'rank': getattr(profile, 'rank', 'N/A'),
#         'is_in_any_group': request.user.groups.exists()
#     })

def profile_update_view(request):
    """
    Handles fetching and saving the user's profile data using a ModelForm.
    """
    profile = request.user.profile
    
    # Minimal context data (placeholders for stats)
    score = getattr(profile, 'score', 'N/A')
    rank = getattr(profile, 'rank', 'N/A')

    if request.method == 'POST':
        # Pass the request data, files (for pic), and the profile instance
        form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        
        if form.is_valid():
            # ModelForm handles validation, cleaning, and persistence (including file upload and M2M)
            form.save()
            
            # NOTE: If user-specific fields like first_name/last_name were on the User model
            # instead of the Profile model, you'd need custom logic here:
            # request.user.first_name = form.cleaned_data['Name']
            # request.user.last_name = form.cleaned_data['Surname']
            # request.user.save()
            
            messages.success(request, "Profile updated successfully.")
            return redirect('profile_update')
    else:
        # Initialize the form with the current instance data
        form = ProfileEditForm(instance=profile)

    return render(request, 'profile_update.html', {
        'form': form,
        'profile': profile, # Required for accessing pic.url and organization_profile in the template
        'score': score,
        'rank': rank,
    })



@require_POST
@login_required
def add_to_student_group(request, user_id):
    if request.method == "POST":
        try:
            print('i am hit')
            user = User.objects.get(id=user_id)
            
            # --- REMOVED DEPRECATED INSTITUTE LOGIC ---
            # The profile should be linked to an organization_profile during creation/onboarding
            # ------------------------------------------
            
            student_group, created = Group.objects.get_or_create(name="student_group")
            user.groups.add(student_group)
            user.save()
            return JsonResponse({"status": "success", "message": "User added to student group", "user_id": user.id})
        except Exception as e:
            return JsonResponse({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}, status=500)
    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=400)


 
@login_required
@staff_required
@permission_required('accounts.view_user',login_url='profile_update')
def manage_users_view(request):
    role = request.GET.get("role")
    # --- UPDATED: Filter by organization instead of institute ---
    selected_organization = request.GET.get("organization")
    
    # Exclude the current user from the list
    # Update select_related to use organization_profile
    users = User.objects.exclude(id=request.user.id).select_related('profile', 'profile__organization_profile')

    if role:
        users = users.filter(role=role)

    if selected_organization:
        # Filter by organization name
        users = users.filter(profile__organization_profile__name=selected_organization)
        
    # Group users by organization and then by role
    grouped_data = defaultdict(lambda: defaultdict(list))
    for user in users:
        # Get organization name from profile or a default value
        organization_name = user.profile.organization_profile.name if user.profile and user.profile.organization_profile else "No Client Organization"
        grouped_data[organization_name][user.role].append(user)
        
    # Convert defaultdict to a regular dict for template rendering
    grouped_data_fixed = {
        organization: dict(roles) for organization, roles in grouped_data.items()
    }
    
    # Get all unique roles for the filter dropdown
    roles = User.objects.values_list("role", flat=True).distinct().exclude(role__isnull=True).exclude(role='')
    # Get all organization profiles for filtering
    organizations = OrganizationProfile.objects.all().order_by('name')

    return render(request, "manage_users.html", {
        "grouped_data": grouped_data_fixed,
        "roles": roles,
        "selected_role": role,
        "organizations": organizations, # Pass organizations for the filter dropdown
        "selected_organization": selected_organization,
        "page_title": "Manage Users"
    })

# --- NEW VIEW: Securely delete a user via POST ---
@login_required
@staff_required
@permission_required('accounts.delete_user', raise_exception=True)
def delete_user_view(request, user_id):
    """
    Handles the deletion of a user account via a secure POST request.
    Requires the 'auth.delete_user' permission (typically Superuser/Admin).
    """
    user_to_delete = get_object_or_404(User, id=user_id)

    # Security check 1: Prevent the current admin from deleting their own account
    if user_to_delete == request.user:
        messages.error(request, "You cannot delete your own account.")
        return redirect('manage_users')

    # Security check 2: Prevent non-superusers from deleting other superusers
    # (Optional, but good practice for high-level management)
    if user_to_delete.is_superuser and not request.user.is_superuser:
         messages.error(request, "Only a Superuser can delete another Superuser account.")
         return redirect('manage_users')

    try:
        username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f"User '{username}' has been permanently deleted.")
    except Exception as e:
        messages.error(request, f"An error occurred while deleting user: {str(e)}")
        
    return redirect('manage_users')
# ------------------------------------------------

 

@login_required
@staff_required
@permission_required('accounts.change_user',login_url='profile_update')
def edit_user_view(request, user_id):
    user_to_edit = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    # Safely get or create the profile instance
    try:
        profile = user_to_edit.profile
    except Exception:
        # Create profile if it doesn't exist
        profile = Profile.objects.create(user=user_to_edit)

    # print("User Permissions:" ,user_to_edit.user_permissions.all())
    # for per in user_to_edit.user_permissions.all():
    #     print(per.name)
    
     # Security check: Prevent editing superuser accounts unless it's the current user themselves   
    if request.method == 'POST':
        # NOTE: You MUST replace UserEditForm with your actual user form class
        user_form = UserEditForm(request.POST, instance=user_to_edit) 
        profile_form = ProfileEditForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            # ModelForm save handles all included FK and M2M fields automatically
            user_form.save()
            profile_form.save() 

            messages.success(request, f"User '{user_to_edit.email}' details updated successfully.")
            return redirect('manage_users')
        else:
            messages.error(request, "Please correct the errors below.")
            print("User Form Errors:", user_form.errors)
            print("Profile Form Errors:", profile_form.errors)
    else:
        # NOTE: You MUST replace UserEditForm with your actual user form class
        user_form = UserEditForm(instance=user_to_edit) 
        profile_form = ProfileEditForm(instance=profile)

    # Logic to fetch inherited permissions for display
    inherited_perm_ids = []
    for group in user_to_edit.groups.all():
        inherited_perm_ids.extend([p.name for p in group.permissions.all()])
    inherited_perm_ids = list(set(inherited_perm_ids))

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'user_to_edit': user_to_edit,
        # Using email as the primary identifier
        'page_title': f'Edit User: {user_to_edit.email}', 
        'inherited_perm_ids': inherited_perm_ids,
    }
    return render(request, 'edit_user.html', context)


@permission_required('accounts.add_teacher',raise_exception=True)
def add_teacher_view(request):
    """
    Allows an organization admin to add a new teacher account linked to their organization.
    """
    form = TeacherCreationForm(request.POST or None, request=request)
    if form.is_valid():
        form.save()
        messages.success(request, "Teacher account created successfully.")
        return redirect('manage_institute_users')
    else:
        print("TeacherCreationForm Errors:", form.errors)
    return render(request, 'userInstitute/add_teacher.html', {'form': form, 'page_title': 'Add New Teacher'})



@permission_required('accounts.view_institute_user',raise_exception=True)
def manage_institute_users_view(request):
    """
    Displays teachers and students associated with the logged-in admin's organization.
    """
    user = request.user
    
    # Check for the organization profile link
    organization_profile = user.profile.organization_profile
    if not organization_profile:
        messages.error(request, "Your admin account is not linked to a Client Organization. Please contact a superuser.")
        return redirect('home')

    # Filter all users belonging to this organization profile
    # Exclude the current admin user themselves
    organization_users = User.objects.filter(
        profile__organization_profile=organization_profile
    ).exclude(id=user.id).order_by('role', 'username')

    # Separate users by role for display
    admin_users = organization_users.filter(role__in=['admin']).order_by('role')
    teachers = organization_users.filter(role='teacher')
    students = organization_users.filter(role='student')

    context = {
        'organization_name': organization_profile.name,
        'admin_users': admin_users,
        'teachers': teachers,
        'students': students,
        'page_title': f'Manage Users for {organization_profile.name}',
    }
    return render(request, 'userInstitute/manage_institute_users.html', context)



@permission_required('accounts.change_institute_user',raise_exception=True)
def edit_institute_user_view(request, user_id):
    """
    Allows an organization admin to edit a teacher or student within their organization.
    Security check: uses organization_profile for affiliation verification.
    """
    user_to_edit = get_object_or_404(User, id=user_id)
    admin_org = request.user.profile.organization_profile

    # Security check 1: Ensure the user being edited belongs to the admin's organization
    if not hasattr(user_to_edit, 'profile') or user_to_edit.profile.organization_profile != admin_org:
        messages.error(request, "You do not have permission to edit this user (Organization mismatch).")
        return redirect('manage_institute_users')

    # Security check 2: Prevent editing other admin/superuser roles
    if user_to_edit.role in ['admin'] or user_to_edit.is_superuser:
        if user_to_edit != request.user: # Allow editing own profile details if role permits, but prevent editing other admins
             messages.error(request, "You cannot edit another admin or a superuser account.")
             return redirect('manage_institute_users')
        

    profile, created = Profile.objects.get_or_create(user=user_to_edit)

    if request.method == 'POST':
        user_form = InstituteUserEditForm(request.POST, instance=user_to_edit)
        profile_form = InstituteProfileEditForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, f"User '{user_to_edit.username}' details updated successfully.")
            return redirect('manage_institute_users')
        else:
            messages.error(request, "Please correct the errors below.")
            print("User Form Errors:", user_form.errors)
            print("Profile Form Errors:", profile_form.errors)
    else:
        user_form = InstituteUserEditForm(instance=user_to_edit)
        profile_form = ProfileEditForm(instance=profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'user_to_edit': user_to_edit,
        'page_title': f'Edit User: {user_to_edit.username}',
    }
    return render(request, 'userInstitute/edit_institute_user.html', context)



@permission_required('accounts.delete_institute_user',raise_exception=True)
def delete_institute_user_view(request, user_id):
    """
    Allows an organization admin to delete a teacher or student within their organization.
    Security check: uses organization_profile for affiliation verification.
    """
    user_to_delete = get_object_or_404(User, id=user_id)
    admin_org = request.user.profile.organization_profile

    # Security check 1: Ensure the user being deleted belongs to the admin's organization
    if not hasattr(user_to_delete, 'profile') or user_to_delete.profile.organization_profile != admin_org:
        messages.error(request, "You do not have permission to delete this user (Organization mismatch).")
        return redirect('manage_institute_users')

    # Security check 2: Prevent deleting other admin/superuser roles
    if user_to_delete.role in ['admin'] or user_to_delete.is_superuser:
        messages.error(request, "You cannot delete another admin or a superuser account.")
        return redirect('manage_institute_users')


    if request.method == 'POST':
        username = user_to_delete.username
        user_to_delete.delete()
        messages.success(request, f"User '{username}' deleted successfully.")
        return redirect('manage_institute_users')

    context = {
        'user_to_delete': user_to_delete,
        'page_title': f'Confirm Delete: {user_to_delete.username}',
    }
    return render(request, 'userInstitute/confirm_delete_institute_user.html', context)


# The remaining permission views (get_permissions_by_app_and_model, edit_user_permissions_and_groups, 
# edit_permissions_by_institute_admin) do not directly interact with the refactored profile fields
# and remain valid.

def get_permissions_by_app_and_model(permissions_queryset):
    grouped = defaultdict(lambda: defaultdict(list))
    for perm in permissions_queryset:
        # Ensure that content_type is pre-fetched or accessed carefully
        # Accessing content_type.app_label and content_type.model implies ContentType is related
        grouped[perm.content_type.app_label][perm.content_type.model].append(perm)
    return grouped


@login_required
@staff_required
@permission_required('account.change_user',login_url='profile_update')
def edit_user_permissions_and_groups(request, user_id):
    user = get_object_or_404(User, id=user_id)

    # Note: Printing permissions here is mostly for debugging, keep it minimal in production.
    # print("User Permissions:", user.user_permissions.all())
    
    if request.method == 'POST':
        # --- Handle POST Request for saving changes ---
        
        # 1. Update groups
        selected_group_ids = request.POST.getlist('groups')
        # Ensure we convert IDs to integers if they came from HTML as strings
        selected_group_ids = [int(id) for id in selected_group_ids if id.isdigit()]
        user.groups.set(Group.objects.filter(id__in=selected_group_ids))

        # 2. Update user-level permissions
        selected_permission_ids = request.POST.getlist('user_permissions')
        selected_permission_ids = [int(id) for id in selected_permission_ids if id.isdigit()]
        user.user_permissions.set(Permission.objects.filter(id__in=selected_permission_ids))

        messages.success(request, f'Permissions and groups for {user.username} updated successfully. 🎉')
        return redirect('UserPermission', user_id=user.id) # Assuming this is the correct URL name

    # --- Data for GET request or POST with errors ---

    # 1. Get all permissions in the system, pre-fetching content_type
    all_system_permissions = Permission.objects.all().select_related('content_type').order_by(
        'content_type__app_label', 'content_type__model', 'name'
    )

    # 2. Get permissions directly assigned to the user
    user_direct_permission_ids = set(user.user_permissions.all().values_list('id', flat=True))

    # 3. Get permissions inherited from all current groups (Django's default format)
    # The format is 'app_label.codename' (e.g., 'auth.add_user')
    user_group_permissions_codenames = user.get_group_permissions() 
    
    # 4. Process all system permissions into the nested dictionary structure
    app_perm_dict = get_permissions_by_app_and_model(all_system_permissions)

    context = {
        'user': user,
        'app_perm_dict': dict(app_perm_dict),
        
        # IDs are needed to check the 'checked' state of the direct permission checkbox
        'user_direct_permission_ids': user_direct_permission_ids, 
        
        # Codename format ('app_label.codename') is needed to check the 'disabled' state
        'user_group_permissions_codenames': user_group_permissions_codenames, 
        
        'groups': Group.objects.all(),
        'user_group_ids': set(user.groups.values_list('id', flat=True)), 
    }
    return render(request, 'User_permissions_controler/edit_user_permissions.html', context)


@login_required
@staff_required
def edit_permissions_by_institute_admin(request, user_id):
    user = get_object_or_404(User, id=user_id)


    if request.method == 'POST':
        # ✅ Update groups
        selected_group_ids = request.POST.getlist('groups')
        user.groups.set(Group.objects.filter(id__in=selected_group_ids))

        # ✅ Update direct permissions (non-auth apps only)
        selected_permission_ids = request.POST.getlist('user_permissions')
        allowed_permissions = Permission.objects.exclude(content_type__app_label__in=[
            'auth', 'admin', 'sessions', 'contenttypes', 'taggit', 'accounts'
        ])
        user.user_permissions.set(allowed_permissions.filter(id__in=selected_permission_ids))

        messages.success(request, 'Permissions updated successfully.')
        return redirect('edit_permissions_by_institute_admin', user_id=user.id)

    # 📛 Exclude irrelevant apps from permission listing
    excluded_apps = ['auth', 'admin', 'sessions', 'contenttypes', 'taggit', 'accounts']
    all_permissions = Permission.objects.exclude(content_type__app_label__in=excluded_apps).select_related('content_type').order_by(
        'content_type__app_label', 'content_type__model'
    )

    # 👤 Direct (user-level) permissions
    user_direct_permission_ids = set(user.user_permissions.values_list('id', flat=True))

    # 👥 Group-based permissions (codename only for display)
    user_group_permissions_codenames = user.get_group_permissions()
    group_permission_codenames = [perm.split('.')[1] for perm in user_group_permissions_codenames]

    # 📊 Group permissions by app → model → list
    app_perm_dict = get_permissions_by_app_and_model(all_permissions)

    context = {
        'user': user,
        'app_perm_dict': dict(app_perm_dict),
        'user_permissions': user_direct_permission_ids,
        'group_permissions': group_permission_codenames,
        'groups': Group.objects.all(),
        'user_group_ids': set(user.groups.values_list('id', flat=True)),
    }
    return render(request, 'User_permissions_controler/edit_permissions_by_institute_admin.html', context)



@login_required
@permission_required('accounts.add_organisation_user',login_url='profile_update')
def create_user_by_admin(request, org_pk):
    """
    Allows an Organization Admin to create Teacher or Student accounts,
    limited to their licensed permissions and curriculum nodes.
    """
    admin_user = request.user
    
    # Check if current user is admin
    if admin_user.role != "admin" or not admin_user.is_active:
        messages.error(request, "You do not have permission to create users.")
        return redirect("dashboard")

    # Fetch the organization
    org = None
    if org_pk:
        # Use a placeholder implementation for get_object_or_404
        try:
             org = OrganizationProfile.objects.get(pk=org_pk)
        except:
             messages.error(request, "Organization not found.")
             return redirect("dashboard")
    
    if not org:
        messages.error(request, "No organization linked to your account.")
        return redirect("dashboard")

    # Get all license grants for the org
    # Placeholder implementation for LicenseGrant and filtering
    try:
        license_grants = LicenseGrant.objects.filter(organization_profile=org)
        active_licenses_qs = org.license_grants.filter(
            Q(valid_until__isnull=True) | Q(valid_until__gte=today)
            )

        # Collect licensed permissions and nodes
        licensed_permissions = Permission.objects.filter(
            id__in=active_licenses_qs.values_list('permissions', flat=True)
        ).distinct()

        licensed_nodes = TreeNode.objects.filter(
            id__in=[node.id for grant in active_licenses_qs for node in grant.get_all_licensed_nodes()]
        ).distinct()
    except:
         # Fallback if models are not fully set up
         licensed_permissions = []
         licensed_nodes = []


    if request.method == "POST":
        with transaction.atomic():
            # Gather POST data manually
            role = request.POST.get("role")
            email = request.POST.get("email")
            username = request.POST.get("username")
            password = request.POST.get("password")
            
            # ✅ NEW: Retrieve phone_number from the form
            phone_number = request.POST.get("phone_number") 
            
            # NOTE: Mapping 'name' and 'surname' from HTML to User model fields
            first_name = request.POST.get("name")
            last_name = request.POST.get("surname")
            contact = request.POST.get("contact")
            birth_date = request.POST.get("birth_date")

            permission_ids = request.POST.getlist("permissions")
            stream_ids = request.POST.getlist("academic_stream")

            # Basic Validation
            if role not in ["teacher", "student"]:
                messages.error(request, "Invalid role selected.")
                return redirect("home")

            if User.objects.filter(email=email).exists():
                messages.error(request, "Email already exists.")
                return redirect("home")

            # ✅ Create User: Included first_name, last_name, and phone_number
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role=role,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number # Added phone_number
            )

            # ✅ Assign permissions (restricted to licensed ones)
            valid_permissions = licensed_permissions.filter(id__in=permission_ids)
            user.user_permissions.set(valid_permissions)

            # ✅ Create Profile
            # Profile fields are 'MiddleName', 'Contact', 'BirthDate', etc.
            profile = user.profile
    
            # Assuming 'name' and 'surname' are saved on the User object (first_name/last_name)
            # and 'contact' maps to Profile.Contact (Secondary Contact)
            
            # profile.Name=name # This line is likely incorrect if 'Name' is not a Profile field
            # profile.Surname=surname # This line is likely incorrect if 'Surname' is not a Profile field
            
            profile.Contact=contact
            profile.BirthDate=birth_date or None
            profile.organization_profile=org

            profile.save()
        

            # ✅ Assign academic stream (restricted)
            valid_streams = licensed_nodes.filter(id__in=stream_ids)
            profile.academic_stream.set(valid_streams)

            messages.success(request, f"{role.title()} '{username}' created successfully 🎉")
            return redirect("home")

    context = {
        "page_title": "Create User",
        "licensed_permissions": licensed_permissions,
        "licensed_nodes": licensed_nodes,
    }
    return render(request, "create_user_by_admin.html", context)



@login_required
@permission_required('accounts.view_orgainsation_user',login_url='profile_update')
def list_organization_users(request, org_pk):
    """
    Allows an organization admin to view a paginated list of all users
    associated with their organization.
    """
    # 1. Authorization
    admin_user = request.user
    if admin_user.role != "admin" or not admin_user.is_active:
        messages.error(request, "You do not have permission to view users in this organization.")
        return redirect("dashboard")

    # 2. Fetch Organization
    org = get_object_or_404(OrganizationProfile, pk=org_pk)
    
    # 3. Fetch Users for the Organization
    # Filter User objects whose related Profile is linked to this organization
    # NOTE: Assuming 'user__profile' or similar reverse lookup is available if not using 'profile' directly
    org_users_qs = User.objects.filter(profile__organization_profile=org).order_by('username')
    
    # 4. Pagination
    paginator = Paginator(org_users_qs, 25)  # Show 25 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        "page_title": f"Manage Users for {org.name}",
        "org": org,
        "page_obj": page_obj,
    }
    return render(request, "Organisations/list_organization_users.html", context)



@login_required
@permission_required('accounts.change_organisation_user',login_url='profile_update')
def edit_organization_user(request, org_pk, user_pk):
    """
    Allows an organization admin to edit a specific user's details,
    organization groups, direct permissions, and academic stream.
    """
    # 1. Authorization & Tenant Check
    
    # Ensure the logged-in user is an Admin
    if request.user.role not in ("admin", "main_admin") or not request.user.is_active:
        messages.error(request, "Access Denied: You must be an active admin to manage users.")
        return redirect("dashboard")

    org = get_object_or_404(OrganizationProfile, pk=org_pk)
    
    # Ensure the admin is managing a user within their own organization.
    # Note: If request.user is a Superuser, this check might need adjustment.
    try:
        if request.user.profile.organization_profile != org:
             messages.error(request, "Authorization Failed: You can only manage users in your own organization.")
             return redirect("dashboard")
    except AttributeError:
        # Fails if the admin user somehow doesn't have a profile linked
        messages.error(request, "Authorization Failed: Admin profile missing organization link.")
        return redirect("dashboard")


    # Fetch the target user, ensuring they belong to the current organization
    target_user = get_object_or_404(User.objects.select_related('profile'), 
                                    pk=user_pk, 
                                    profile__organization_profile=org)
    print(" target_user : ", target_user)
    print(" target_user.user_permissions :", target_user.user_permissions.all())
    target_profile = target_user.profile

    print(" organization_groups : ",target_profile.organization_groups.name)
    
    # Initialize Forms
    user_form = OrgUserAdminForm(request.POST or None, instance=target_user)
    profile_form = OrgProfileAdminForm(request.POST or None, request.FILES or None, instance=target_profile)

    # Get current M2M IDs for initial state/POST processing
    user_group_ids = list(target_profile.organization_groups.all().values_list('id', flat=True))
    user_direct_permission_ids = list(target_user.user_permissions.all().values_list('id', flat=True))

    # 2. Handle POST Request
    if request.method == 'POST':
        groups_ids = []
        print(" post request ",request.POST.getlist('organization_groups[]'))
        groups_ids = request.POST.getlist('organization_groups[]')
        permission_ids = request.POST.getlist('user_permissions')

        print(" groups_ids : ",groups_ids)

        if user_form.is_valid() and profile_form.is_valid():
            try:
                with transaction.atomic():
                    user_form.save()
                    profile_form.save()

                    # ---- FIX HERE ----
                    

                    target_profile.organization_groups.set(groups_ids)

                    print(" organization_groups : ",target_profile.organization_groups)
                    # -------------------

                    # Direct permissions
                    target_user.user_permissions.set(permission_ids)

                    # Academic streams
                    academic_streams = profile_form.cleaned_data.get('academic_stream')
                    target_profile.academic_stream.set(academic_streams)

                    messages.success(request, f"User '{target_user.username}' successfully updated.")
                    return redirect('view_organization_users_list', org_pk=org_pk)

            except Exception as e:
                messages.error(request, f"An error occurred while saving user data: {e}")
                
    
    # 3. Prepare Context Data (for GET/Error POST)

    # a. Organization Groups (For Checkbox list)
    all_org_groups = OrganizationGroup.objects.filter(organization=org).order_by('name')


    active_licenses_qs = org.license_grants.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
        )

    # Collect licensed permissions and nodes
    permissions = Permission.objects.filter(
        id__in=active_licenses_qs.values_list('permissions', flat=True)
    ).distinct()

    # b. Structured Permissions (For Accordion UI)
    # permissions = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')
    app_perm_dict = {}

    for perm in permissions:
        app_label = perm.content_type.app_label
        # Clean up model name for display (e.g., change 'user' to 'User')
        model_name = perm.content_type.model.replace('_', ' ').title()
        
        if app_label not in app_perm_dict:
            app_perm_dict[app_label] = {}
        
        if model_name not in app_perm_dict[app_label]:
            app_perm_dict[app_label][model_name] = []
            
        app_perm_dict[app_label][model_name].append(perm)

    context = {
        'page_title': f"Edit User: {target_user.username}",
        'org': org,
        'target_user': target_user,
        'user_form': user_form,
        'profile_form': profile_form,
        'all_org_groups': all_org_groups,
        'user_group_ids': user_group_ids,
        'app_perm_dict': app_perm_dict,
        'user_direct_permission_ids': user_direct_permission_ids,
    }
    return render(request, "Organisations/edit_organization_user.html", context)




@login_required
@permission_required('accounts.view_organizationgroup',login_url='profile_update')
def manage_organization_groups(request, group_id=None):

    """
    Handles creating new groups and editing existing groups for the current organization.
    """
    # 1. Tenant Check: Ensure the user is linked to an organization
    try:
        # NOTE: Using a placeholder object for organization access
        organization = request.user.profile.organization_profile
    except AttributeError:
        messages.error(request, "Access Denied: Your user account is not associated with an organization profile.")
        return redirect('home')

    if not organization:
        messages.error(request, "Access Denied: Organization profile not found.")
        return redirect('home')
    
    # 2. Instance Handling (Edit vs. Create)
    is_editing = bool(group_id)
    group_permission_ids = [] # Initialize list for checked permissions

    if is_editing:
        # Fetch the group instance, ensure it belongs to the current organization
        group_instance = get_object_or_404(OrganizationGroup, id=group_id, organization=organization)
        action_name = "Edit"
        # When editing, get the current list of permission IDs
        group_permission_ids = list(group_instance.permissions.values_list('id', flat=True))
    else:
        # New group instance, pre-set the organization but don't save yet
        group_instance = OrganizationGroup(organization=organization)
        action_name = "Create"

    # 3. Form Submission
    if request.method == 'POST':
        # Form only validates the 'name' field now
        form = OrganizationGroupForm(request.POST, instance=group_instance)
        
        if form.is_valid():
            new_group = form.save(commit=False)
            new_group.organization = organization # Double-check organization linkage
            
            try:
                new_group.save()
                
                # --- MANUAL PERMISSIONS HANDLING (NEW) ---
                # 1. Get the list of IDs from the submitted checkboxes (name="permissions" in template)
                permission_ids = request.POST.getlist('permissions')
                
                # 2. Update the ManyToMany field
                # NOTE: form.save_m2m() is removed as the field is no longer on the form
                new_group.permissions.set(permission_ids)
                # -----------------------------------------

                messages.success(request, f"Group '{new_group.name}' successfully {action_name.lower()}d.")
                return redirect('manage_groups') # Redirect back to the list view
            except Exception as e:
                # Catch unexpected database errors
                messages.error(request, f"An error occurred while saving the group: {e}")
                
        # If form is invalid, proceed to render with errors
    else:
        # GET request or initial render
        form = OrganizationGroupForm(instance=group_instance)
    
    # 4. Permission Data Structuring (NEW: Required for Accordion UI)
    # Fetch all permissions and organize them by App Label and Model Name
    # org = get_object_or_404(OrganizationProfile, pk=org_pk)

    active_licenses_qs = organization.license_grants.filter(
        Q(valid_until__isnull=True) | Q(valid_until__gte=today)
        )

    # # Collect licensed permissions and nodes
    permissions = Permission.objects.filter(
        id__in=active_licenses_qs.values_list('permissions', flat=True)
    ).select_related('content_type').order_by('content_type__app_label', 'name')

    # permissions = Permission.objects.select_related('content_type').order_by('content_type__app_label', 'name')
    app_perm_dict = {}

    for perm in permissions:
        app_label = perm.content_type.app_label
        model_name = perm.content_type.model
        
        if app_label not in app_perm_dict:
            app_perm_dict[app_label] = {}
        
        if model_name not in app_perm_dict[app_label]:
            app_perm_dict[app_label][model_name] = []
            
        app_perm_dict[app_label][model_name].append(perm)
    
    # 5. Context Preparation
    all_organization_groups = OrganizationGroup.objects.filter(organization=organization).order_by('name')

    context = {
        'form': form,
        'organization': organization,
        'groups': all_organization_groups,
        'is_editing': is_editing,
        'action_name': action_name,
        # NEW context variables for the permission accordion:
        'app_perm_dict': app_perm_dict, 
        'group_permission_ids': group_permission_ids,
    }
    return render(request, 'groups/manage_groups.html', context)

@login_required
@permission_required('saas.delete_organizationgroup',login_url='profile_update')
def delete_organization_group(request, group_id):
    """
    Handles deleting a group, ensuring it belongs to the current organization.
    """
    try:
        organization = request.user.profile.organization_profile
    except AttributeError:
        messages.error(request, "Access Denied: Not linked to an organization.")
        return redirect('home') 
        
    group = get_object_or_404(OrganizationGroup, id=group_id, organization=organization)

    if request.method == 'POST':
        group_name = group.name
        group.delete()
        messages.success(request, f"Group '{group_name}' has been successfully deleted.")
        return redirect('manage_groups')

    # Simple GET request shows a confirmation page (or could be handled by a modal in the template)
    return render(request, 'groups/group_confirm_delete.html', {'group': group, 'organization': organization})




@login_required
@superuser_required
def django_group_list(request):
    """
    Displays a list of all Django Groups.
    """
    # Fetch all groups, prefetching related users and permissions for efficiency
    groups = Group.objects.prefetch_related('permissions').order_by('name')
    
    context = {
        'groups': groups,
        'title': 'Manage Django User Groups',
    }
    return render(request, 'groups/django_group_list.html', context)

# --- 2. Create View (Create) ---

@login_required
@superuser_required
def django_group_create(request):
    """
    Handles creation of a new Django Group.
    """
    if request.method == 'POST':
        form = DjangoGroupForm(request.POST)
        if form.is_valid():
            group = form.save()
            messages.success(request, f"Django Group '{group.name}' created successfully.")
            return redirect(reverse('group_list'))
    else:
        form = DjangoGroupForm()
    
    context = {
        'form': form,
        'title': 'Create New Django User Group',
    }
    return render(request, 'groups/django_group_form.html', context)


# --- 3. Update View (Update) ---

@login_required
@superuser_required
def django_group_update(request, pk):
    """
    Handles updating an existing Django Group.
    """
    group = get_object_or_404(Group, pk=pk)
    
    if request.method == 'POST':
        form = DjangoGroupForm(request.POST, instance=group)
        if form.is_valid():
            form.save()
            messages.success(request, f"Django Group '{group.name}' updated successfully.")
            return redirect(reverse('group_list'))
    else:
        form = DjangoGroupForm(instance=group)
    
    context = {
        'form': form,
        'title': f"Edit Django Group: {group.name}",
        'object': group, # object is required by the delete link in the template
    }
    return render(request, 'groups/django_group_form.html', context)


# --- 4. Delete View (Delete) ---

@login_required
@superuser_required
def django_group_delete(request, pk):
    """
    Handles deletion of a Django Group.
    """
    group = get_object_or_404(Group, pk=pk)

    if request.method == 'POST':
        group_name = group.name
        group.delete()
        messages.warning(request, f"Django Group '{group_name}' deleted.")
        return redirect(reverse('group_list'))
    
    # GET request shows the confirmation page
    context = {
        'object': group,
        'title': 'Confirm Group Deletion',
    }
    return render(request, 'groups/django_group_confirm_delete.html', context)






@login_required
@staff_required
@permission_required('auth.view_permission',login_url='profile_update')
def permission_list(request):
    # Fetch all permissions ordered by app + model
    permissions = Permission.objects.select_related('content_type').order_by(
        'content_type__app_label', 'content_type__model', 'codename'
    )

    # Group by app -> model
    grouped = {}
    for perm in permissions:
        app_label = perm.content_type.app_label.replace('_', ' ').title()
        model_name = perm.content_type.model.replace('_', ' ').title()

        if app_label not in grouped:
            grouped[app_label] = {}
        if model_name not in grouped[app_label]:
            grouped[app_label][model_name] = []
        
        grouped[app_label][model_name].append(perm)

    return render(request, 'User_permissions_controler/permission_list.html', {
        'title': 'All Permissions',
        'grouped': grouped
    })



@login_required
@staff_required
@permission_required('auth.add_permission',login_url='profile_update')
def permission_create(request):
    if request.method == 'POST':
        form = PermissionCreateForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Permission created successfully!")
            return redirect('permission_list')  # (optional) redirect to a list page
    else:
        form = PermissionCreateForm()

    return render(request, 'User_permissions_controler/create_permission.html', {'form': form, 'title': 'Add New Permission'})



@login_required
@staff_required
@permission_required('auth.delete_permission',login_url='profile_update')
def permission_delete(request, pk):
    permission = get_object_or_404(Permission, pk=pk)
    name = permission.name

    if request.method == "POST":
        permission.delete()
        messages.success(request, f'Permission "{name}" deleted successfully!')
        return redirect('permission_list')

    messages.error(request, "Invalid request.")
    return redirect('permission_list')
