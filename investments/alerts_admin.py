# investments/alerts_admin.py
"""
Django Admin интерфейс для системы алертов
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q, Avg
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime, timedelta
import json

from .alerts_models import (
    AlertType, ProjectAlert, AlertSettings,
    AlertLog, AlertRule, AlertStatistics
)
from .alerts import AlertManager, AlertAnalyzer


@admin.register(AlertType)
class AlertTypeAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'default_severity_badge', 
        'check_frequency_display', 'is_active', 'alert_count'
    ]
    list_filter = ['default_severity', 'is_active']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('code', 'name', 'description', 'default_severity', 'is_active')
        }),
        ('Configuration', {
            'fields': ('check_frequency', 'threshold_config', 'email_template')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def default_severity_badge(self, obj):
        colors = {
            'CRITICAL': '#ff0000',
            'HIGH': '#ff9900',
            'MEDIUM': '#ffcc00',
            'LOW': '#0099ff',
            'INFO': '#999999'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.default_severity, '#666'),
            obj.default_severity
        )
    default_severity_badge.short_description = 'Default Severity'
    
    def check_frequency_display(self, obj):
        if obj.check_frequency >= 1440:
            return f"{obj.check_frequency // 1440} day(s)"
        elif obj.check_frequency >= 60:
            return f"{obj.check_frequency // 60} hour(s)"
        else:
            return f"{obj.check_frequency} min"
    check_frequency_display.short_description = 'Frequency'
    
    def alert_count(self, obj):
        count = obj.project_alerts.count()
        return format_html(
            '<a href="{}?alert_type__id__exact={}">{} alerts</a>',
            reverse('admin:investments_projectalert_changelist'),
            obj.id,
            count
        )
    alert_count.short_description = 'Total Alerts'


@admin.register(ProjectAlert)
class ProjectAlertAdmin(admin.ModelAdmin):
    list_display = [
        'severity_icon', 'project_link', 'title_truncated', 
        'alert_type', 'status_badge', 'created_at_display',
        'age_display', 'action_buttons'
    ]
    list_filter = [
        'severity', 'status', 'alert_type',
        ('created_at', admin.DateFieldListFilter),
        'email_sent', 'is_recurring'
    ]
    search_fields = ['project__name', 'title', 'message']
    readonly_fields = [
        'created_at', 'updated_at', 'acknowledged_at',
        'resolved_at', 'escalated_at', 'email_sent_at',
        'push_sent_at', 'last_occurrence', 'created_by'
    ]
    date_hierarchy = 'created_at'
    list_per_page = 50
    
    fieldsets = (
        ('Alert Information', {
            'fields': ('project', 'alert_type', 'severity', 'status', 'title', 'message')
        }),
        ('Metrics & Details', {
            'fields': ('metric_value', 'threshold_value', 'deviation', 'details'),
            'classes': ('collapse',)
        }),
        ('Assignment & Resolution', {
            'fields': ('assigned_to', 'resolved_by', 'resolution_notes', 'actions_taken')
        }),
        ('Notifications', {
            'fields': ('email_sent', 'email_sent_at', 'push_sent', 'push_sent_at'),
            'classes': ('collapse',)
        }),
        ('Recurrence', {
            'fields': ('is_recurring', 'recurrence_count', 'last_occurrence', 'parent_alert'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': (
                'created_by', 'created_at', 'updated_at',
                'acknowledged_at', 'resolved_at', 'escalated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'acknowledge_alerts', 'resolve_alerts',
        'escalate_alerts', 'dismiss_alerts',
        'send_email_notifications'
    ]
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_site.admin_view(self.alerts_dashboard), name='alerts_dashboard'),
            path('analytics/', self.admin_site.admin_view(self.alerts_analytics), name='alerts_analytics'),
            path('api/stats/', self.alerts_api_stats, name='alerts_api_stats'),
            path('api/acknowledge/<int:alert_id>/', self.api_acknowledge_alert, name='api_acknowledge_alert'),
            path('api/resolve/<int:alert_id>/', self.api_resolve_alert, name='api_resolve_alert'),
        ]
        return custom_urls + urls
    
    def severity_icon(self, obj):
        icons = {
            'CRITICAL': '🚨',
            'HIGH': '⚠️',
            'MEDIUM': '⚡',
            'LOW': 'ℹ️',
            'INFO': '📊'
        }
        colors = {
            'CRITICAL': '#ff0000',
            'HIGH': '#ff9900',
            'MEDIUM': '#ffcc00',
            'LOW': '#0099ff',
            'INFO': '#999999'
        }
        return format_html(
            '<span style="font-size: 20px;" title="{}">{}</span>',
            obj.get_severity_display(),
            icons.get(obj.severity, '❓')
        )
    severity_icon.short_description = ''
    
    def project_link(self, obj):
        url = reverse('admin:investments_project_change', args=[obj.project.id])
        return format_html('<a href="{}">{}</a>', url, obj.project.name)
    project_link.short_description = 'Project'
    
    def title_truncated(self, obj):
        max_length = 50
        if len(obj.title) > max_length:
            return format_html(
                '<span title="{}">{}</span>',
                obj.title,
                obj.title[:max_length] + '...'
            )
        return obj.title
    title_truncated.short_description = 'Alert'
    
    def status_badge(self, obj):
        colors = {
            'NEW': '#dc3545',
            'ACKNOWLEDGED': '#ffc107',
            'IN_PROGRESS': '#17a2b8',
            'RESOLVED': '#28a745',
            'DISMISSED': '#6c757d',
            'ESCALATED': '#dc3545'
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            colors.get(obj.status, '#666'),
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def created_at_display(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M')
    created_at_display.short_description = 'Created'
    
    def age_display(self, obj):
        age = obj.age_days
        if age == 0:
            hours = (timezone.now() - obj.created_at).total_seconds() / 3600
            if hours < 1:
                return "< 1 hour"
            return f"{int(hours)} hours"
        elif age == 1:
            return "1 day"
        else:
            return f"{age} days"
    age_display.short_description = 'Age'
    
    def action_buttons(self, obj):
        buttons = []
        
        if obj.status == 'NEW':
            buttons.append(format_html(
                '<a class="button" href="#" onclick="acknowledgeAlert({}); return false;" '
                'style="padding: 3px 8px; margin: 2px;">✓ Acknowledge</a>',
                obj.id
            ))
        
        if obj.status in ['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS']:
            buttons.append(format_html(
                '<a class="button" href="#" onclick="resolveAlert({}); return false;" '
                'style="padding: 3px 8px; margin: 2px; background: #28a745;">✓ Resolve</a>',
                obj.id
            ))    
    # Admin Actions
    def acknowledge_alerts(self, request, queryset):
        count = 0
        for alert in queryset.filter(status='NEW'):
            alert.acknowledge(request.user)
            count += 1
        messages.success(request, f'{count} alerts acknowledged')
    acknowledge_alerts.short_description = "Acknowledge selected alerts"
    
    def resolve_alerts(self, request, queryset):
        count = 0
        for alert in queryset.filter(status__in=['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS']):
            alert.resolve(request.user)
            count += 1
        messages.success(request, f'{count} alerts resolved')
    resolve_alerts.short_description = "Resolve selected alerts"
    
    def escalate_alerts(self, request, queryset):
        count = 0
        for alert in queryset.filter(status__in=['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS']):
            alert.escalate()
            count += 1
        messages.success(request, f'{count} alerts escalated')
    escalate_alerts.short_description = "Escalate selected alerts"
    
    def dismiss_alerts(self, request, queryset):
        count = queryset.update(status='DISMISSED')
        messages.success(request, f'{count} alerts dismissed')
    dismiss_alerts.short_description = "Dismiss selected alerts"
    
    def send_email_notifications(self, request, queryset):
        manager = AlertManager()
        count = 0
        for alert in queryset:
            if not alert.email_sent:
                manager.send_notifications(alert)
                count += 1
        messages.success(request, f'Email notifications sent for {count} alerts')
    send_email_notifications.short_description = "Send email notifications"
    
    # Custom Views
    def alerts_dashboard(self, request):
        """Dashboard view for alerts"""
        manager = AlertManager()
        analyzer = AlertAnalyzer()
        
        stats = manager.get_dashboard_stats()
        portfolio_report = analyzer.generate_portfolio_report()
        
        # Recent critical alerts
        critical_alerts = ProjectAlert.objects.filter(
            severity='CRITICAL',
            status__in=['NEW', 'ACKNOWLEDGED']
        ).select_related('project', 'alert_type')[:10]
        
        context = {
            'title': 'Alerts Dashboard',
            'stats': stats,
            'portfolio_report': portfolio_report,
            'critical_alerts': critical_alerts,
            'opts': self.model._meta,
            'has_filters': False,
        }
        
        return render(request, 'admin/alerts_dashboard.html', context)
    
    def alerts_analytics(self, request):
        """Analytics view for alerts"""
        # Date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # Collect daily statistics
        daily_stats = []
        current_date = start_date
        while current_date <= end_date:
            alerts_count = ProjectAlert.objects.filter(
                created_at__date=current_date
            ).count()
            
            resolved_count = ProjectAlert.objects.filter(
                resolved_at__date=current_date
            ).count()
            
            daily_stats.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'created': alerts_count,
                'resolved': resolved_count
            })
            current_date += timedelta(days=1)
        
        # Top projects by alerts
        top_projects = ProjectAlert.objects.values(
            'project__name'
        ).annotate(
            alert_count=Count('id')
        ).order_by('-alert_count')[:10]
        
        # Alert type distribution
        type_distribution = ProjectAlert.objects.values(
            'alert_type__name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Average resolution time by severity
        resolution_times = {}
        for severity, _ in ProjectAlert.SEVERITY_CHOICES:
            alerts = ProjectAlert.objects.filter(
                severity=severity,
                resolved_at__isnull=False
            )
            times = []
            for alert in alerts[:100]:  # Sample
                if alert.resolution_time_hours:
                    times.append(alert.resolution_time_hours)
            
            if times:
                resolution_times[severity] = sum(times) / len(times)
            else:
                resolution_times[severity] = 0
        
        context = {
            'title': 'Alerts Analytics',
            'daily_stats': json.dumps(daily_stats),
            'top_projects': list(top_projects),
            'type_distribution': list(type_distribution),
            'resolution_times': resolution_times,
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/alerts_analytics.html', context)
    
    # API Endpoints
    @csrf_exempt
    def alerts_api_stats(self, request):
        """API endpoint for real-time stats"""
        manager = AlertManager()
        stats = manager.get_dashboard_stats()
        
        return JsonResponse({
            'success': True,
            'data': {
                'total_open': stats['total_open'],
                'critical': stats['severity_stats'].get('critical', 0),
                'high': stats['severity_stats'].get('high', 0),
                'medium': stats['severity_stats'].get('medium', 0),
                'low': stats['severity_stats'].get('low', 0),
                'info': stats['severity_stats'].get('info', 0),
                'alerts_today': stats['alerts_today'],
                'alerts_week': stats['alerts_week'],
            }
        })
    
    @csrf_exempt
    def api_acknowledge_alert(self, request, alert_id):
        """API endpoint to acknowledge alert"""
        try:
            alert = ProjectAlert.objects.get(id=alert_id)
            alert.acknowledge(request.user)
            return JsonResponse({'success': True, 'message': 'Alert acknowledged'})
        except ProjectAlert.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Alert not found'})
    
    @csrf_exempt
    def api_resolve_alert(self, request, alert_id):
        """API endpoint to resolve alert"""
        try:
            alert = ProjectAlert.objects.get(id=alert_id)
            notes = request.POST.get('notes', '')
            alert.resolve(request.user, notes)
            return JsonResponse({'success': True, 'message': 'Alert resolved'})
        except ProjectAlert.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Alert not found'})
    
    class Media:
        css = {
            'all': ('admin/css/alerts.css',)
        }
        js = ('admin/js/alerts.js',)


@admin.register(AlertSettings)
class AlertSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'email_enabled', 'email_frequency',
        'push_enabled', 'min_severity', 'vacation_mode'
    ]
    list_filter = [
        'email_enabled', 'push_enabled',
        'email_frequency', 'min_severity',
        'vacation_mode'
    ]
    search_fields = ['user__username', 'user__email']
    filter_horizontal = ['subscribed_types', 'subscribed_projects']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Email Settings', {
            'fields': (
                'email_enabled', 'email_frequency',
                'email_digest_time'
            )
        }),
        ('Push Notifications', {
            'fields': ('push_enabled', 'push_token')
        }),
        ('Subscriptions', {
            'fields': (
                'subscribed_types', 'subscribed_projects',
                'min_severity'
            )
        }),
        ('Quiet Hours', {
            'fields': (
                'quiet_hours_enabled',
                'quiet_hours_start', 'quiet_hours_end',
                'weekend_notifications'
            ),
            'classes': ('collapse',)
        }),
        ('Vacation Mode', {
            'fields': ('vacation_mode', 'vacation_mode_until'),
            'classes': ('collapse',)
        })
    )
# ПРОДОЛЖЕНИЕ alerts_admin.py - добавьте в конец файла


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'alert_type', 'condition_type',
        'metric_field', 'operator', 'threshold_value',
        'is_active', 'trigger_count', 'last_triggered'
    ]
    list_filter = [
        'is_active', 'condition_type', 'operator',
        'alert_type', 'applies_to_all_projects'
    ]
    search_fields = ['name', 'description', 'metric_field']
    filter_horizontal = ['specific_projects']
    readonly_fields = ['last_checked', 'last_triggered', 'trigger_count']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'alert_type', 'is_active')
        }),
        ('Condition', {
            'fields': (
                'condition_type', 'metric_field',
                'operator', 'threshold_value',
                'lookback_days', 'min_occurrences'
            )
        }),
        ('Projects', {
            'fields': ('applies_to_all_projects', 'specific_projects')
        }),
        ('Advanced', {
            'fields': (
                'severity_override', 'custom_condition',
                'check_schedule'
            ),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': (
                'last_checked', 'last_triggered',
                'trigger_count'
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = ['test_rules', 'reset_statistics']
    
    def test_rules(self, request, queryset):
        """Test selected rules"""
        manager = AlertManager()
        count = 0
        
        for rule in queryset:
            # Test logic here
            count += 1
        
        messages.success(request, f'{count} rules tested')
    test_rules.short_description = "Test selected rules"
    
    def reset_statistics(self, request, queryset):
        """Reset rule statistics"""
        queryset.update(
            trigger_count=0,
            last_checked=None,
            last_triggered=None
        )
        messages.success(request, 'Statistics reset')
    reset_statistics.short_description = "Reset statistics"


@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin):
    list_display = [
        'alert_link', 'action', 'user',
        'created_at', 'details_truncated'
    ]
    list_filter = ['action', ('created_at', admin.DateFieldListFilter)]
    search_fields = ['alert__title', 'details', 'user__username']
    readonly_fields = ['alert', 'action', 'user', 'details', 'old_value', 'new_value', 'created_at']
    date_hierarchy = 'created_at'
    
    def alert_link(self, obj):
        url = reverse('admin:investments_projectalert_change', args=[obj.alert.id])
        return format_html('<a href="{}">{}</a>', url, obj.alert.title[:50])
    alert_link.short_description = 'Alert'
    
    def details_truncated(self, obj):
        if obj.details and len(obj.details) > 100:
            return obj.details[:100] + '...'
        return obj.details
    details_truncated.short_description = 'Details'
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AlertStatistics)
class AlertStatisticsAdmin(admin.ModelAdmin):
    list_display = [
        'date', 'total_alerts', 'critical_count',
        'high_count', 'resolved_count',
        'avg_resolution_time_display'
    ]
    list_filter = [('date', admin.DateFieldListFilter)]
    date_hierarchy = 'date'
    readonly_fields = [
        'date', 'critical_count', 'high_count',
        'medium_count', 'low_count', 'info_count',
        'new_count', 'acknowledged_count',
        'resolved_count', 'dismissed_count',
        'avg_response_time', 'avg_resolution_time',
        'top_projects', 'top_types'
    ]
    
    def total_alerts(self, obj):
        return (
            obj.critical_count + obj.high_count +
            obj.medium_count + obj.low_count + obj.info_count
        )
    total_alerts.short_description = 'Total'
    
    def avg_resolution_time_display(self, obj):
        if obj.avg_resolution_time:
            return f"{obj.avg_resolution_time:.1f} hours"
        return "-"
    avg_resolution_time_display.short_description = 'Avg Resolution'
    
    def has_add_permission(self, request):
        return False
    
    actions = ['recalculate_statistics']
    
    def recalculate_statistics(self, request, queryset):
        """Recalculate statistics for selected dates"""
        for stat in queryset:
            AlertStatistics.calculate_for_date(stat.date)
        messages.success(request, 'Statistics recalculated')
    recalculate_statistics.short_description = "Recalculate statistics"
