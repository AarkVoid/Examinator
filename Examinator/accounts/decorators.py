# users/decorators.py
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages

def institute_admin_required(function=None, redirect_field_name='next', login_url=None):
    """
    Decorator for views that checks that the user is logged in,
    is an 'admin' role, and has a profile linked to an institute.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and u.role == 'admin' and hasattr(u, 'profile') and u.profile.institute is not None,
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def institute_admin_or_super_required(function=None, redirect_field_name='next', login_url=None):
    """
    Decorator for views that checks that the user is logged in,
    and is either a superuser or an 'admin' role with an associated institute.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (u.is_superuser or (u.role == 'admin' and hasattr(u, 'profile') and u.profile.institute is not None)),
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator