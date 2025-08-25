from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def get_item(obj, key):
    """Получить значение из объекта или словаря"""
    if hasattr(obj, 'get') and callable(obj.get):
        return obj.get(key)
    return getattr(obj, key, None)

@register.inclusion_tag('tables/base-table.html')
def portfolio_table(projects, table_classes=''):
    """Рендер таблицы портфолио с правильным выравниванием"""
    
    columns = [
        {
            'key': 'name',
            'label': 'Project Name',
            'type': 'project-name',
            'width': '200px',
            'css_classes': 'col-wide',
            'aria_label': 'Project Name'
        },
        {
            'key': 'status',
            'label': 'Status',
            'type': 'status',
            'width': '80px',
            'css_classes': 'col-narrow',
            'aria_label': 'Project Status'
        },
        {
            'key': 'start_date',
            'label': 'Start Date',
            'type': 'date',
            'width': '100px',
            'css_classes': 'col-hide-mobile',
            'aria_label': 'Start Date'
        },
        {
            'key': 'total_invested',
            'label': 'Total Invested (USD)',
            'type': 'currency',
            'format_type': 'currency',
            'width': '140px',
            'css_classes': 'col-wide',
            'aria_label': 'Total invested amount in USD'
        },
        {
            'key': 'total_returned',
            'label': 'Total Returned (USD)',
            'type': 'currency',
            'format_type': 'currency',
            'width': '140px',
            'css_classes': 'col-wide',
            'aria_label': 'Total returned amount in USD'
        },
        {
            'key': 'nav',
            'label': 'NAV (USD)',
            'type': 'currency',
            'format_type': 'currency',
            'width': '120px',
            'css_classes': 'col-wide',
            'aria_label': 'Net Asset Value in USD'
        },
        {
            'key': 'xirr',
            'label': 'XIRR (%)',
            'type': 'percentage',
            'format_type': 'percentage',
            'width': '80px',
            'css_classes': 'col-narrow',
            'aria_label': 'Extended Internal Rate of Return'
        },
        {
            'key': 'dpi',
            'label': 'DPI',
            'type': 'multiple',
            'format_type': 'multiple',
            'width': '80px',
            'css_classes': 'col-narrow',
            'aria_label': 'Distributions to Paid-In capital'
        },
        {
            'key': 'tvpi',
            'label': 'TVPI',
            'type': 'multiple',
            'format_type': 'multiple',
            'width': '80px',
            'css_classes': 'col-narrow',
            'aria_label': 'Total Value to Paid-In capital'
        },
        {
            'key': 'xnpv',
            'label': 'XNPV (USD)',
            'type': 'currency',
            'format_type': 'currency',
            'width': '120px',
            'css_classes': 'col-wide col-hide-mobile',
            'aria_label': 'Extended Net Present Value in USD'
        },
        {
            'key': 'estimated_return',
            'label': 'Est. Return (USD)',
            'type': 'currency',
            'format_type': 'currency',
            'width': '140px',
            'css_classes': 'col-wide col-hide-mobile',
            'aria_label': 'Estimated return in USD'
        }
    ]
    
    # Форматируем данные проектов
    rows = []
    for project in projects:
        rows.append({
            'name': project.name,
            'status': project.get_status_display(),
            'start_date': project.start_date.strftime('%b %d, %Y') if project.start_date else '-',
            'total_invested': project.get_total_invested(),
            'total_returned': project.get_total_returned(),
            'nav': project.nav,
            'xirr': project.get_xirr(),
            'dpi': project.get_dpi(),
            'tvpi': project.get_tvpi(),
            'xnpv': project.get_xnpv(),
            'estimated_return': project.estimated_return,
        })
    
    return {
        'columns': columns,
        'rows': rows,
        'table_classes': f'portfolio-table {table_classes}',
        'empty_message': 'No projects found'
    }

@register.inclusion_tag('tables/base-table.html')
def portfolio_summary_table(summary_data, table_classes=''):
    """Рендер сводной таблицы портфолио"""
    
    columns = [
        {
            'key': 'metric',
            'label': 'Metric',
            'type': 'text',
            'width': '200px',
            'css_classes': 'col-wide',
            'aria_label': 'Metric name'
        },
        {
            'key': 'all',
            'label': 'ALL',
            'type': 'currency',  # Динамически определяется
            'width': '120px',
            'css_classes': 'col-wide',
            'aria_label': 'All projects value'
        },
        {
            'key': 'active',
            'label': 'ACTIVE',
            'type': 'currency',  # Динамически определяется
            'width': '120px',
            'css_classes': 'col-wide',
            'aria_label': 'Active projects value'
        },
        {
            'key': 'ytd',
            'label': 'YTD',
            'type': 'currency',  # Динамически определяется
            'width': '120px',
            'css_classes': 'col-wide',
            'aria_label': 'Year-to-date value'
        }
    ]
    
    # Форматируем данные сводки
    rows = []
    for metric, values in summary_data.items():
        # Определяем тип форматирования
        if metric.upper() in ['XIRR', 'TARGET_IRR', 'GAP_TO_TARGET_IRR']:
            format_type = 'percentage'
        elif metric.upper() in ['DPI', 'TVPI']:
            format_type = 'multiple'
        elif metric.upper() in ['TOTAL_INVESTED', 'TOTAL_RETURNED', 'NAV', 'ESTIMATED_RETURN', 'XNPV']:
            format_type = 'currency'
        else:
            format_type = 'decimal'
        
        # Красивое название метрики
        metric_labels = {
            'XIRR': 'XIRR (%)',
            'TARGET_IRR': 'Target IRR (%)',
            'GAP_TO_TARGET_IRR': 'Gap to Target IRR (%)',
            'TOTAL_INVESTED': 'Total Invested (USD)',
            'TOTAL_RETURNED': 'Total Returned (USD)',
            'NAV': 'NAV (USD)',
            'ESTIMATED_RETURN': 'Estimated Return (USD)',
            'XNPV': 'XNPV (USD)',
            'DPI': 'DPI',
            'TVPI': 'TVPI'
        }
        
        rows.append({
            'metric': metric_labels.get(metric.upper(), metric),
            'all': values.get('ALL'),
            'active': values.get('ACTIVE'),
            'ytd': values.get('YTD'),
            '_format_type': format_type  # Служебное поле для определения формата
        })
    
    return {
        'columns': columns,
        'rows': rows,
        'table_classes': f'portfolio-summary {table_classes}',
        'empty_message': 'No portfolio data available'
    }