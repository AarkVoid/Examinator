from django import template
from django.contrib.auth.models import Group
register = template.Library()

@register.filter
def lower_icon(value):
    """
    Maps Django message tags to Font Awesome icon names.
    """
    icon_map = {
        'success': 'check-circle',
        'error': 'times-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle',
        'debug': 'bug', # Optional: for debug messages
    }
    # Get the icon from the map, default to 'info-circle' if tag not found
    return icon_map.get(value.lower(), 'info-circle')



@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, [])



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

    # Anonymous users have no permissions.
    if not user.is_authenticated:
        return False

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

    # Get a set of the user's permissions for efficient checks
    user_permissions = user.get_all_permissions()

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


    

@register.filter
def is_institute_global(user,required_instotite_str):
    if not required_instotite_str:
        return False
    
    required_institute = [institute.strip() for institute in required_instotite_str.split(',')]
    return user.profile.institute.name in required_institute

    
