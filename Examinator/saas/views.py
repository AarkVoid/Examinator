from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Count
from django.core import serializers

from django.shortcuts import render, redirect,get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from accounts.models import Profile 
from django.urls import reverse
from django.core.paginator import Paginator
from curritree.models import TreeNode
from django.contrib.auth.models import Permission
from django.db.models import Q
import json
# IMPORTANT: Ensure your forms are imported from the correct location
from .saas_admin_forms import (
    OrganizationProfileForm, UsageLimitForm, MultipleLicenseGrantForm, 
    UserAssignmentForm, NewClientUserForm, OrganizationAssignmentForm ,
    OrganizationCreateForm,OrganizationEditForm, LicenseGrantForm

)

from django.views.decorators.csrf import csrf_protect, csrf_exempt # New Import
from datetime import date
from saas.models import OrganizationProfile, LicenseGrant, UsageLimit,LicensePermission
from accounts.views import staff_required,superuser_required
import logging
logger = logging.getLogger(__name__)
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
@permission_required('saas.view_license_summary',login_url='profile_update')
def organization_license_overview(request):
    """
    Read-only dashboard showing the current organization's licenses,
    permissions, and usage summary.
    """
    user = request.user
    today = timezone.now().date()

    # ------------------------------
    # Determine which organization to show
    # ------------------------------
    if user.is_superuser:
        organization = None
        licenses = LicenseGrant.objects.select_related("organization_profile").prefetch_related(
            "curriculum_node", "permissions"
        )
    else:
        organization = getattr(user.profile, "organization_profile", None)
        if not organization:
            return render(request, "saas/license_overview.html", {
                "error": "You are not linked to any organization.",
            })
        
        licenses = LicenseGrant.objects.filter(
            organization_profile=organization
        ).prefetch_related("curriculum_node", "permissions")

    # ------------------------------
    # Categorize active vs expired
    # ------------------------------
    active_licenses = []
    expired_licenses = []

    for license in licenses:
        is_active = not license.valid_until or license.valid_until >= today
        license_data = {
            "id": license.id,
            "organization": license.organization_profile.name,
            "valid_until": license.valid_until,
            "curriculum_nodes": license.curriculum_node.all(),
            "permissions": license.permissions.all(),
            "max_papers": license.max_question_papers or 0,
            "created_papers": license.question_papers_created or 0,
        }
        (active_licenses if is_active else expired_licenses).append(license_data)

    # ------------------------------
    # Usage summary (for org users only)
    # ------------------------------
    usage_limit = 0
    current_users = 0
    usage_percent = 0
    draft_limit = 0
    paper_limit = 0
    paper_created = 0
    paper_usage_percent = 0

    if organization:
        try:
            usage_limit = organization.usage_limit.max_users
            draft_limit = organization.usage_limit.max_question_papers_drafts
        except UsageLimit.DoesNotExist:
            usage_limit = 0
            draft_limit = 0

        current_users = User.objects.filter(
            profile__organization_profile=organization,
            is_active=True
        ).count()

        if usage_limit > 0:
            usage_percent = min(100, (current_users / usage_limit) * 100)

        # ✅ Only include active licenses for paper usage
        total_papers_limit = sum(l["max_papers"] for l in active_licenses)
        total_papers_created = sum(l["created_papers"] for l in active_licenses)

        if total_papers_limit > 0:
            paper_usage_percent = min(100, (total_papers_created / total_papers_limit) * 100)

        paper_limit = total_papers_limit
        paper_created = total_papers_created

        print(" usage_percent :",usage_percent)

    # ------------------------------
    # Render context
    # ------------------------------
    context = {
        "organization": organization,
        "active_licenses": active_licenses,
        "expired_licenses": expired_licenses,
        "usage_limit": usage_limit,
        "draft_limit": draft_limit,
        "current_users": current_users,
        "usage_percent": int(usage_percent),
        "paper_limit": paper_limit,
        "paper_created": paper_created,
        "paper_usage_percent": int(paper_usage_percent),
        "today": today,
    }

    return render(request, "license_overview.html", context)


