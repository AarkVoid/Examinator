# institute/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test,permission_required
from django.contrib import messages
from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Q, Prefetch # Import Prefetch if needed, not directly used in this snippet but good to have
from datetime import datetime

from .models import Institution, InstitutionPasskey, InstituteApplication,InstitutionGroup
from .forms import InstitutionForm, InstitutionPasskeyForm, InstituteApplicationForm

from django.http import JsonResponse
from education.models import StudentClass
from accounts.models import User 

from education.models import Board
from accounts.models import Profile
from django.db import transaction

# --- Helper Decorator for Superuser Access ---
def superuser_required(view_func):
    @login_required
    @user_passes_test(lambda u: u.is_superuser, login_url='/admin/login/') # Redirect non-superusers to admin login
    def _wrapped_view(request, *args, **kwargs):
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def list_institution_groups(request):
    """
    Displays a list of all existing Institution Groups.
    """
    groups = InstitutionGroup.objects.all().order_by('name')
    context = {
        'page_title': 'Institution Groups',
        'groups': groups,
    }
    return render(request, 'institute/list_groups.html', context)


def manage_institution_group(request, pk=None):
    """
    Handles the creation and editing of an InstitutionGroup.
    
    If `pk` is provided, it's an edit view.
    If `pk` is None, it's a create view.
    """
    if pk:
        group = get_object_or_404(InstitutionGroup, pk=pk)
    else:
        group = None
        
    if request.method == 'POST':
        try:
            with transaction.atomic():
                group_name = request.POST.get('group_name')
                description = request.POST.get('description')
                
                # Retrieve the comma-separated string from the hidden input
                board_ids_str = request.POST.get('boards', '')
                board_ids = [int(id) for id in board_ids_str.split(',') if id.strip()]

                if not group_name:
                    messages.error(request, 'Group name cannot be empty.')
                    # Re-render the form with user's data and error
                    context = {
                        'page_title': 'Edit Institution Group' if pk else 'Create New Institution Group',
                        'group': group,
                        'countries': Country.objects.all().order_by('name'),
                        'states': State.objects.none(),
                        'all_boards': Board.objects.all().order_by('name'),
                        'selected_board_ids': board_ids,
                    }
                    group.name = group_name
                    group.description = description
                    return render(request, 'institute/manage_group.html', context)

                group.name = group_name
                group.description = description
                
                # The fix is here: Save the object FIRST to get an ID.
                group.save()
                
                # THEN, set the Many-to-Many relationship.
                group.board.set(board_ids)
                
                messages.success(request, f'Group "{group.name}" saved successfully!')
                return redirect('list-institution-groups')
        
        except Exception as e:
            messages.error(request, f'An error occurred: {e}')
            return redirect('list-institution-groups')
    
    # GET request logic
    selected_board_ids = [board.id for board in group.board.all()] if pk else []
    
    context = {
        'page_title': 'Edit Institution Group' if pk else 'Create New Institution Group',
        'group': group,
        'countries': Country.objects.all().order_by('name'),
        'states': State.objects.none(),
        'boards': Board.objects.none(),
        'all_boards': Board.objects.all().order_by('name'),
        'selected_board_ids': selected_board_ids,
    }
    return render(request, 'institute/manage_group.html', context)


def delete_institution_group(request, pk):
    """
    Deletes a single institution group object.
    """
    # Get the object or return a 404 if it doesn't exist
    group = get_object_or_404(InstitutionGroup, pk=int(pk))

    # Only allow POST requests for deletion to prevent CSRF issues
    try:
        group.delete()
        messages.success(request, f'Successfully deleted group: {group.name}.')
        # Redirect to the list view after successful deletion
        return redirect('list-institution-groups')
    except Exception as e:
        # If it's a GET request, we can render a confirmation page if needed,
        # but for a simple modal, we can just redirect back or show an error.
        messages.error(request, f'Invalid request for deletion. error is {e}')
    return redirect('list-institution-groups')


def institute_admin_or_superuser_required(view_func):
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user = request.user
        if user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check for institute admin role and associated institute
        # Ensure user.profile exists and institute is set before checking
        if hasattr(user, 'profile') and user.profile.institute and user.role == 'admin':
            return view_func(request, *args, **kwargs)
        
        # If not superuser or institute admin, redirect or raise forbidden
        messages.error(request, "You do not have permission to access this page.")
        return redirect('home') # Redirect to home or a permission denied page
    return _wrapped_view


