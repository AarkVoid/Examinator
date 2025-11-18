from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.urls import reverse
from django.contrib import messages
from .models import Profile

# Use this key to store the superuser's ID in the session
ORIGINAL_USER_KEY = 'original_user_id'

User = get_user_model()

# --- Helper Function for Impersonation Authorization ---
def can_impersonate(user):
    """
    Checks if the user has permission to impersonate others.
    (Superusers always can, plus users with 'admin' or 'teacher' roles).
    """
    return user.is_superuser or user.role in ['teacher', 'admin']

# --- Utility Views ---

@user_passes_test(can_impersonate, login_url='/')
def impersonate_user(request, user_id,pin=None):
    """
    Allows a superuser to log in as another user temporarily.
    The superuser's original ID is stored in the session.
    """
    # 1. Retrieve the target user
    try:
        target_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('user_list') 
    
    # Store the original superuser's PK locally before we proceed
    original_pk = request.user.pk


    # --- NEW PIN CHECK LOGIC ---
    # Only perform the PIN check if the current user is NOT a superuser
    if not request.user.is_superuser:
        if not pin:
            messages.error(request, "A security PIN is required to impersonate non-staff users.")
            # Redirect to a page where the PIN can be entered
            return redirect('user_list') 

        try:
            target_profile = target_user.profile
        except Profile.DoesNotExist:
            messages.error(request, "Target user profile missing the required security data.")
            return redirect('user_list')

        # SECURITY WARNING: This comparison uses the plaintext PIN from the database.
        # In production, use Django's check_password() after hashing the pin 
        # (e.g., using set_password() in the save method or form clean method).
        if not target_profile.impersonation_pin or target_profile.impersonation_pin != pin:
            messages.error(request, "Invalid security PIN provided.")
            return redirect('user_list')
    # --- END NEW PIN CHECK LOGIC ---
    
    # 2. Log in the target user
    # IMPORTANT: Explicitly specify the backend to avoid the ValueError 
    # and to ensure the login works correctly.
    login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')

    # 3. RE-ADD the original user ID immediately AFTER login()
    # Django's login() clears the session, so we must restore our key.
    request.session[ORIGINAL_USER_KEY] = original_pk
    
    # 4. Explicitly save the session (though often unnecessary after login, it's safer)
    request.session.save()
    
    messages.success(request, f"You are now impersonating {target_user.username}.")
    
    return redirect('OrgHome')



@user_passes_test(can_impersonate, login_url='/')
def impersonate_user_submission(request):
    """
    Handles POST request from the PIN modal to execute impersonation.
    This view now contains the full logic, ensuring an HttpResponse is always returned.
    """
    # 1. Define local redirect handler for clean failure paths
    org_pk = request.POST.get('org_pk')

    def redirect_failure(error_message):
        messages.error(request, error_message)
        if org_pk:
            # Redirects back to the user list for the specific organization
            return redirect(reverse('view_organization_users', kwargs={'org_pk': org_pk}))
        return redirect('OrgHome') # Fallback redirect

    # 2. Check method
    if request.method != 'POST':
        return redirect_failure("Invalid request method.")

    # 3. Extract data from POST
    user_id = request.POST.get('user_id')
    pin = request.POST.get('pin')

    if not user_id:
        return redirect_failure("Target user not specified.")

    # 4. Retrieve the target user
    try:
        target_user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return redirect_failure("User not found.")
    
    # Store the original authorized user's PK before potential session clear
    original_pk = request.user.pk

    # 5. PIN Check Logic (Bypassed for Superusers)
    if not request.user.is_superuser:
        if not pin:
            return redirect_failure("A security PIN is required to impersonate this user.")

        try:
            target_profile = target_user.profile
        except Profile.DoesNotExist:
            return redirect_failure("Target user profile missing the required security data.")

        # WARNING: Security check (should use target_profile.check_password(pin) in production)
        if not target_profile.impersonation_pin or target_profile.impersonation_pin != pin:
            return redirect_failure("Invalid security PIN provided.")

    # 6. Successful Login
    # IMPORTANT: Explicitly specify the backend
    login(request, target_user, backend='django.contrib.auth.backends.ModelBackend')

    # Restore the original user ID in the session after login() clears it
    request.session[ORIGINAL_USER_KEY] = original_pk
    request.session.save()
    
    messages.success(request, f"You are now impersonating {target_user.username}.")
    
    # 7. Success Redirect
    return redirect('OrgHome') 


def exit_impersonation(request):
    """
    Allows the impersonating user (who is currently the target user) to return 
    to their original superuser account.
    """
    # 1. Check if the session key exists
    original_user_id = request.session.get(ORIGINAL_USER_KEY)
    
    if not original_user_id:
        # Failsafe: if the key is missing, redirect to admin home
        messages.error(request, "Could not find original user session key.")
        return redirect('manage_users')

    # 2. Retrieve the original superuser object
    original_user = get_object_or_404(User, pk=original_user_id)

    # 3. Clear the original user's ID from the session (Do this before login)
    del request.session[ORIGINAL_USER_KEY]
    
    # 4. Log out the currently impersonated user (optional)
    # logout(request)
    
    # 5. Log the original superuser back in
    # FIX: Explicitly pass the backend to resolve the ValueError
    login(
        request, 
        original_user, 
        backend='django.contrib.auth.backends.ModelBackend' # <--- This is the key fix
    )
    
    messages.success(request, f"Returned to original account: {original_user.username}.")
    
    # 6. Redirect back to the admin dashboard
    return redirect('manage_users')