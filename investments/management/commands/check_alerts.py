# investments/management/commands/check_alerts.py
"""
Management команда для автоматической проверки и генерации алертов
Запускается через cron для регулярного мониторинга

Использование:
    python manage.py check_alerts
    python manage.py check_alerts --dry-run
    python manage.py check_alerts --project="Project Name"
    python manage.py check_alerts --email-summary
"""

from django.core.management.base import BaseCommand, CommandError
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from datetime import datetime, timedelta
import logging

from investments.models import Project
from investments.alerts import AlertManager, AlertAnalyzer
from investments.alerts_models import (
    ProjectAlert, AlertType, AlertSettings, 
    AlertStatistics, AlertRule
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check all projects and generate alerts based on defined rules'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run checks without creating alerts (preview mode)',
        )
        
        parser.add_argument(
            '--project',
            type=str,
            help='Check specific project by name',
        )
        
        parser.add_argument(
            '--email-summary',
            action='store_true',
            help='Send email summary to administrators',
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force check even if recently checked',
        )
        
        parser.add_argument(
            '--type',
            type=str,
            help='Check only specific alert type (IRR_GAP, NAV_DROP, etc)',
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output',
        )
    
    def handle(self, *args, **options):
        self.dry_run = options.get('dry_run', False)
        self.verbose = options.get('verbose', False)
        self.email_summary = options.get('email_summary', False)
        self.force = options.get('force', False)
        self.specific_project = options.get('project')
        self.specific_type = options.get('type')
        
        start_time = timezone.now()
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No alerts will be created'))
        
        self.stdout.write(self.style.SUCCESS(f'🚀 Starting alert check at {start_time}'))
        
        try:
            # Проверяем, не запускали ли недавно
            if not self.force and not self.dry_run:
                last_check = self._get_last_check_time()
                if last_check and (timezone.now() - last_check).total_seconds() < 300:  # 5 минут
                    self.stdout.write(self.style.WARNING('⏳ Skipping - checked less than 5 minutes ago'))
                    return
            
            # Инициализируем менеджеры
            alert_manager = AlertManager()
            analyzer = AlertAnalyzer()
            
            # Получаем проекты для проверки
            projects = self._get_projects_to_check()
            
            if not projects:
                self.stdout.write(self.style.WARNING('No projects to check'))
                return
            
            self.stdout.write(f'📊 Checking {len(projects)} projects...')
            
            # Статистика
            stats = {
                'projects_checked': 0,
                'alerts_created': 0,
                'critical_alerts': 0,
                'high_alerts': 0,
                'medium_alerts': 0,
                'low_alerts': 0,
                'info_alerts': 0,
                'errors': 0,
                'alerts_by_type': {},
                'alerts_by_project': {}
            }
            
            # Проверяем каждый проект
            for project in projects:
                if self.verbose:
                    self.stdout.write(f'  Checking {project.name}...')
                
                try:
                    alerts = self._check_project(project, alert_manager)
                    stats['projects_checked'] += 1
                    
                    for alert in alerts:
                        if not self.dry_run:
                            # Алерт уже создан в alert_manager
                            pass
                        else:
                            # В dry-run режиме просто выводим информацию
                            self._print_alert_preview(alert)
                        
                        # Обновляем статистику
                        stats['alerts_created'] += 1
                        severity_key = f"{alert.severity.lower()}_alerts"
                        if severity_key in stats:
                            stats[severity_key] += 1
                        
                        # По типам
                        alert_type = getattr(alert, 'alert_type_code', 'UNKNOWN')
                        stats['alerts_by_type'][alert_type] = stats['alerts_by_type'].get(alert_type, 0) + 1
                        
                        # По проектам
                        stats['alerts_by_project'][project.name] = stats['alerts_by_project'].get(project.name, 0) + 1
                
                except Exception as e:
                    stats['errors'] += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ Error checking {project.name}: {str(e)}')
                    )
                    logger.error(f'Error checking project {project.name}: {str(e)}', exc_info=True)
            
            # Проверяем правила если не dry-run
            if not self.dry_run:
                self._check_alert_rules(alert_manager, stats)
            
            # Обновляем статистику дня
            if not self.dry_run:
                self._update_daily_statistics()
            
            # Выводим результаты
            self._print_summary(stats)
            
            # Отправляем email сводку если нужно
            if self.email_summary and not self.dry_run:
                self._send_email_summary(stats, analyzer)
            
            # Записываем время последней проверки
            if not self.dry_run:
                self._save_last_check_time()
            
            end_time = timezone.now()
            duration = (end_time - start_time).total_seconds()
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Alert check completed in {duration:.1f} seconds')
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Fatal error: {str(e)}'))
            logger.error(f'Fatal error in check_alerts: {str(e)}', exc_info=True)
            raise CommandError(f'Alert check failed: {str(e)}')
    
    def _get_projects_to_check(self):
        """Получить список проектов для проверки"""
        if self.specific_project:
            try:
                return [Project.objects.get(name=self.specific_project)]
            except Project.DoesNotExist:
                raise CommandError(f'Project "{self.specific_project}" not found')
        else:
            # Проверяем только активные проекты
            return Project.objects.filter(status='active')
    
    def _check_project(self, project, alert_manager):
        """Проверить один проект"""
        alerts = []
        
        # Определяем какие проверки выполнять
        checks_to_run = []
        
        if self.specific_type:
            checks_to_run = [self.specific_type]
        else:
            checks_to_run = [
                'IRR_GAP',
                'NAV_DROP',
                'NPV_NEGATIVE',
                'DATA_QUALITY',
                'DRAWDOWN',
                'DISTRIBUTION',
                'PERFORMANCE'
            ]
        
        # Выполняем проверки
        for check_type in checks_to_run:
            try:
                if check_type == 'IRR_GAP':
                    alert = alert_manager.check_irr_gap(project)
                    if alert:
                        alert.alert_type_code = 'IRR_GAP'
                        alerts.append(alert)
                
                elif check_type == 'NAV_DROP':
                    alert = alert_manager.check_nav_drop(project)
                    if alert:
                        alert.alert_type_code = 'NAV_DROP'
                        alerts.append(alert)
                
                elif check_type == 'NPV_NEGATIVE':
                    alert = alert_manager.check_npv_negative(project)
                    if alert:
                        alert.alert_type_code = 'NPV_NEGATIVE'
                        alerts.append(alert)
                
                elif check_type == 'DATA_QUALITY':
                    quality_alerts = alert_manager.check_data_quality(project)
                    for alert in quality_alerts:
                        alert.alert_type_code = 'DATA_QUALITY'
                        alerts.append(alert)
                
                elif check_type == 'DRAWDOWN':
                    alert = alert_manager.check_drawdown(project)
                    if alert:
                        alert.alert_type_code = 'DRAWDOWN'
                        alerts.append(alert)
                
                elif check_type == 'DISTRIBUTION':
                    alert = alert_manager.check_distribution_received(project)
                    if alert:
                        alert.alert_type_code = 'DISTRIBUTION'
                        alerts.append(alert)
                
                elif check_type == 'PERFORMANCE':
                    alert = alert_manager.check_performance_milestone(project)
                    if alert:
                        alert.alert_type_code = 'PERFORMANCE'
                        alerts.append(alert)
                
            except Exception as e:
                if self.verbose:
                    self.stdout.write(
                        self.style.WARNING(f'    Warning in {check_type}: {str(e)}')
                    )
                logger.warning(f'Error in {check_type} check for {project.name}: {str(e)}')
        
        return alerts