# --- Institution Views (No changes here, kept for context) ---

@superuser_required
def institution_list(request):
    institutions = Institution.objects.all().order_by('name')
    context = {'institutions': institutions, 'page_title': 'Institutions List'}
    return render(request, 'institute_management/institution_list.html', context)


def institution_detail(request, pk):
    institution = get_object_or_404(Institution, pk=pk)
    passkeys = InstitutionPasskey.objects.filter(institution=institution).order_by('-valid_until')
    context = {'institution': institution, 'passkeys': passkeys, 'page_title': f'{institution.name} Details'}
    return render(request, 'institute_management/institution_detail.html', context)

@permission_required('institute.add_institution', raise_exception=True)
def institution_create(request):
    # Initialize context with empty data and errors for initial GET request
    context = {
        'page_title': 'Create New Institution',
        'data': {
            'name': '', 'code': '', 'address': '',
            'country_id': '', 'state_id': '', 'board_id': '',
            'Institute_group':request.user.profile.institute_group.name if request.user.profile.institute_group else '',
        },
        'errors': {},
        'countries': Country.objects.all().order_by('name'),
        'states': State.objects.none(), # Initially empty, populated by JS
        'boards': Board.objects.none(), # Initially empty, populated by JS
        'InstituteGroup': InstitutionGroup.objects.all().order_by('name')
    }

    if request.method == 'POST':
        # Get data directly from POST request
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        address = request.POST.get('address', '').strip()
        country_id = request.POST.get('country', '')
        state_id = request.POST.get('state', '')
        board_id = request.POST.get('board', '')
        group_name = request.POST.get('group_name','')

        # Store submitted data back to context for re-rendering if errors occur
        context['data'] = {
            'name': name, 'code': code, 'address': address,
            'country_id': country_id, 'state_id': state_id, 'board_id': board_id,
            'Institute_group':group_name,
        }

        # Manual Validation
        errors = {}
        if group_name !='' or group_name==None:
            group_instance, created = InstitutionGroup.objects.get_or_create(name=group_name)
            group_instance.board.set([board_id])
        else:
            errors['name'] = "Institution Group name is required."

        if not name:
            errors['name'] = "Institution name is required."
        if not code:
            errors['code'] = "Institution code is required."
        elif Institution.objects.filter(code=code).exists():
            errors['code'] = "An institution with this code already exists."
        
        # Validate board selection
        selected_board = None
        if board_id:
            try:
                selected_board = Board.objects.get(id=board_id)

            except Board.DoesNotExist:
                errors['board'] = "Invalid board selected."

        context['errors'] = errors

        if not errors:
            # If no errors, save the institution
            institution = Institution.objects.create(
                name=name,
                code=code,
                address=address,
                board=selected_board, # Assign the validated board object
                group = group_instance
            )
            messages.success(request, 'Institution created successfully!')
            return redirect('institution_list')
        else:
            messages.error(request, 'Please correct the errors below.')
            # If there are errors, ensure dropdowns are re-populated with valid options
            if country_id:
                context['states'] = State.objects.filter(country_id=country_id).order_by('name')
            if state_id:
                context['boards'] = Board.objects.filter(location_id=state_id).order_by('name')

    # For initial GET request or POST with errors, ensure countries are loaded
    context['countries'] = Country.objects.all().order_by('name')
    return render(request, 'institute_management/institution_form.html', context)


