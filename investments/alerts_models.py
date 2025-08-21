# investments/alerts_models.py
"""
🚀 HEDGE FUND TRACKER v4.0 - СИСТЕМА АЛЕРТОВ
Модели для системы уведомлений и мониторинга инвестиционных проектов
"""

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import json


class AlertType(models.Model):
    """Типы алертов"""
    
    TYPE_CHOICES = [
        ('IRR_GAP', 'IRR Gap Alert'),
        ('NAV_DROP', 'NAV Drop Alert'),
        ('NPV_NEGATIVE', 'NPV Negative Alert'),
        ('DATA_QUALITY', 'Data Quality Alert'),
        ('TARGET_MISS', 'Target Miss Alert'),
        ('DRAWDOWN', 'Drawdown Alert'),
        ('SHARPE_DECLINE', 'Sharpe Ratio Decline'),
        ('DISTRIBUTION', 'New Distribution'),
        ('DATE_REMINDER', 'Important Date Reminder'),
        ('PORTFOLIO_RISK', 'Portfolio Risk Alert'),
        ('NO_UPDATE', 'Missing Update Alert'),
        ('PERFORMANCE', 'Performance Alert'),
    ]
    
    code = models.CharField(max_length=50, unique=True, choices=TYPE_CHOICES)
    name = models.CharField(max_length=200)
    description = models.TextField()
    default_severity = models.CharField(
        max_length=20,
        choices=[
            ('CRITICAL', 'Critical'),
            ('HIGH', 'High'),
            ('MEDIUM', 'Medium'),
            ('LOW', 'Low'),
            ('INFO', 'Info')
        ],
        default='MEDIUM'
    )
    check_frequency = models.IntegerField(
        default=1440,  # минуты (24 часа по умолчанию)
        help_text="Частота проверки в минутах"
    )
    is_active = models.BooleanField(default=True)
    email_template = models.TextField(
        blank=True,
        help_text="Шаблон email уведомления"
    )
    
    # Пороговые значения для автоматических проверок
    threshold_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON конфигурация порогов для данного типа алерта"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Alert Type"
        verbose_name_plural = "Alert Types"
    
    def __str__(self):
        return self.name


