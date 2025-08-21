from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def metric_format(value, fmt_type):
    """
    Универсальный фильтр для форматирования метрик.
    
    Использование:
    {{ value|metric_format:"currency" }}     -> $12,345.67
    {{ value|metric_format:"percentage" }}   -> 12.50%
    {{ value|metric_format:"multiple" }}     -> 1.25x
    {{ value|metric_format:"decimal" }}      -> 1.25
    """
    if value is None:
        return "-"
    
    try:
        float_value = float(value)
        
        if fmt_type == "currency":
            return f"${float_value:,.2f}"
        elif fmt_type == "percentage":
            return f"{float_value * 100:.2f}%"
        elif fmt_type == "multiple":
            return f"{float_value:.2f}x"
        elif fmt_type == "decimal":
            return f"{float_value:.2f}"
        else:
            return str(value)
    except (ValueError, TypeError):
        return "-"

@register.filter
def format_currency(value):
    """Форматирует как валюту с символом $"""
    if value is None:
        return "-"
    try:
        return f"${float(value):,.2f}"
    except:
        return "-"

@register.filter
def format_percentage(value):
    """Форматирует десятичное число как процент с 2 знаками"""
    if value is None:
        return "-"
    try:
        return f"{float(value) * 100:.2f}%"
    except:
        return "-"

@register.filter
def format_multiple(value):
    """Форматирует как множитель с 'x'"""
    if value is None:
        return "-"
    try:
        return f"{float(value):.2f}x"
    except:
        return "-"

# 🔧 НОВЫЕ ПРОСТЫЕ ФИЛЬТРЫ для таблицы
@register.filter
def currency(value):
    """Простой фильтр для валют без символа $ (для таблицы с $ в заголовке)"""
    if value is None or value == 0:
        return "-"
    try:
        return f"{float(value):,.2f}"
    except:
        return "-"

@register.filter
def multiple(value):
    """Простой фильтр для множителей без символа x (для таблицы с x в заголовке)"""
    if value is None or value == 0:
        return "-"
    try:
        return f"{float(value):.2f}"
    except:
        return "-"

# 🔧 НОВЫЙ ФИЛЬТР для процентов БЕЗ символа %
@register.filter
def percentage_value(value):
    """Конвертирует 0.2267 в 22.67 (БЕЗ символа % для таблицы с % в заголовке)"""
    if value is None:
        return "-"
    try:
        return f"{float(value) * 100:.2f}"
    except:
        return "-"

@register.filter
def safe_call(value):
    """Безопасно вызывает функцию, если value является callable"""
    try:
        return value() if callable(value) else value
    except:
        return "-"

@register.filter
def default_if_none(value, default="-"):
    """Возвращает default если value None"""
    return default if value is None else value

@register.simple_tag
def format_metric(value, metric_type):
    """
    Тег для форматирования метрик с автоматическим определением типа.
    
    Использование:
    {% format_metric project.xirr "xirr" %}
    {% format_metric project.total_invested "currency" %}
    """
    if value is None:
        return mark_safe("-")
    
    try:
        float_value = float(value)
        
        if metric_type in ["xirr", "target_irr", "gap_to_target_irr", "percentage"]:
            return mark_safe(f"{float_value * 100:.2f}%")
        elif metric_type in ["dpi", "tvpi", "multiple"]:
            return mark_safe(f"{float_value:.2f}x")
        elif metric_type in ["currency", "invested", "returned", "nav", "xnpv", "estimated_return"]:
            return mark_safe(f"${float_value:,.2f}")
        else:
            return mark_safe(f"{float_value:.2f}")
    except (ValueError, TypeError):
        return mark_safe("-")