@login_required
@staff_required
@permission_required('saas.add_licensegrant',login_url='profile_update')
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
        # license_form = MultipleLicenseGrantForm(request.POST, prefix='license')
        # Use the NEW user creation form
        new_user_form = ClientUserForm(request.POST, prefix='user')

        # Validate all forms simultaneously
        # if org_form.is_valid() and usage_form.is_valid() and license_form.is_valid() and new_user_form.is_valid():
        if org_form.is_valid() and usage_form.is_valid() and new_user_form.is_valid():
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
                    # curriculum_nodes = license_form.cleaned_data['curriculum_nodes']
                    # valid_until = license_form.cleaned_data['valid_until']
                    
                    # license_obj = LicenseGrant.objects.create(
                    #     organization_profile=organization,
                    #     valid_until=valid_until
                    # )
                    # # Set the M2M relationship
                    # license_obj.curriculum_node.set(curriculum_nodes)

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
        # license_form = MultipleLicenseGrantForm(prefix='license')
        # Use the NEW user creation form
        new_user_form = ClientUserForm(prefix='user')

    context = {
        'org_form': org_form,
        'usage_form': usage_form,
        # 'license_form': license_form,
        'new_user_form': new_user_form, # Updated context key
        'page_title': 'New Organization Setup',
    }
    return render(request, 'create_license_view.html', context)


@login_required
@staff_required
@permission_required('saas.view_licensegrant',login_url='profile_update')
def manage_licenses(request, org_id):
    organization = get_object_or_404(OrganizationProfile, id=org_id)
    # Ensure LicenseGrant is imported/accessible for prefetch
    grants = organization.license_grants.all().prefetch_related('curriculum_node') 
    root_nodes = TreeNode.objects.filter(parent__isnull=True).order_by('name')
    
    today = timezone.now().date()

    # 🔹 Permissions filtering logic
    APP_LABELS = ['accounts', 'quiz','saas']
    ACTION_CODENAMES = ['add_', 'change_', 'delete_', 'view_']

    app_filter = Q(content_type__app_label__in=APP_LABELS)
    action_filter = Q()
 

    available_permissions = Permission.objects.filter(
        app_filter & action_filter
    ).select_related('content_type').order_by(
        'content_type__app_label', 'codename'
    )

    # 🔑 START: Grouping permissions model-wise and calculating display name
    permissions_by_model = {}
    
    for perm in available_permissions:
        # Key: model name (e.g., 'course', 'question', 'user'). We capitalize it for display.
        # model_name = perm.content_type.model.capitalize()
        model_class = perm.content_type.model_class()
       

        # 2. Check if the model class exists (it should, but safety first).
        if model_class:
            # Access the verbose_name_plural from the related model's metadata
            model_name = model_class._meta.verbose_name_plural.title()
        else:
            # Fallback for custom or unlinked permissions
            model_name = perm.content_type.model.replace('_', ' ').title()
           
            
        
        # FIX: Calculate the display name in Python using string replace and capitalize.
        # This prevents the TemplateSyntaxError in HTML. E.g., 'add_quiz' -> 'Add quiz'
        display_name = perm.codename.replace('_', ' ').capitalize()

        if model_name not in permissions_by_model:
            permissions_by_model[model_name] = []

        
        # Store as a dictionary to include the pre-calculated display name
        permissions_by_model[model_name].append({
            'id': perm.id,
            'codename': perm.codename,
            'display_name': display_name
        })
    # 🔑 END: Grouping permissions model-wise


    if request.method == 'POST':
        # 🔹 Extract fields directly from POST
        curriculum_node_ids = request.POST.getlist('curriculum_node')
        permission_ids = request.POST.getlist('permissions')
        valid_until = request.POST.get('valid_until')
        
        # NEW: Extract and safely convert max_question_papers
        max_qp_str = request.POST.get('max_question_papers', '0')
        max_question_papers = None

        try:
            if max_qp_str:
                max_question_papers = int(max_qp_str)
        except ValueError:
            messages.error(request, "Maximum Question Papers must be a valid number.")
            return redirect('saas:manage_licenses', org_id=org_id)


        # Basic validation
        if not valid_until:
            messages.error(request, "Please select a valid expiry date.")
            return redirect('saas:manage_licenses', org_id=org_id)

        # 🔹 Create LicenseGrant, including max_question_papers
        grant = LicenseGrant.objects.create(
            organization_profile=organization,
            valid_until=valid_until,
            max_question_papers=max_question_papers,
        )

        # 🔹 Attach curriculum nodes
        curriculum_nodes = TreeNode.objects.filter(id__in=curriculum_node_ids)
        final_stream_pks = set()
        for node in curriculum_nodes:
            final_stream_pks.add(node.pk)

            # Efficiently retrieve and add all ancestors and descendants to the stream
            ancestors = node.get_ancestors(include_self=False)
            final_stream_pks.update([n.pk for n in ancestors])

            descendants = node.get_descendants(include_self=False)
            final_stream_pks.update([d.pk for d in descendants])

        all_active_nodes_pk = list(final_stream_pks)
        # exclude_ids = []
        # for curriculum_node in all_active_nodes_pk:
        #     print("curriculum_node", curriculum_node)
        #     if curriculum_node.parent is not None:
        #         if str(curriculum_node.parent.id) in map(str, curriculum_node_ids):
        #             print("Parent node included")
        #             exclude_ids.append(curriculum_node.id)
        #             print(curriculum_node.parent.id,curriculum_node.id)
        #             print(curriculum_node_ids)
        # curriculum_nodes = curriculum_nodes.exclude(id__in=exclude_ids) 
        grant.curriculum_node.set(all_active_nodes_pk)

        # 🔹 Attach permissions (via LicensePermission model)
        permissions = Permission.objects.filter(id__in=permission_ids)
        # Ensure LicensePermission is imported/accessible for creation
        for perm in permissions: 
            LicensePermission.objects.create(license=grant, permission=perm)

        messages.success(request, "License created successfully.")
        return redirect('saas:manage_licenses', org_id=org_id)

    # 🔹 Display active and expired grants
    grants_with_paths = []
    active_node_ids = set()

    for grant in grants:
        is_expired = grant.valid_until and grant.valid_until < today
        curriculum_paths = []
        for node_instance in grant.curriculum_node.all():
            curriculum_paths.append(node_instance.get_path_display(sep=' > '))

        grant_data = {
            'id': grant.id,
            'valid_until': grant.valid_until,
            'original_grant': grant,
            'is_expired': is_expired,
            'curriculum_paths':curriculum_paths,
            'max_question_papers': grant.max_question_papers,
        }
        grants_with_paths.append(grant_data)

        if not is_expired:
            node_ids = grant.curriculum_node.all().values_list('id', flat=True)
            active_node_ids.update(node_ids)

    active_curriculum_nodes_qs = TreeNode.objects.filter(
        id__in=list(active_node_ids)
    ).order_by('name')
    print("json_root_nodes :",serializers.serialize('json', root_nodes, fields=('id', 'name', 'node_type')),)
    return render(request, 'manage_licenses.html', {
        'organization': organization,
        'grants': grants,
        'grants_with_paths': grants_with_paths,
        'root_nodes':root_nodes,
        'json_root_nodes': serializers.serialize('json', root_nodes, fields=('id', 'name', 'node_type')),
        'today': today,
        'active_curriculum_nodes': active_curriculum_nodes_qs,
        'available_permissions': available_permissions,
        'all_permissions_by_model': permissions_by_model, # Updated: Now contains the grouped data
    })