class ProjectAlert(models.Model):
    """Алерты для конкретных проектов"""
    
    SEVERITY_CHOICES = [
        ('CRITICAL', 'Critical'),
        ('HIGH', 'High'),
        ('MEDIUM', 'Medium'),
        ('LOW', 'Low'),
        ('INFO', 'Info')
    ]
    
    STATUS_CHOICES = [
        ('NEW', 'New'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
        ('DISMISSED', 'Dismissed'),
        ('ESCALATED', 'Escalated')
    ]
    
    # Связи
    project = models.ForeignKey(
        'investments.Project',
        on_delete=models.CASCADE,
        related_name='alerts'
    )
    alert_type = models.ForeignKey(
        AlertType,
        on_delete=models.CASCADE,
        related_name='project_alerts'
    )
    
    # Основные поля
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='MEDIUM',
        db_index=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='NEW',
        db_index=True
    )
    
    # Детали алерта
    title = models.CharField(max_length=300)
    message = models.TextField()
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Дополнительные данные алерта в JSON"
    )
    
    # Метрики
    metric_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Числовое значение метрики, вызвавшей алерт"
    )
    threshold_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Пороговое значение"
    )
    deviation = models.FloatField(
        null=True,
        blank=True,
        help_text="Отклонение от нормы в %"
    )
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    
    # Пользователи
    created_by = models.CharField(
        max_length=100,
        default='System',
        help_text="Кто или что создало алерт"
    )
    assigned_to = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_alerts'
    )
    resolved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='resolved_alerts'
    )
    
    # Действия
    resolution_notes = models.TextField(
        blank=True,
        help_text="Заметки о решении проблемы"
    )
    actions_taken = models.JSONField(
        default=list,
        blank=True,
        help_text="Список предпринятых действий"
    )
    
    # Уведомления
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    push_sent = models.BooleanField(default=False)
    push_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Повторяемость
    is_recurring = models.BooleanField(
        default=False,
        help_text="Повторяющийся алерт"
    )
    recurrence_count = models.IntegerField(
        default=0,
        help_text="Количество повторений"
    )
    last_occurrence = models.DateTimeField(null=True, blank=True)
    
    # Связь с родительским алертом (для группировки)
    parent_alert = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='child_alerts'
    )
    
    class Meta:
        ordering = ['-created_at', '-severity']
        verbose_name = "Project Alert"
        verbose_name_plural = "Project Alerts"
        indexes = [
            models.Index(fields=['-created_at', 'status']),
            models.Index(fields=['project', '-created_at']),
            models.Index(fields=['severity', 'status']),
        ]
    
    def __str__(self):
        return f"{self.project.name} - {self.title} ({self.get_severity_display()})"
    
    def acknowledge(self, user=None):
        """Подтвердить получение алерта"""
        self.status = 'ACKNOWLEDGED'
        self.acknowledged_at = timezone.now()
        if user:
            self.assigned_to = user
        self.save()
    
    def resolve(self, user=None, notes=""):
        """Отметить алерт как решенный"""
        self.status = 'RESOLVED'
        self.resolved_at = timezone.now()
        if user:
            self.resolved_by = user
        if notes:
            self.resolution_notes = notes
        self.save()
    
    def escalate(self):
        """Эскалировать алерт"""
        self.status = 'ESCALATED'
        self.escalated_at = timezone.now()
        if self.severity == 'LOW':
            self.severity = 'MEDIUM'
        elif self.severity == 'MEDIUM':
            self.severity = 'HIGH'
        elif self.severity == 'HIGH':
            self.severity = 'CRITICAL'
        self.save()
    
    def get_severity_color(self):
        """Получить цвет для отображения severity"""
        colors = {
            'CRITICAL': '#FF0000',
            'HIGH': '#FF9900',
            'MEDIUM': '#FFCC00',
            'LOW': '#0099FF',
            'INFO': '#999999'
        }
        return colors.get(self.severity, '#666666')
    
    def get_severity_icon(self):
        """Получить иконку для severity"""
        icons = {
            'CRITICAL': '🚨',
            'HIGH': '⚠️',
            'MEDIUM': '⚡',
            'LOW': 'ℹ️',
            'INFO': '📊'
        }
        return icons.get(self.severity, '❓')
    
    @property
    def is_open(self):
        """Проверить, открыт ли алерт"""
        return self.status not in ['RESOLVED', 'DISMISSED']
    
    @property
    def age_days(self):
        """Возраст алерта в днях"""
        if self.resolved_at:
            delta = self.resolved_at - self.created_at
        else:
            delta = timezone.now() - self.created_at
        return delta.days
    
    @property
    def response_time_hours(self):
        """Время реакции в часах"""
        if self.acknowledged_at:
            delta = self.acknowledged_at - self.created_at
            return round(delta.total_seconds() / 3600, 1)
        return None
    
    @property
    def resolution_time_hours(self):
        """Время решения в часах"""
        if self.resolved_at:
            delta = self.resolved_at - self.created_at
            return round(delta.total_seconds() / 3600, 1)
        return None