@permission_required('institute.change_institution', raise_exception=True)
def institution_update(request, pk):
    institution = get_object_or_404(Institution, pk=pk)
    
    # Pre-populate data for the form based on the existing institution
    initial_country = institution.board.location.country if institution.board and institution.board.location else None
    initial_state = institution.board.location if institution.board and institution.board.location else None
    initial_board = institution.board
    initial_institute_group = institution.group
    context = {
        'page_title': f'Update {institution.name}',
        'institution': institution, # Pass the instance itself for other details
        'data': {
            'name': institution.name,
            'code': institution.code,
            'address': institution.address,
            'country_id': initial_country.id if initial_country else '',
            'state_id': initial_state.id if initial_state else '',
            'board_id': initial_board.id if initial_board else '',
            'Institute_group':initial_institute_group.name if initial_institute_group else '',
        },
        'errors': {},
        'countries': Country.objects.all().order_by('name'),
        'states': State.objects.filter(country=initial_country).order_by('name') if initial_country else State.objects.none(),
        'boards': Board.objects.filter(location=initial_state).order_by('name') if initial_state else Board.objects.none(),
        'InstituteGroup' : InstitutionGroup.objects.all().order_by('name'),
    }

    

    if request.method == 'POST':
        # Get data directly from POST request
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        address = request.POST.get('address', '').strip()
        country_id = request.POST.get('country', '')
        state_id = request.POST.get('state', '')
        board_id = request.POST.get('board', '')
        group_name = request.POST.get('group_name','')
        print(' group_name :',group_name)

        # Update data in context for re-rendering if errors occur
        context['data'] = {
            'name': name, 'code': code, 'address': address,
            'country_id': country_id, 'state_id': state_id, 'board_id': board_id,
            'Institute_group':group_name,
        }

        # Manual Validation
        errors = {}

        if group_name !='' or group_name==None:
            group_instance = InstitutionGroup.objects.filter(name=group_name).first()
            if not group_instance:
                errors['group'] = "Institution Group name does not exist."
        else:
            group_instance = None

        if not name:
            errors['name'] = "Institution name is required."
        # Check if code is unique, excluding the current institution's code
        if not code:
            errors['code'] = "Institution code is required."
        elif Institution.objects.filter(code=code).exclude(pk=pk).exists():
            errors['code'] = "An institution with this code already exists."
        
        # Validate board selection
        selected_board = None
        if board_id:
            try:
                selected_board = Board.objects.get(id=board_id)
                # Further validate if the selected board belongs to the selected state (if state was provided)
                if state_id and selected_board.location_id != int(state_id):
                    errors['board'] = "Selected board does not belong to the chosen state."
            except Board.DoesNotExist:
                errors['board'] = "Invalid board selected."
        else:
            pass # Board is optional

        context['errors'] = errors

        if not errors:
            board_changed = institution.board != selected_board

            # If no errors, update the institution
            institution.name = name
            institution.code = code
            institution.address = address
            institution.board = selected_board # Assign the validated board object
            institution.group = group_instance
            institution.save()

            if board_changed:
                profiles = Profile.objects.filter(institute=institution)
                for profile in profiles:
                    profile.board = selected_board
                    profile.save()

            messages.success(request, f'Institution "{institution.name}" updated successfully!')
            return redirect('institution_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors below.')
            # If there are errors, ensure dropdowns are re-populated with valid options
            if country_id:
                context['states'] = State.objects.filter(country_id=country_id).order_by('name')
            if state_id:
                context['boards'] = Board.objects.filter(location_id=state_id).order_by('name')

    return render(request, 'institute_management/institution_form.html', context)


@permission_required('institute.delete_institution', raise_exception=True)
def institution_delete(request, pk):
    institution = get_object_or_404(Institution, pk=pk)
    if request.method == 'POST':
        institution.delete()
        messages.success(request, f'Institution "{institution.name}" deleted successfully!')
        return redirect('institution_list')
    context = {'object': institution, 'page_title': f'Delete {institution.name}'}
    return render(request, 'institute_management/institution_confirm_delete.html', context)


# --- InstitutionPasskey Views (No changes here, kept for context) ---

@permission_required('institute.view_institutionpasskey', raise_exception=True)
def passkey_list(request):
    user = request.user
    if user.is_superuser:
        passkeys = InstitutionPasskey.objects.all().order_by('institution__name', '-valid_until')
    elif user.role=='main_admin':
        user_institute_group = request.user.profile.institute_group
        passkeys = InstitutionPasskey.objects.filter(institution__group=user_institute_group).order_by('institution__name', '-valid_until')
    else:
        user_institute = request.user.profile.institute
        passkeys = InstitutionPasskey.objects.filter(institution=user_institute).order_by('institution__name', '-valid_until')
    context = {'passkeys': passkeys, 'page_title': 'Passkeys List'}
    return render(request, 'institute_management/institutionpasskey_list.html', context)

@permission_required('institute.view_institutionpasskey', raise_exception=True)
def passkey_detail(request, pk):
    passkey = get_object_or_404(InstitutionPasskey, pk=pk)
    context = {'passkey': passkey, 'page_title': f'Passkey for {passkey.institution.name}'}
    return render(request, 'institute_management/institutionpasskey_detail.html', context)