@login_required
@staff_required
@permission_required('saas.change_licensegrant',login_url='profile_update')
def edit_license(request, pk):
    """
    Allows editing of a single LicenseGrant (including its curriculum nodes, expiry date, and permissions).
    """
    license_grant = get_object_or_404(LicenseGrant, pk=pk)
    organization = license_grant.organization_profile
   

    # Load all root curriculum nodes
    root_nodes = TreeNode.objects.filter(parent__isnull=True).order_by('name')

    licensed_nodes_with_paths = []
    for node in license_grant.curriculum_node.all():
        # Using .get_ancestors() requires a Tree structure setup (e.g., django-treebeard)
        try:
            ancestor_objects = node.get_ancestors() 
            path_names = [ancestor.name for ancestor in ancestor_objects]
        except AttributeError:
             # Fallback if get_ancestors is not implemented/available
            path_names = ["(Path not available)"]

        licensed_nodes_with_paths.append({
            'name': node.name,
            'id': node.id,
            'path': path_names # A list of ancestor names (strings)
        })

    # --- PERMISSIONS LOGIC UPDATE ---
    
    # 1. Get currently assigned permission IDs efficiently
    # We use LicensePermission model to check what's granted to this specific license
    granted_permission_ids = set(
        LicensePermission.objects.filter(license=license_grant).values_list('permission_id', flat=True)
    )

    # 2. Load available permissions grouped by ContentType model
    # APP_LABELS = ['accounts', 'quiz','saas']
    
    # all_available_permissions = (
    #     Permission.objects.filter(content_type__app_label__in=APP_LABELS)
    #     .select_related('content_type')
    #     .order_by('content_type__app_label', 'name') # Ordering by 'name' (human readable) is better than 'codename'
    # )

    APP_LABELS = ['accounts', 'quiz','saas']
    
    app_filter = Q(content_type__app_label__in=APP_LABELS)
    action_filter = Q()
    # 2. Load available permissions grouped by ContentType model
    
    
    all_available_permissions = Permission.objects.filter(
        app_filter & action_filter
    ).select_related('content_type').order_by(
        'content_type__app_label', 'codename'
    )

    permissions_by_model = {}
    
    for perm in all_available_permissions:

        model_class = perm.content_type.model_class()
       

        # 2. Check if the model class exists (it should, but safety first).
        if model_class:
            # Access the verbose_name_plural from the related model's metadata
            model_name = model_class._meta.verbose_name_plural.title()
        else:
            # Fallback for custom or unlinked permissions
           
            model_name = perm.content_type.model.replace('_', ' ').title()
        # Key: model name (e.g., 'course', 'question', 'user')
        # model_name = perm.content_type.model
        
        if model_name not in permissions_by_model:
            permissions_by_model[model_name] = []
        
        # Attach the 'is_granted' status directly to the object for template use
        perm.is_granted = perm.id in granted_permission_ids
        
        permissions_by_model[model_name].append(perm)
    
    # --- END PERMISSIONS LOGIC UPDATE ---

    # Handle form submission manually (no ModelForm)
    if request.method == 'POST':
        valid_until = request.POST.get('valid_until')
        # Correctly get the node IDs from the hidden field populated by JS
        node_ids = request.POST.getlist('curriculum_node') 
        permission_ids = request.POST.getlist('permissions')

        try:
            license_grant.valid_until = valid_until if valid_until else None
            

            # Update curriculum nodes (set() handles many-to-many relationship update)
            selected_nodes = TreeNode.objects.filter(id__in=node_ids)
            license_grant.curriculum_node.set(selected_nodes)

            # Update permissions
            # Clear existing and add new
            license_grant.LicensePermission.all().delete()

            selected_perms = Permission.objects.filter(id__in=permission_ids)

            # Prepare a list of LicensePermission objects to create
            new_license_permissions = []
            for perm in selected_perms:
                # Assuming LicensePermission requires just the license and permission FKs
                new_license_permissions.append(
                    LicensePermission(
                        license=license_grant,  # FK to LicenseGrant instance
                        permission=perm,        # FK to Permission instance
                    )
                )
            try:
                # Use bulk_create for maximum efficiency
                LicensePermission.objects.bulk_create(new_license_permissions)
            except Exception as e:
                # Handle possible errors like uniqueness constraints
                print(f"Error during bulk_create: {e}")
            
            license_grant.save()

            messages.success(request, f"License for '{organization.name}' updated successfully. 🛠️")
            return redirect('saas:organization_edit', pk=organization.pk)

        except Exception as e:
            messages.error(request, f"An error occurred while updating license: {e}")

    # Prepare JSON data for JS rendering
    root_nodes_json_data = serializers.serialize('json', root_nodes, fields=('name', 'node_type'))
    print(" root_nodes_json_data :",root_nodes_json_data)

    # permissions_json is no longer needed for JS, but we keep other JS variables
    selected_node_ids = list(license_grant.curriculum_node.values_list('id', flat=True))

    context = {
        "license_grant": license_grant,
        "organization": organization,
        "root_nodes": root_nodes, # Still needed for Django select options
        "TAILWIND_INPUT_CLASSES": "mt-1 block w-full rounded-lg border border-gray-300 dark:border-gray-600 shadow-sm p-2 focus:border-indigo-500 focus:ring-indigo-500 dark:bg-gray-700 dark:text-gray-100 dark:focus:border-indigo-400",
        "root_nodes_json": root_nodes_json_data, # Serialized data
        "selected_node_ids": json.dumps(selected_node_ids),
        "page_title": f"Edit License for {organization.name}",
        'licensed_nodes_with_paths' : licensed_nodes_with_paths,
        # NEW CONTEXT VARIABLE FOR TEMPLATE RENDERING
        'permissions_by_model': permissions_by_model,
    }

    return render(request, "license_edit.html", context)