class AlertSettings(models.Model):
    """Настройки алертов для пользователей"""
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='alert_settings'
    )
    
    # Email настройки
    email_enabled = models.BooleanField(default=True)
    email_frequency = models.CharField(
        max_length=20,
        choices=[
            ('IMMEDIATE', 'Immediate'),
            ('HOURLY', 'Hourly'),
            ('DAILY', 'Daily'),
            ('WEEKLY', 'Weekly')
        ],
        default='IMMEDIATE'
    )
    email_digest_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Время отправки дайджеста"
    )
    
    # Push настройки
    push_enabled = models.BooleanField(default=False)
    push_token = models.TextField(
        blank=True,
        help_text="FCM/APNs токен для push уведомлений"
    )
    
    # Подписки на типы алертов
    subscribed_types = models.ManyToManyField(
        AlertType,
        blank=True,
        related_name='subscribers'
    )
    
    # Подписки на проекты
    subscribed_projects = models.ManyToManyField(
        'investments.Project',
        blank=True,
        related_name='alert_subscribers'
    )
    
    # Фильтры по severity
    min_severity = models.CharField(
        max_length=20,
        choices=ProjectAlert.SEVERITY_CHOICES,
        default='LOW',
        help_text="Минимальный уровень важности для уведомлений"
    )
    
    # Quiet hours
    quiet_hours_enabled = models.BooleanField(default=False)
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    # Дополнительные настройки
    weekend_notifications = models.BooleanField(default=False)
    vacation_mode = models.BooleanField(default=False)
    vacation_mode_until = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Alert Settings"
        verbose_name_plural = "Alert Settings"
    
    def __str__(self):
        return f"Alert Settings for {self.user.username}"
    
    def should_send_notification(self, alert):
        """Проверить, нужно ли отправлять уведомление"""
        # Vacation mode
        if self.vacation_mode:
            if self.vacation_mode_until and timezone.now() > self.vacation_mode_until:
                self.vacation_mode = False
                self.save()
            else:
                return False
        
        # Check severity
        severity_levels = ['INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
        alert_level = severity_levels.index(alert.severity)
        min_level = severity_levels.index(self.min_severity)
        if alert_level < min_level:
            return False
        
        # Check quiet hours
        if self.quiet_hours_enabled:
            now = timezone.now().time()
            if self.quiet_hours_start <= now <= self.quiet_hours_end:
                return False
        
        # Check weekend
        if not self.weekend_notifications:
            if timezone.now().weekday() in [5, 6]:  # Saturday, Sunday
                return False
        
        # Check subscriptions
        if self.subscribed_types.exists():
            if alert.alert_type not in self.subscribed_types.all():
                return False
        
        if self.subscribed_projects.exists():
            if alert.project not in self.subscribed_projects.all():
                return False
        
        return True


class AlertLog(models.Model):
    """Лог всех действий с алертами"""
    
    ACTION_CHOICES = [
        ('CREATED', 'Alert Created'),
        ('ACKNOWLEDGED', 'Alert Acknowledged'),
        ('ASSIGNED', 'Alert Assigned'),
        ('ESCALATED', 'Alert Escalated'),
        ('RESOLVED', 'Alert Resolved'),
        ('DISMISSED', 'Alert Dismissed'),
        ('EMAIL_SENT', 'Email Sent'),
        ('PUSH_SENT', 'Push Sent'),
        ('COMMENT_ADDED', 'Comment Added'),
        ('STATUS_CHANGED', 'Status Changed'),
        ('SEVERITY_CHANGED', 'Severity Changed'),
    ]
    
    alert = models.ForeignKey(
        ProjectAlert,
        on_delete=models.CASCADE,
        related_name='logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    user = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    details = models.TextField(blank=True)
    old_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Alert Log"
        verbose_name_plural = "Alert Logs"
    
    def __str__(self):
        return f"{self.alert.title} - {self.get_action_display()} at {self.created_at}"


class AlertRule(models.Model):
    """Правила автоматической генерации алертов"""
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    alert_type = models.ForeignKey(AlertType, on_delete=models.CASCADE)
    
    # Условия правила
    condition_type = models.CharField(
        max_length=50,
        choices=[
            ('THRESHOLD', 'Threshold'),
            ('CHANGE', 'Change'),
            ('TREND', 'Trend'),
            ('COMPARISON', 'Comparison'),
            ('TIME_BASED', 'Time Based'),
            ('CUSTOM', 'Custom')
        ]
    )
    
    # Метрика для проверки
    metric_field = models.CharField(
        max_length=100,
        help_text="Поле модели для проверки (например, 'irr', 'nav')"
    )
    
    # Условия
    operator = models.CharField(
        max_length=20,
        choices=[
            ('GT', 'Greater Than'),
            ('GTE', 'Greater Than or Equal'),
            ('LT', 'Less Than'),
            ('LTE', 'Less Than or Equal'),
            ('EQ', 'Equal'),
            ('NEQ', 'Not Equal'),
            ('CHANGE_GT', 'Change Greater Than'),
            ('CHANGE_LT', 'Change Less Than'),
        ]
    )
    
    threshold_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Пороговое значение для сравнения"
    )
    
    # Дополнительные параметры
    lookback_days = models.IntegerField(
        default=1,
        help_text="Период для анализа изменений (дни)"
    )
    
    min_occurrences = models.IntegerField(
        default=1,
        help_text="Минимальное количество срабатываний для создания алерта"
    )
    
    # Настройки severity
    severity_override = models.CharField(
        max_length=20,
        choices=ProjectAlert.SEVERITY_CHOICES,
        null=True,
        blank=True,
        help_text="Переопределить severity для этого правила"
    )
    
    # Активность
    is_active = models.BooleanField(default=True)
    applies_to_all_projects = models.BooleanField(default=True)
    specific_projects = models.ManyToManyField(
        'investments.Project',
        blank=True,
        related_name='alert_rules'
    )
    
    # Custom Python код для сложных правил
    custom_condition = models.TextField(
        blank=True,
        help_text="Python код для проверки условия (опционально)"
    )
    
    # Расписание проверок
    check_schedule = models.CharField(
        max_length=100,
        default='0 */1 * * *',  # Каждый час
        help_text="Cron expression для расписания проверок"
    )
    
    last_checked = models.DateTimeField(null=True, blank=True)
    last_triggered = models.DateTimeField(null=True, blank=True)
    trigger_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = "Alert Rule"
        verbose_name_plural = "Alert Rules"
    
    def __str__(self):
        return f"{self.name} ({self.alert_type.name})"
    
    def check_condition(self, project, current_value):
        """Проверить условие правила для проекта"""
        if self.condition_type == 'CUSTOM' and self.custom_condition:
            # Выполнить custom код
            try:
                # Безопасное выполнение с ограниченным контекстом
                local_vars = {
                    'project': project,
                    'value': current_value,
                    'threshold': self.threshold_value
                }
                exec(self.custom_condition, {"__builtins__": {}}, local_vars)
                return local_vars.get('result', False)
            except Exception as e:
                print(f"Error in custom condition: {e}")
                return False
        
        # Стандартные проверки
        if self.operator == 'GT':
            return current_value > self.threshold_value
        elif self.operator == 'GTE':
            return current_value >= self.threshold_value
        elif self.operator == 'LT':
            return current_value < self.threshold_value
        elif self.operator == 'LTE':
            return current_value <= self.threshold_value
        elif self.operator == 'EQ':
            return current_value == self.threshold_value
        elif self.operator == 'NEQ':
            return current_value != self.threshold_value
        
        return False


class AlertStatistics(models.Model):
    """Статистика по алертам для дашборда"""
    
    date = models.DateField(unique=True)
    
    # Счетчики по severity
    critical_count = models.IntegerField(default=0)
    high_count = models.IntegerField(default=0)
    medium_count = models.IntegerField(default=0)
    low_count = models.IntegerField(default=0)
    info_count = models.IntegerField(default=0)
    
    # Счетчики по статусу
    new_count = models.IntegerField(default=0)
    acknowledged_count = models.IntegerField(default=0)
    resolved_count = models.IntegerField(default=0)
    dismissed_count = models.IntegerField(default=0)
    
    # Метрики производительности
    avg_response_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Среднее время реакции в часах"
    )
    avg_resolution_time = models.FloatField(
        null=True,
        blank=True,
        help_text="Среднее время решения в часах"
    )
    
    # Top алерты
    top_projects = models.JSONField(
        default=list,
        blank=True,
        help_text="Топ проектов по количеству алертов"
    )
    top_types = models.JSONField(
        default=list,
        blank=True,
        help_text="Топ типов алертов"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Alert Statistics"
        verbose_name_plural = "Alert Statistics"
    
    def __str__(self):
        return f"Alert Statistics for {self.date}"
    
    @classmethod
    def calculate_for_date(cls, date):
        """Рассчитать статистику для указанной даты"""
        from django.db.models import Count, Avg
        
        alerts = ProjectAlert.objects.filter(
            created_at__date=date
        )
        
        stats, created = cls.objects.get_or_create(date=date)
        
        # Подсчет по severity
        severity_counts = alerts.values('severity').annotate(count=Count('id'))
        for item in severity_counts:
            setattr(stats, f"{item['severity'].lower()}_count", item['count'])
        
        # Подсчет по статусу  
        status_counts = alerts.values('status').annotate(count=Count('id'))
        for item in status_counts:
            setattr(stats, f"{item['status'].lower()}_count", item['count'])
        
        # Средние времена
        resolved_alerts = alerts.filter(resolved_at__isnull=False)
        if resolved_alerts.exists():
            times = []
            for alert in resolved_alerts:
                if alert.resolution_time_hours:
                    times.append(alert.resolution_time_hours)
            if times:
                stats.avg_resolution_time = sum(times) / len(times)
        
        # Top проекты
        top_projects = alerts.values('project__name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        stats.top_projects = list(top_projects)
        
        # Top типы
        top_types = alerts.values('alert_type__name').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        stats.top_types = list(top_types)
        
        stats.save()
        return stats