@permission_required({'institute.add_institutionpasskey'},raise_exception=True)
def passkey_create(request):
    # 'context' will only hold 'form' and 'page_title'
    context = {} 
    user = request.user
    
    if request.method == 'POST':
        # Create a mutable copy of the POST data
        post_data = request.POST.copy()

        # Check if the user is an institute admin and associate with their institution
        if user.role == 'admin' and hasattr(user, 'profile') and user.profile.institute:
            # Manually set the institution ID from the admin's profile
            post_data['institution'] = user.profile.institute.id
            form = InstitutionPasskeyForm(post_data)
        else:
            # For superusers, or if admin has no institute, use raw POST data
            form = InstitutionPasskeyForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, 'Passkey created successfully!')
            return redirect('passkey_list')
        else:
            messages.error(request, 'Please correct the errors in the form.')
            print(form.errors) # For debugging
    else: # GET request
        form = InstitutionPasskeyForm()
        # Filter institutions for the dropdown for institute admins
        if user.role == 'admin' and hasattr(user, 'profile') and user.profile.institute:
            form.fields['institution'].queryset = Institution.objects.filter(id=user.profile.institute.id)
            # If there's only one institution for an admin, pre-select it
            if form.fields['institution'].queryset.count() == 1:
                form.initial['institution'] = form.fields['institution'].queryset.first()
        elif user.role == 'main_admin':
            user_institute_group = request.user.profile.institute_group
            form.fields['institution'].queryset = Institution.objects.filter(group=user_institute_group)
            # If there's only one institution for an admin, pre-select it
            if form.fields['institution'].queryset.count() == 1:
                form.initial['institution'] = form.fields['institution'].queryset.first()
        
    context = {'form': form, 'page_title': 'Create New Passkey'}
    return render(request, 'institute_management/institutionpasskey_form.html', context)




@permission_required({'institute.change_institutionpasskey'},raise_exception=True)
def passkey_update(request, pk):
    passkey = get_object_or_404(InstitutionPasskey, pk=pk)

    # Security check: Institute admin can only edit their institute's passkeys
    if not request.user.is_superuser and passkey.institution != request.user.profile.institute:
        messages.error(request, "You do not have permission to edit this passkey.")
        return redirect('passkey_list')

    if request.method == 'POST':
        form = InstitutionPasskeyForm(request.POST, instance=passkey)
        # Ensure institution field is not changed by unauthorized users
        if not request.user.is_superuser:
            # Remove institution from POST data to prevent tampering
            # Or ensure it's the same as the original passkey's institution
            if 'institution' in form.changed_data and form.cleaned_data['institution'] != passkey.institution:
                 messages.error(request, "You cannot change the institution for this passkey.")
                 return redirect('passkey_detail', pk=pk) # Or re-render with error
            # If we want to strictly prevent changing institution via form, we could do:
            # form.fields['institution'].widget.attrs['disabled'] = 'disabled'
            # (But this requires special handling when saving, often setting instance.institution directly)
            # For simplicity, we'll let the form clean it, and the above check validates.
            
        if form.is_valid():
            form.save()
            messages.success(request, 'Passkey updated successfully!')
            return redirect('passkey_detail', pk=pk)
        else:
            messages.error(request, 'Please correct the errors in the form.')
            print(form.errors) # For debugging
    else:
        form = InstitutionPasskeyForm(instance=passkey)
        # If admin, restrict institution choices or disable field
        if not request.user.is_superuser:
            form.fields['institution'].queryset = Institution.objects.filter(id=passkey.institution.id)
            form.fields['institution'].widget.attrs['disabled'] = 'disabled' # Disable field for view
            
    context = {'form': form, 'passkey': passkey, 'page_title': f'Update Passkey for {passkey.institution.name}'}
    return render(request, 'institute_management/institutionpasskey_form.html', context)



@permission_required({'institute.delete_institutionpasskey'},raise_exception=True)
def passkey_delete(request, pk):
    passkey = get_object_or_404(InstitutionPasskey, pk=pk)

    # Security check: Institute admin can only delete their institute's passkeys
    if not request.user.is_superuser and passkey.institution != request.user.profile.institute:
        messages.error(request, "You do not have permission to delete this passkey.")
        return redirect('passkey_list')

    if request.method == 'POST':
        passkey.delete()
        messages.success(request, 'Passkey deleted successfully!')
        return redirect('passkey_list')
    context = {'object': passkey, 'page_title': f'Delete Passkey for {passkey.institution.name}'}
    return render(request, 'institute_management/institutionpasskey_confirm_delete.html', context)


