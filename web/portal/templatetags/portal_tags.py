from django import template

register = template.Library()


@register.filter
def score_points(value):
    """La salida del modelo es una puntuación; no una probabilidad calibrada."""
    try:
        return f"{float(value) * 100:.1f}"
    except (TypeError, ValueError):
        return "—"
