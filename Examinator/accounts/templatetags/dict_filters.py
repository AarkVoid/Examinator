from django import template
from django.contrib.auth.models import Permission
from datetime import datetime

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def find_perm_by_name(queryset, name):
    try:
        return queryset.get(name=name)
    except queryset.model.DoesNotExist:
        return None
    

@register.filter
def is_future(date):
    if not date:
        return True  # Treat None as permanent (future)
    return date > datetime.now().date()

@register.filter
def is_active(grant):
    if not grant.valid_until:
        return True  # No expiry date means permanent
    return grant.valid_until >= datetime.now().date()



@register.filter
def has_access(user, required_roles_str):
    """
    Checks if a user's role is in a list of required roles.
    A user with is_superuser=True always has access.

    Usage in template:
    {% load my_app_tags %}
    {% if request.user|has_access:"admin,main_admin" %}
        ...
    {% endif %}
    """
    if user.is_superuser:
        return True

    if not required_roles_str:
        return False

    required_roles = [role.strip() for role in required_roles_str.split(',')]
    return user.role in required_roles

@register.filter(name='check_permissions')
def check_permissions(user, value):
    # Superusers have all permissions.
    if user.is_superuser:
        return True
    
    # print(f"Checking permissions for user: {user.username}, role: {user.role}")

    # Anonymous users have no permissions.
    if not user.is_authenticated:
        print("User is not authenticated. Returning False.")
        return False
    
    # print(f"User is authenticated. Checking permissions: {value}")

    # Split the input string into permissions and the operator
    try:
        permissions_str, operator = value.split('|')
        required_permissions = {p.strip() for p in permissions_str.split(',')}
        operator = operator.strip().lower()
    except ValueError:
        # Handle malformed input, e.g., "quizzes.add_quiz" without an operator
        return False

    if not required_permissions:
        return False
    
    # print(f"Required permissions: {required_permissions}, Operator: {operator}")

    # Get a set of the user's permissions for efficient checks
    user_permissions = user.get_all_permissions()
    # print(f"User permissions: {user_permissions}")
    # Apply the logic based on the operator
    if operator == 'and':
        # Check if the user has ALL of the required permissions
        return required_permissions.issubset(user_permissions)
    elif operator == 'or':
        # Check if the user has ANY of the required permissions
        return not required_permissions.isdisjoint(user_permissions)
    else:
        # Unknown operator, return False
        return False