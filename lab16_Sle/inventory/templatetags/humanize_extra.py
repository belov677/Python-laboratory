from django import template

register = template.Library()


@register.filter
def money(value):
    """12345.6 -> «12 345,60»."""
    try:
        return f"{float(value):,.2f}".replace(",", " ").replace(".", ",")
    except (TypeError, ValueError):
        return value
