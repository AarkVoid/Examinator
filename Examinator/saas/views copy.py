from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Count

from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from accounts.models import Profile 
from django.urls import reverse
from django.core.paginator import Paginator

# IMPORTANT: Ensure your forms are imported from the correct location
from .saas_admin_forms import (
    OrganizationProfileForm, UsageLimitForm, MultipleLicenseGrantForm, 
    UserAssignmentForm, NewClientUserForm, OrganizationAssignmentForm ,
    OrganizationCreateForm,OrganizationEditForm, LicenseGrantForm

)

from saas.models import OrganizationProfile, LicenseGrant, UsageLimit
# NOTE: The User model is implicitly linked via a Profile model in the application design.

User = get_user_model()

def get_user_organization(user):
    try:
        # Assumes user.profile exists and has a ForeignKey to OrganizationProfile.
        return user.profile.organization_profile
    except AttributeError:
        # Handles cases where 'user.profile' or 'user.profile.organization_profile' is missing.
        return None


@login_required
def license_dashboard(request):
    """
    Displays licensing and usage information.
    - Superusers see all organizations' licenses.
    - Organization admins see only their own.
    """
    today = timezone.now().date()

    # Superuser: show all licenses
    if request.user.is_superuser:
        licenses_qs = LicenseGrant.objects.all().prefetch_related('curriculum_node', 'organization_profile')
        organization = None
    else:
        organization = get_user_organization(request.user)
        if not organization:
            return render(request, 'license_dashboard.html', {
                'organization': None,
                'message': "You are not linked to any organization profile. Please contact support.",
            })
        licenses_qs = LicenseGrant.objects.filter(
            organization_profile=organization
        ).prefetch_related('curriculum_node')

    # Build active and expired license lists
    active_licenses = []
    expired_licenses = []

    for license in licenses_qs:
        valid_until = license.valid_until
        is_active = valid_until is None or valid_until >= today

        # Iterate over all linked curriculum nodes
        for node in license.curriculum_node.all():
            node_type_display = getattr(node, 'get_node_type_display', lambda: node.node_type.capitalize())()
            license_data = {
                'organization_name': license.organization_profile.name if request.user.is_superuser else None,
                'node_name': node.name,
                'node_type': node_type_display,
                'valid_until': valid_until,
                'is_expired': not is_active,
            }
            if is_active:
                active_licenses.append(license_data)
            else:
                expired_licenses.append(license_data)

    # Usage info (only for org admins)
    usage_limit = 0
    current_users = 0
    usage_percent = 0

    if organization:
        try:
            usage_limit = organization.usage_limit.max_users
        except UsageLimit.DoesNotExist:
            usage_limit = 0

        current_users = User.objects.filter(
            profile__organization_profile=organization,
            is_active=True
        ).count()

        if usage_limit > 0:
            usage_percent = min(100, (current_users / usage_limit) * 100)

    context = {
        'organization': organization,
        'active_licenses': active_licenses,
        'expired_licenses': expired_licenses,
        'usage_limit': usage_limit,
        'current_users': current_users,
        'usage_percent': int(usage_percent),
        'message': None
    }

    return render(request, 'license_dashboard.html', context)


@login_required
def create_license_view(request):
    """
    Admin view to create an OrganizationProfile, its UsageLimit,
    multiple LicenseGrants, and create/assign a new client admin user.
    """
    
    # We remove the UserAssignmentForm and use NewClientUserForm
    ClientUserForm = NewClientUserForm 
    
    if request.method == 'POST':
        # Instantiate all four forms with POST data, using prefixes
        org_form = OrganizationProfileForm(request.POST, prefix='org')
        usage_form = UsageLimitForm(request.POST, prefix='usage')
        license_form = MultipleLicenseGrantForm(request.POST, prefix='license')
        # Use the NEW user creation form
        new_user_form = ClientUserForm(request.POST, prefix='user')

        # Validate all forms simultaneously
        if org_form.is_valid() and usage_form.is_valid() and license_form.is_valid() and new_user_form.is_valid():
            try:
                # Use a transaction to ensure all database writes succeed or fail together
                with transaction.atomic():
                    # 1. Create OrganizationProfile
                    organization = org_form.save()
                    
                    # 2. Create UsageLimit
                    usage_limit = usage_form.save(commit=False)
                    usage_limit.organization_profile = organization
                    usage_limit.save()

                    # 3. Create LicenseGrant instance (M2M handled in separate steps)
                    curriculum_nodes = license_form.cleaned_data['curriculum_nodes']
                    valid_until = license_form.cleaned_data['valid_until']
                    
                    license_obj = LicenseGrant.objects.create(
                        organization_profile=organization,
                        valid_until=valid_until
                    )
                    # Set the M2M relationship
                    license_obj.curriculum_node.set(curriculum_nodes)

                    # 4. Create and Assign New User (Client Admin)
                    client_admin_user = new_user_form.save() # This creates User AND Profile
                    
                    # 5. Link the newly created User's Profile to the Organization
                    # We assume new_user_form.save() successfully created the profile object.
                    client_admin_user.profile.organization_profile = organization
                    client_admin_user.profile.save()
                    
                    messages.success(request, f"✅ Client package for '{organization.name}' created and primary administrator '{client_admin_user.email}' setup successfully.")
                    return redirect('saas:license_dashboard') # Redirect to the license dashboard, assuming a URL named 'saas:license_dashboard'
            
            except Exception as e:
                # Include specific model import error if Profile is missing
                messages.error(request, f"A critical error occurred during client creation: {e}")
        else:
            messages.error(request, "Please correct the errors in the highlighted sections below.")
    
    else:
        # Initial GET request: Instantiate blank forms
        org_form = OrganizationProfileForm(prefix='org')
        usage_form = UsageLimitForm(prefix='usage')
        license_form = MultipleLicenseGrantForm(prefix='license')
        # Use the NEW user creation form
        new_user_form = ClientUserForm(prefix='user')

    context = {
        'org_form': org_form,
        'usage_form': usage_form,
        'license_form': license_form,
        'new_user_form': new_user_form, # Updated context key
        'page_title': 'New Organization Setup',
    }
    return render(request, 'create_license_view.html', context)