# --- Institute Application Views ---

@login_required
def apply_for_institute(request):
    user_profile = request.user.profile
    # Check for *any* pending application by this user
    existing_pending_application = InstituteApplication.objects.filter(user=request.user, status='pending').first()
    
    # Get the user's current institute for pre-selection in the form
    current_user_institute = user_profile.institute 

    if request.method == 'POST':
        # Pass the current_user_institute to the form (even for POST, for re-rendering if errors)
        form = InstituteApplicationForm(request.POST, user_institute=current_user_institute)
        if form.is_valid():
            institution = form.cleaned_data['institution']
            passkey_attempt = form.cleaned_data['passkey_attempt']

            # Check if there's already a pending application to prevent multiple pending ones
            if existing_pending_application:
                messages.warning(request, f"You already have a pending application to {existing_pending_application.institution.name}. Please wait for it to be reviewed before submitting another.")
                return redirect('student_applications_status') # Redirect to their status page

            # Validate passkey (your existing logic here)
            passkey_valid = False
            if InstitutionPasskey.objects.filter(
                institution=institution,
                valid_until__gte=timezone.now().date()
            ).exists():
                if InstitutionPasskey.objects.filter(
                    institution=institution, 
                    passkey=passkey_attempt, 
                    valid_until__gte=timezone.now().date()
                ).exists():
                    passkey_valid = True
                else:
                    messages.error(request, "The passkey entered is incorrect or expired for the selected institution. A valid passkey is required.")
                    # Re-render form with errors, ensure current_user_institute is passed again
                    context = {
                        'form': form, # form with errors
                        'page_title': 'Apply for Institution',
                        'current_institute': current_user_institute, # Pass current institute status
                        'pending_application': existing_pending_application,
                    }
                    return render(request, 'institute_management/apply_for_institute_form.html', context)
            else:
                passkey_valid = True

            if passkey_valid:
                InstituteApplication.objects.create(
                    user=request.user,
                    institution=institution,
                    passkey_attempt=passkey_attempt,
                    status='pending'
                )
                messages.success(request, f"Your application to {institution.name} has been submitted. It is pending review.")
                return redirect('student_applications_status')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        # For GET request, instantiate the form with the user's current institute
        form = InstituteApplicationForm(user_institute=current_user_institute)
    
    context = {
        'form': form,
        'page_title': 'Apply for Institution',
        'current_institute': current_user_institute, # Pass current institute status
        'pending_application': existing_pending_application, # Pass pending application status
    }
    return render(request, 'institute_management/apply_for_institute_form.html', context)



@login_required
def student_applications_status(request):
    """
    Allows a student to view the status of all their submitted applications.
    """
    user_applications = InstituteApplication.objects.filter(user=request.user).order_by('-applied_at')
    context = {
        'user_applications': user_applications,
        'application_count': user_applications.count(),
        'page_title': 'My Institute Applications'
    }
    return render(request, 'institute_management/student_applications_status.html', context)



@permission_required('institute.can_mangage_instituteapplication', raise_exception=True)
def manage_applications(request):
    if request.user.is_superuser:
        applications = InstituteApplication.objects.filter(status='pending').select_related(
            'user', 'user__profile', 'institution'
        ).order_by('applied_at')
    elif request.user.role == 'main_admin':
        user_institute_group = request.user.profile.institute_group
        
        applications = InstituteApplication.objects.filter(
            institution__group=user_institute_group, 
            status='pending'
        ).select_related(
            'user', 'user__profile', 'institution'
        ).order_by('applied_at')
    else: # Institute Admin
        user_institute = request.user.profile.institute
        applications = InstituteApplication.objects.filter(
            institution=user_institute, 
            status='pending'
        ).select_related(
            'user', 'user__profile', 'institution'
        ).order_by('applied_at')
    
    context = {
        'applications': applications,
        'page_title': 'Manage Institute Applications'
    }
    return render(request, 'institute_management/manage_applications.html', context)