@login_required
@staff_required
@permission_required('saas.delete_licensegrant',login_url='profile_update')
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
@staff_required
@permission_required('saas.add_organizationprofile', raise_exception=True)
def create_client_and_organization_view(request):
    """
    Handles the creation of a new client administrator (User) and their
    associated OrganizationProfile (new or existing) in one step.
    """
    page_title = "One-Step Client Onboarding"
    orgId = request.GET.get('orgId', None)  
    
    # Initialize forms
    if request.method == 'POST':
        user_form = NewClientUserForm(request.POST)
        org_assign_form = OrganizationAssignmentForm(request.POST, org_id=orgId)
        
        # Define today here so it's available in all branches (NEW/EXISTING org)
        today = date.today() 

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
                    
                    # Get the profile (assumes signal or form saved it)
                    profile = new_user.profile 

                    # CRITICAL: Link the Profile to the Organization
                    profile.organization_profile = org_profile
                    
                    # --- 4. License, Stream, and Permission Assignment ---
                    # This logic runs immediately after the organization is assigned.
                    
                    # Get licenses active as of today
                    active_licenses_qs = org_profile.license_grants.filter(
                                Q(valid_until__isnull=True) | Q(valid_until__gte=today)
                            )
                    
                    # --- 4a. GLOBAL RECALCULATION OF ALL ACTIVE LICENSED NODES ---
                    all_licensed_nodes_qs = TreeNode.objects.filter(
                        # Filter nodes only based on the active licenses
                        licensegrant__in=active_licenses_qs
                    ).distinct()

                    # final_stream_pks = set()
                    # for node in all_licensed_nodes_qs:
                    #     final_stream_pks.add(node.pk)

                    #     # Efficiently retrieve and add all ancestors and descendants to the stream
                    #     ancestors = node.get_ancestors(include_self=False)
                    #     final_stream_pks.update([n.pk for n in ancestors])

                    #     descendants = node.get_descendants(include_self=False)
                    #     final_stream_pks.update([d.pk for d in descendants])

                    all_active_nodes_pk = list(all_licensed_nodes_qs)

                    
                    profile.academic_stream.set(all_active_nodes_pk)
                    
                    # --- 4b. PERMISSION ASSIGNMENT ---
                    all_perms = Permission.objects.filter(
                            licensepermission__license__in=active_licenses_qs
                        ).distinct()
                    
                    # Only add permissions if the user has a role that requires them (e.g., admin)
                    
                    for perm in all_perms:
                        # Note: The 'add' method automatically handles existence checks
                        new_user.user_permissions.add(perm)

                    new_user.save() # Save needed for permissions M2M set
                    profile.save()
                    
                    messages.success(request, f"Client Admin '{new_user.email}' and Organization '{org_profile.name}' created successfully.")
                    
                    # Redirect to a success page or the dashboard
                    return redirect(reverse('saas:organization_license_overview'))

            except Exception as e:
                # Log error and show user a message
                logger.error(f"Database transaction failed: {e}")
                messages.error(request, f"An unexpected error occurred during client creation. Details: {e}")
        
        # If forms were invalid, they will fall through and be re-rendered
    else:
        # GET request: initialize empty forms
        user_form = NewClientUserForm()
        print(orgId)
        org_assign_form = OrganizationAssignmentForm(org_id=orgId)

    context = {
        'page_title': page_title,
        'user_form': user_form,
        'org_assign_form': org_assign_form,
    }
    return render(request, 'create_user_and_organization.html', context)


@login_required
@staff_required
@permission_required('saas.add_organizationprofile', raise_exception=True)
def create_organization_and_admin_view(request):
    """ View to create a new OrganizationProfile and assign an EXISTING User (Client Admin) to it. """
    # ... implementation for existing user assignment ...
    # This is a placeholder as the full implementation was in the previous turn and is not the primary focus now.
    org_form = OrganizationProfileForm(prefix='org')
    user_assign_form = UserAssignmentForm(prefix='user')
    context = {'org_form': org_form, 'user_assign_form': user_assign_form, 'page_title': 'Create Client Organization & Assign Admin'}
    return render(request, 'create_user_and_organization.html', context)


@login_required
@staff_required
@permission_required('saas.view_organizationgroup',login_url='profile_update')
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

@login_required
@staff_required
@permission_required('saas.add_organizationgroup',login_url='profile_update')
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


@login_required
@staff_required
@permission_required('saas.change_organizationgroup',login_url='profile_update')
def edit_organization(request, pk):
    organization = get_object_or_404(OrganizationProfile, pk=pk)
    # Fetch grants using the correct related_name
    grants = organization.license_grants.all().order_by('-valid_until')

    # --- Fetch and Group Licensed Permissions ---
    # 1. Get all unique Permission IDs linked to the organization's LicenseGrants
    licensed_permission_ids = LicensePermission.objects.filter(
        license__organization_profile=organization
    ).values_list('permission_id', flat=True).distinct()

    # 2. Fetch the actual Permission objects and group them
    all_licensed_permissions = (
        Permission.objects.filter(id__in=licensed_permission_ids)
        .select_related('content_type')
        .order_by('content_type__app_label', 'name')
    )

    permissions_by_model = {}
    for perm in all_licensed_permissions:
        # Key: model name (e.g., 'course', 'question', 'user')
        model_name = perm.content_type.model
        if model_name not in permissions_by_model:
            permissions_by_model[model_name] = []
        permissions_by_model[model_name].append(perm)
    # --- End Fetch and Group Licensed Permissions ---


    # --- Organization Edit Logic ---
    if request.method == 'POST' and 'edit_org' in request.POST:
        org_form = OrganizationEditForm(request.POST, instance=organization)
        if org_form.is_valid():
            org_form.save()
            messages.success(request, f"Organization '{organization.name}' updated successfully! 🛠️")
            return redirect('saas:organization_edit', pk=pk)
        else:
            messages.error(request, "Error updating organization details.")
            # Note: license_form is no longer needed here
    
    # --- License Grant Logic (REMOVED / REDIRECTED) ---
    # The elif block for 'add_license' is completely removed.
    
    # --- GET Request (or form validation failed) ---
    org_form = OrganizationEditForm(instance=organization)
    # license_form is still initialized to avoid errors in the template's context passing, 
    # but it won't be used for submission here.
    license_form = LicenseGrantForm() 

    context = {
        'organization': organization,
        'org_form': org_form,
        'license_form': license_form, # Kept for safety if not fully removed in template
        'grants': grants, 
        'page_title': f"Edit: {organization.name}",
        'all_permissions_by_model': permissions_by_model, # NEW CONTEXT VARIABLE
    }
    return render(request, 'organization_edit.html', context)



