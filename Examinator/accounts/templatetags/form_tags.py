# accounts/templatetags/form_tags.py

from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})


@register.filter
def lookup_by_pk(iterable, pk_value):
    """
    Looks up an item in an iterable (like a QuerySet or list of objects)
    by its primary key (pk) attribute.
    Usage: {{ my_list_of_objects|lookup_by_pk:object_id }}
    """
    if hasattr(iterable, '__iter__') and not isinstance(iterable, (str, bytes, dict)):
        for item in iterable:
            if hasattr(item, 'pk') and item.pk == pk_value:
                return item
    return None


@register.filter
def total_perms_in_app(models_dict):
    """Calculates total permissions across all models in an app dict."""
    total = 0
    for model_perms in models_dict.values():
        total += len(model_perms)
    return total




@register.filter
def capfirst(value):
    """Capitalizes the first letter of the value."""
    return str(value).capitalize()
