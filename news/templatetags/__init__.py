from django import template
from news.models import Category

register = template.Library()

@register.simple_tag
def get_categories():
    """
    Returns all Category objects (ordered by name).
    Usage in template: {% get_categories as categories_list %}
    """
    return Category.objects.order_by('name')