# ПРОДОЛЖЕНИЕ check_alerts.py - добавьте после _check_project
    
    def _check_alert_rules(self, alert_manager, stats):
        """Проверить кастомные правила алертов"""
        rules = AlertRule.objects.filter(is_active=True)
        
        for rule in rules:
            try:
                # Проверяем расписание
                if not self._should_check_rule(rule):
                    continue
                
                # Получаем проекты для правила
                if rule.applies_to_all_projects:
                    projects = Project.objects.filter(status='active')
                else:
                    projects = rule.specific_projects.filter(status='active')
                
                for project in projects:
                    # Получаем значение метрики
                    try:
                        current_value = getattr(project, rule.metric_field, None)
                        if callable(current_value):
                            current_value = current_value()
                    except:
                        continue
                    
                    if current_value is None:
                        continue
                    
                    # Проверяем условие
                    if rule.check_condition(project, current_value):
                        # Создаем алерт
                        severity = rule.severity_override or rule.alert_type.default_severity
                        
                        alert = alert_manager.create_alert(
                            project=project,
                            alert_type_code=rule.alert_type.code,
                            title=f"{rule.name} triggered",
                            message=f"{rule.metric_field} = {current_value} (rule: {rule.operator} {rule.threshold_value})",
                            severity=severity,
                            metric_value=current_value,
                            threshold_value=rule.threshold_value,
                            details={'rule_id': rule.id, 'rule_name': rule.name}
                        )
                        
                        if alert:
                            stats['alerts_created'] += 1
                            # Обновляем счетчики правила
                            rule.last_triggered = timezone.now()
                            rule.trigger_count += 1
                            rule.save()
                
                # Обновляем время последней проверки
                rule.last_checked = timezone.now()
                rule.save()
                
            except Exception as e:
                logger.error(f'Error checking rule {rule.name}: {str(e)}')
    
    def _should_check_rule(self, rule):
        """Проверить, нужно ли запускать правило"""
        # Здесь можно добавить проверку cron расписания
        # Пока просто проверяем, что правило не проверялось последний час
        if rule.last_checked:
            hours_since_check = (timezone.now() - rule.last_checked).total_seconds() / 3600
            if hours_since_check < 1:
                return False
        return True
    
    def _print_alert_preview(self, alert):
        """Вывести превью алерта в dry-run режиме"""
        icon = '🚨' if alert.severity == 'CRITICAL' else '⚠️' if alert.severity == 'HIGH' else 'ℹ️'
        
        self.stdout.write(
            f"    {icon} [{alert.severity}] {alert.title}"
        )
        if self.verbose:
            self.stdout.write(f"       {alert.message}")
            if alert.metric_value is not None:
                self.stdout.write(f"       Metric: {alert.metric_value}")
    
    def _print_summary(self, stats):
        """Вывести сводку результатов"""
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('📊 SUMMARY'))
        self.stdout.write('='*50)
        
        self.stdout.write(f"Projects checked: {stats['projects_checked']}")
        self.stdout.write(f"Alerts created: {stats['alerts_created']}")
        
        if stats['alerts_created'] > 0:
            self.stdout.write('\nBy Severity:')
            if stats['critical_alerts'] > 0:
                self.stdout.write(self.style.ERROR(f"  🚨 Critical: {stats['critical_alerts']}"))
            if stats['high_alerts'] > 0:
                self.stdout.write(self.style.WARNING(f"  ⚠️  High: {stats['high_alerts']}"))
            if stats['medium_alerts'] > 0:
                self.stdout.write(f"  ⚡ Medium: {stats['medium_alerts']}")
            if stats['low_alerts'] > 0:
                self.stdout.write(f"  ℹ️  Low: {stats['low_alerts']}")
            if stats['info_alerts'] > 0:
                self.stdout.write(f"  📊 Info: {stats['info_alerts']}")
            
            if stats['alerts_by_type']:
                self.stdout.write('\nBy Type:')
                for alert_type, count in sorted(stats['alerts_by_type'].items(), key=lambda x: x[1], reverse=True):
                    self.stdout.write(f"  {alert_type}: {count}")
            
            if stats['alerts_by_project'] and len(stats['alerts_by_project']) <= 10:
                self.stdout.write('\nBy Project:')
                for project, count in sorted(stats['alerts_by_project'].items(), key=lambda x: x[1], reverse=True):
                    self.stdout.write(f"  {project}: {count}")
        
        if stats['errors'] > 0:
            self.stdout.write(self.style.ERROR(f"\n❌ Errors: {stats['errors']}"))
        
        self.stdout.write('='*50)
    
    def _send_email_summary(self, stats, analyzer):
        """Отправить email сводку администраторам"""
        try:
            # Получаем администраторов
            admins = User.objects.filter(is_staff=True, is_active=True, email__isnull=False)
            
            if not admins.exists():
                return
            
            # Генерируем отчет
            portfolio_report = analyzer.generate_portfolio_report()
            
            # Подготавливаем контекст
            context = {
                'stats': stats,
                'report': portfolio_report,
                'timestamp': timezone.now(),
                'critical_alerts': ProjectAlert.objects.filter(
                    severity='CRITICAL',
                    status__in=['NEW', 'ACKNOWLEDGED']
                ),
                'high_alerts': ProjectAlert.objects.filter(
                    severity='HIGH',
                    status__in=['NEW', 'ACKNOWLEDGED']
                )[:5],
            }
            
            # Генерируем HTML
            try:
                html_content = render_to_string('alerts/email_summary.html', context)
            except:
                # Если шаблон не найден, используем простой текст
                html_content = None
            
            # Текстовая версия
            text_content = f"""
HEDGE FUND TRACKER - Alert Summary
{'='*50}

Check completed at: {timezone.now()}

Projects checked: {stats['projects_checked']}
Alerts created: {stats['alerts_created']}

Critical alerts: {stats['critical_alerts']}
High alerts: {stats['high_alerts']}
Medium alerts: {stats['medium_alerts']}

Portfolio Health Score: {portfolio_report['portfolio_health_score']:.1f}/100

Projects at Risk: {len(portfolio_report['projects_at_risk'])}

{'='*50}
View full dashboard: {getattr(settings, 'SITE_URL', 'http://localhost:8000')}/admin/
            """
            
            # Отправляем каждому администратору
            for admin in admins:
                send_mail(
                    subject=f"[HFT] Alert Summary - {stats['alerts_created']} new alerts",
                    message=text_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin.email],
                    html_message=html_content,
                    fail_silently=True
                )
            
            self.stdout.write(
                self.style.SUCCESS(f"📧 Email summary sent to {admins.count()} administrators")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Failed to send email summary: {str(e)}")
            )
            logger.error(f"Failed to send email summary: {str(e)}", exc_info=True)
    
    def _update_daily_statistics(self):
        """Обновить статистику дня"""
        try:
            today = timezone.now().date()
            AlertStatistics.calculate_for_date(today)
        except Exception as e:
            logger.error(f"Failed to update daily statistics: {str(e)}")
    
    def _get_last_check_time(self):
        """Получить время последней проверки"""
        try:
            from django.core.cache import cache
            return cache.get('alerts_last_check_time')
        except:
            return None
    
    def _save_last_check_time(self):
        """Сохранить время последней проверки"""
        try:
            from django.core.cache import cache
            cache.set('alerts_last_check_time', timezone.now(), 3600)  # На час
        except:
            pass