@institute_admin_or_superuser_required
@permission_required('institute.can_aprove_instituteapplication', raise_exception=True)
def approve_application(request, pk):
    application = get_object_or_404(InstituteApplication, pk=pk, status='pending')

    # Security check: Institute admin can only approve applications for their institute
    if not request.user.is_superuser and application.institution != request.user.profile.institute:
        messages.error(request, "You do not have permission to approve applications for this institution.")
        return redirect('manage_applications')

    if request.method == 'POST': 
        # Update user's profile
        applicant_profile = application.user.profile
        
        # Check if the user is already assigned to an institute
        if applicant_profile.institute:
            messages.info(request, f"{application.user.username}'s previous institute ({applicant_profile.institute.name}) has been changed to {application.institution.name}.")
        
        applicant_profile.institute = application.institution
        applicant_profile.board = application.institution.board
        applicant_profile.save() # Save profile change

        # Update application status
        application.status = 'approved'
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save()

        messages.success(request, f"Application by {application.user.username} for {application.institution.name} approved successfully!")
    
    return redirect('manage_applications')

@institute_admin_or_superuser_required
@permission_required('institute.can_reject_instituteapplication', raise_exception=True)
def reject_application(request, pk):
    """
    Rejects an institute application.
    Marks the application as rejected.
    """
    application = get_object_or_404(InstituteApplication, pk=pk, status='pending')

    # Security check: Institute admin can only reject applications for their institute
    if not request.user.is_superuser and application.institution != request.user.profile.institute:
        messages.error(request, "You do not have permission to reject applications for this institution.")
        return redirect('manage_applications')

    if request.method == 'POST': 
        application.status = 'rejected'
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save() 
        messages.info(request, f"Application by {application.user.username} for {application.institution.name} rejected.")
    
    return redirect('manage_applications')


def get_classes_for_institution(request):
    institution_id = request.GET.get('institution_id')
    classes = []
    if institution_id:
        # Get all users belonging to this institution
        users_in_institution = User.objects.filter(profile__institute_id=institution_id)
        # Get all unique classes associated with these users' profiles
        # Note: This assumes Profile.class_field is correctly linked to StudentClass
        class_ids = users_in_institution.values_list('profile__class_field', flat=True).distinct()
        classes = StudentClass.objects.filter(id__in=class_ids).values('id', 'name').order_by('name')
    return JsonResponse({'classes': list(classes)})



@institute_admin_or_superuser_required
@permission_required('institute.view_instituteapplication', raise_exception=True)
def application_detail(request, pk):
    application = get_object_or_404(
        InstituteApplication.objects.select_related(
            'user', 'user__profile', 'institution', 'reviewed_by'
        ),
        pk=pk
    )

    profile = application.user.profile
    current_institute = profile.institute
    applied_institute = application.institution

    user_applications = InstituteApplication.objects.filter(user=application.user).order_by('-applied_at')

    context = {
        'application': application,
        'user_profile': profile,
        'user': application.user,
        'current_institute': current_institute,
        'applied_institute': applied_institute,
        'reviewer': application.reviewed_by,
        'page_title': f"Application Detail - {application.user.username}",
        'applications':user_applications,
    }
    return render(request, 'institute_management/application_detail.html', context)




def manage_institution_group_view(request, group_id):
    """
    Allows a main_admin to view and remove institutions from a specific group.
    """
    # Use get_object_or_404 for a clean way to handle non-existent groups
    group = get_object_or_404(InstitutionGroup, pk=group_id)

    if request.method == 'POST':
        # Check if the 'remove_institution' action was requested
        institution_id = request.POST.get('institution_id')
        if institution_id:
            try:
                institution_to_remove = get_object_or_404(Institution, pk=institution_id)
                
                # Set the institution's group to None
                institution_to_remove.group = None
                institution_to_remove.save()
                
                # Django's post_save signal on Institution will handle updating Profiles
                messages.success(request, f'Successfully removed "{institution_to_remove.name}" from the group.')
            except Exception as e:
                messages.error(request, f'An error occurred: {e}')
        
        return redirect('manage_institution_group', group_id=group.pk)

    # For a GET request, retrieve all institutions for the group
    institutions = group.institutionGroup.all().order_by('name')

    context = {
        'group': group,
        'institutions': institutions,
        'page_title': f'Manage {group.name}'
    }
    return render(request, 'institute/manage_institution_group.html', context)