@login_required
def manage_licenses(request, org_id):
    """
    Create and manage licenses for a specific organization.
    """
    organization = get_object_or_404(OrganizationProfile, id=org_id)
    grants = organization.license_grants.all().prefetch_related('curriculum_node')

    if request.method == 'POST':
        form = LicenseGrantForm(request.POST)
        if form.is_valid():
            grant = form.save(commit=False)
            grant.organization_profile = organization  # Auto-attach org
            grant.save()
            form.save_m2m()
            messages.success(request, "License created successfully.")
            return redirect('saas:manage_licenses', org_id=org_id)
    else:
        form = LicenseGrantForm()

    return render(request, 'manage_licenses.html', {
        'organization': organization,
        'form': form,
        'grants': grants
    })

@login_required
def edit_license(request, pk):
    """
    Allows editing of a single LicenseGrant (including its curriculum nodes and expiry date).
    """
    license_grant = get_object_or_404(LicenseGrant, pk=pk)
    organization = license_grant.organization_profile

    if request.method == 'POST':
        form = LicenseGrantForm(request.POST, instance=license_grant)
        if form.is_valid():
            form.save()
            messages.success(request, f"License for '{organization.name}' updated successfully. 🛠️")
            return redirect('saas:organization_edit', pk=organization.pk)
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = LicenseGrantForm(instance=license_grant)

    context = {
        'form': form,
        'license_grant': license_grant,
        'organization': organization,
        'page_title': f"Edit License for {organization.name}",
    }
    return render(request, 'license_edit.html', context)


@login_required
def delete_license(request, pk):
    """
    Allows deletion of a specific LicenseGrant.
    Confirmation step required.
    """
    license_grant = get_object_or_404(LicenseGrant, pk=pk)
    organization = license_grant.organization_profile

    if request.method == 'POST':
        license_grant.delete()
        messages.success(request, f"License for '{organization.name}' deleted successfully. 🗑️")
        return redirect('saas:organization_edit', pk=organization.pk)

    context = {
        'license_grant': license_grant,
        'organization': organization,
        'page_title': f"Delete License for {organization.name}",
    }
    return render(request, 'license_confirm_delete.html', context)



@login_required
@permission_required('saas.add_organizationprofile', raise_exception=True)
def create_client_and_organization_view(request):
    """
    Handles the creation of a new client administrator (User) and their
    associated OrganizationProfile (new or existing) in one step.
    """
    page_title = "One-Step Client Onboarding"
    
    # Initialize forms
    if request.method == 'POST':
        user_form = NewClientUserForm(request.POST)
        org_assign_form = OrganizationAssignmentForm(request.POST)

        # Check validity of both forms
        if user_form.is_valid() and org_assign_form.is_valid():
            
            # Use a transaction to ensure atomic operations
            try:
                with transaction.atomic():
                    # --- 1. User Creation ---
                    # Save the user instance without committing to the database yet
                    new_user = user_form.save(commit=False)
                    
                    # Set the role and password manually (CRITICAL for password hashing!)
                    new_user.role = user_form.cleaned_data['role'] # 'admin'
                    new_user.set_password(user_form.cleaned_data['password'])
                    new_user.save()
                    
                    # --- 2. Organization Assignment ---
                    org_profile = None
                    existing_org = org_assign_form.cleaned_data.get('existing_organization')
                    new_name = org_assign_form.cleaned_data.get('new_org_name')
                    new_email = org_assign_form.cleaned_data.get('new_billing_email')

                    if existing_org:
                        # Case A: Assign to existing organization
                        org_profile = existing_org
                    
                    elif new_name and new_email:
                        # Case B: Create new organization
                        org_profile = OrganizationProfile.objects.create(
                            name=new_name,
                            billing_email=new_email,
                            # is_active defaults to True
                        )
                        
                        # --- 3. Create Default Usage Limit ---
                        # Automatically create a default usage limit for the new organization
                        UsageLimit.objects.create(
                            organization_profile=org_profile,
                            max_users=50 # Default starting limit
                        )
                    
                    messages.success(request, f"Client Admin '{new_user.email}' and Organization '{org_profile.name}' created successfully.")
                    
                    # Redirect to a success page or the dashboard
                    return redirect(reverse('saas:license_dashboard'))

            except Exception as e:
                # Log error and show user a message
                print(f"Database transaction failed: {e}")
                messages.error(request, f"An unexpected error occurred during client creation. Details: {e}")
        
        # If forms were invalid, they will fall through and be re-rendered
    else:
        # GET request: initialize empty forms
        user_form = NewClientUserForm()
        org_assign_form = OrganizationAssignmentForm()

    context = {
        'page_title': page_title,
        'user_form': user_form,
        'org_assign_form': org_assign_form,
    }
    return render(request, 'create_user_and_organization.html', context)