@login_required
@staff_required
@permission_required('saas.view_usagelimit',login_url='profile_update')
def update_max_question_papers(request, org_id):
    """
    Allows an admin to update all usage limits (max users, max papers) 
    for a specific organization's subscription plan using a ModelForm.
    """
    organization = get_object_or_404(OrganizationProfile, id=org_id)
    
    # --- 1. Retrieve or Create UsageLimit ---
    # This handles the scenario where the UsageLimit might not exist yet
    try:
        usage_limit = organization.usage_limit
    except UsageLimit.DoesNotExist:
        # Create the UsageLimit if it doesn't exist (using defaults from the model)
        usage_limit = UsageLimit.objects.create(organization_profile=organization)
        
    if request.method == 'POST':
        # Initialize form with POST data and the existing instance
        form = UsageLimitForm(request.POST, instance=usage_limit)
        
        if form.is_valid():
            with transaction.atomic():
                # ModelForm handles validation and saving all fields
                updated_limit = form.save() 
                messages.success(request, f"Usage limits successfully updated for {organization.name}.")
            
            # Note: Using the original redirect name for compatibility with existing URLs
            return redirect('saas:update_max_question_papers', org_id=org_id)
        else:
            messages.error(request, "Please correct the errors below.")
            # If form is invalid, it falls through to the render step with error messages
    
    else:
        # GET request: Initialize the form with the existing instance data
        form = UsageLimitForm(instance=usage_limit)


    # --- 3. Handle GET Request or Invalid POST ---
    return render(request, 'update_usage_limit.html', {
        'organization': organization,
        'usage_limit': usage_limit,
        'form': form, # Passing the form object for template rendering
    })




