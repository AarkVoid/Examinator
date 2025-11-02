from django import template

register = template.Library()

@register.filter
def to_letter(value):
    """Convert number to letter (1=A, 2=B, etc.)"""
    try:
        return chr(64 + int(value))
    except (ValueError, TypeError):
        return 'A'