@login_required
@permission_required('saas.add_organizationprofile', raise_exception=True)
def create_organization_and_admin_view(request):
    """ View to create a new OrganizationProfile and assign an EXISTING User (Client Admin) to it. """
    # ... implementation for existing user assignment ...
    # This is a placeholder as the full implementation was in the previous turn and is not the primary focus now.
    org_form = OrganizationProfileForm(prefix='org')
    user_assign_form = UserAssignmentForm(prefix='user')
    context = {'org_form': org_form, 'user_assign_form': user_assign_form, 'page_title': 'Create Client Organization & Assign Admin'}
    return render(request, 'create_organization_and_admin.html', context)



def organization_list(request):
    """
    Function-based view to display a paginated list of all organizations.
    """
    # Fetch all organizations, ordered by name
    organization_list = OrganizationProfile.objects.all().order_by('name')
    
    # Handle pagination: Show 10 organizations per page
    paginator = Paginator(organization_list, 10) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # The 'page_obj' contains the list of organizations for the current page
    context = {
        'page_obj': page_obj,
    }
    
    return render(request, 'organization_list.html', context)


def create_organization(request):
    if request.method == 'POST':
        form = OrganizationCreateForm(request.POST)
        if form.is_valid():
            organization = form.save()
            messages.success(request, f"Organization '{organization.name}' successfully created! 🎉")
            # Redirect to the organization list view after creation
            return redirect('organization_list') 
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # GET request: display a blank form
        form = OrganizationCreateForm()

    context = {
        'form': form,
        'page_title': 'Create New Organization',
    }
    return render(request, 'organization_create.html', context)


def edit_organization(request, pk):
    organization = get_object_or_404(OrganizationProfile, pk=pk)
    # Fetch grants using the correct related_name
    grants = organization.license_grants.all().order_by('-valid_until')

    # --- Organization Edit Logic ---
    if request.method == 'POST' and 'edit_org' in request.POST:
        org_form = OrganizationEditForm(request.POST, instance=organization)
        if org_form.is_valid():
            org_form.save()
            messages.success(request, f"Organization '{organization.name}' updated successfully! 🛠️")
            return redirect('saas:organization_edit', pk=pk)
        else:
            messages.error(request, "Error updating organization details.")
            license_form = LicenseGrantForm(request.POST)
    
    # --- License Grant Logic (UPDATED FOR MANY-TO-MANY) ---
    elif request.method == 'POST' and 'add_license' in request.POST:
        license_form = LicenseGrantForm(request.POST)
        if license_form.is_valid():
            
            # Use a transaction to ensure both the grant and M2M links save correctly
            with transaction.atomic():
                new_grant = license_form.save(commit=False)
                new_grant.organization_profile = organization # Link FK field
                new_grant.save() # Saves the LicenseGrant instance (without M2M data)
                
                # CRITICAL: This line saves the M2M data to the intermediary table
                license_form.save_m2m() 

            messages.success(request, "New curriculum access granted successfully! 🔑")
            return redirect('saas:organization_edit', pk=pk)
        else:
            messages.error(request, "Error granting license. Check the form for details.")
            org_form = OrganizationEditForm(instance=organization)
    
    # --- GET Request (or form validation failed) ---
    else:
        org_form = OrganizationEditForm(instance=organization)
        license_form = LicenseGrantForm()

    context = {
        'organization': organization,
        'org_form': org_form,
        'license_form': license_form,
        'grants': grants, 
        'page_title': f"Edit: {organization.name}",
    }
    return render(request, 'organization_edit.html', context)



