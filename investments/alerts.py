# investments/alerts.py
"""
🚨 HEDGE FUND TRACKER - ALERT SYSTEM CORE
Основная логика системы алертов и мониторинга
"""

from datetime import datetime, timedelta, date
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from typing import Optional, List, Dict, Any
import logging

from .models import Project, Transaction
from .alerts_models import (
    ProjectAlert, AlertType, AlertSettings, 
    AlertLog, AlertRule, AlertStatistics
)

logger = logging.getLogger(__name__)


class AlertManager:
    """Менеджер для управления алертами"""
    
    def __init__(self):
        self.severity_weights = {
            'CRITICAL': 5,
            'HIGH': 4,
            'MEDIUM': 3,
            'LOW': 2,
            'INFO': 1
        }
    
    def create_alert(
        self,
        project: Project,
        alert_type_code: str,
        title: str,
        message: str,
        severity: str = 'MEDIUM',
        metric_value: float = None,
        threshold_value: float = None,
        details: Dict = None,
        auto_notify: bool = True
    ) -> ProjectAlert:
        """Создать новый алерт"""
        
        # Получаем тип алерта
        try:
            alert_type = AlertType.objects.get(code=alert_type_code)
        except AlertType.DoesNotExist:
            # Создаем базовый тип если не существует
            alert_type = AlertType.objects.create(
                code=alert_type_code,
                name=alert_type_code.replace('_', ' ').title(),
                description=f"Auto-created alert type: {alert_type_code}",
                default_severity=severity
            )
        
        # Проверяем на дубликаты (не создаем одинаковые алерты в течение часа)
        recent_duplicate = ProjectAlert.objects.filter(
            project=project,
            alert_type=alert_type,
            title=title,
            status__in=['NEW', 'ACKNOWLEDGED'],
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).first()
        
        if recent_duplicate:
            # Увеличиваем счетчик повторений
            recent_duplicate.recurrence_count += 1
            recent_duplicate.last_occurrence = timezone.now()
            recent_duplicate.save()
            logger.info(f"Alert duplicate found, incrementing recurrence: {title}")
            return recent_duplicate
        
        # Рассчитываем отклонение если есть метрика и порог
        deviation = None
        if metric_value is not None and threshold_value is not None and threshold_value != 0:
            deviation = ((metric_value - threshold_value) / abs(threshold_value)) * 100
        
        # Создаем алерт
        alert = ProjectAlert.objects.create(
            project=project,
            alert_type=alert_type,
            severity=severity or alert_type.default_severity,
            title=title,
            message=message,
            metric_value=metric_value,
            threshold_value=threshold_value,
            deviation=deviation,
            details=details or {},
            created_by='System'
        )
        
        # Логируем создание
        AlertLog.objects.create(
            alert=alert,
            action='CREATED',
            details=f"Alert created: {title}"
        )
        
        # Отправляем уведомления если нужно
        if auto_notify:
            self.send_notifications(alert)
        
        logger.info(f"Alert created: {title} for project {project.name}")
        return alert
    
    def check_irr_gap(self, project: Project) -> Optional[ProjectAlert]:
        """Проверка отклонения IRR от целевого"""
        if not project.target_irr:
            return None
        
        current_irr = project.get_xirr()
        if current_irr is None:
            return None
        
        gap = current_irr - project.target_irr
        gap_percent = gap * 100
        
        # Определяем severity на основе размера отклонения
        if gap_percent < -10:
            severity = 'CRITICAL'
        elif gap_percent < -5:
            severity = 'HIGH'
        elif gap_percent < -2:
            severity = 'MEDIUM'
        else:
            return None  # Не создаем алерт для малых отклонений
        
        return self.create_alert(
            project=project,
            alert_type_code='IRR_GAP',
            title=f"IRR значительно ниже целевого",
            message=f"Текущий IRR {current_irr*100:.2f}% отстает от целевого {project.target_irr*100:.2f}% на {abs(gap_percent):.2f}%",
            severity=severity,
            metric_value=current_irr,
            threshold_value=project.target_irr,
            details={
                'current_irr': current_irr,
                'target_irr': project.target_irr,
                'gap': gap,
                'gap_percent': gap_percent
            }
        )
    
    def check_nav_drop(self, project: Project, lookback_days: int = 7) -> Optional[ProjectAlert]:
        """Проверка резкого падения NAV"""
        if project.status != 'active':
            return None
        
        current_nav = project.get_nav()
        if not current_nav:
            return None
        
        # Получаем историческое значение NAV
        past_date = date.today() - timedelta(days=lookback_days)
        past_transaction = project.transactions.filter(
            date__lte=past_date,
            nav__isnull=False
        ).order_by('-date').first()
        
        if not past_transaction or not past_transaction.nav_usd:
            return None
        
        past_nav = past_transaction.nav_usd
        change_percent = ((current_nav - past_nav) / past_nav) * 100
        
        # Проверяем на значительное падение
        if change_percent < -10:
            severity = 'CRITICAL'
        elif change_percent < -5:
            severity = 'HIGH'
        elif change_percent < -3:
            severity = 'MEDIUM'
        else:
            return None
        
        return self.create_alert(
            project=project,
            alert_type_code='NAV_DROP',
            title=f"NAV упал на {abs(change_percent):.1f}% за {lookback_days} дней",
            message=f"NAV снизился с ${past_nav:,.2f} до ${current_nav:,.2f}",
            severity=severity,
            metric_value=current_nav,
            threshold_value=past_nav,
            details={
                'current_nav': current_nav,
                'past_nav': past_nav,
                'change_percent': change_percent,
                'period_days': lookback_days
            }
        )
    
    def check_npv_negative(self, project: Project) -> Optional[ProjectAlert]:
        """Проверка отрицательного NPV"""
        npv = project.get_xnpv()
        if npv is None or npv >= 0:
            return None
        
        invested = project.get_total_invested()
        npv_percent = (abs(npv) / invested * 100) if invested else 0
        
        # Определяем severity
        if npv_percent > 20:
            severity = 'CRITICAL'
        elif npv_percent > 10:
            severity = 'HIGH'
        else:
            severity = 'MEDIUM'
        
        return self.create_alert(
            project=project,
            alert_type_code='NPV_NEGATIVE',
            title="Отрицательный NPV проекта",
            message=f"NPV составляет ${npv:,.2f} ({npv_percent:.1f}% от инвестиций)",
            severity=severity,
            metric_value=npv,
            threshold_value=0,
            details={
                'npv': npv,
                'invested': invested,
                'npv_percent': npv_percent,
                'target_irr': project.target_irr
            }
        )
    
    def check_data_quality(self, project: Project) -> List[ProjectAlert]:
        """Проверка качества данных"""
        alerts = []
        
        # Проверка 1: DPI > TVPI (невозможная ситуация)
        dpi = project.get_dpi()
        tvpi = project.get_tvpi()
        
        if dpi and tvpi and dpi > tvpi:
            alert = self.create_alert(
                project=project,
                alert_type_code='DATA_QUALITY',
                title="Ошибка данных: DPI > TVPI",
                message=f"DPI ({dpi:.2f}) больше TVPI ({tvpi:.2f}), что невозможно",
                severity='HIGH',
                details={'dpi': dpi, 'tvpi': tvpi}
            )
            alerts.append(alert)
        
        # Проверка 2: Нет обновлений NAV для активного проекта
        if project.status == 'active':
            last_nav_update = project.transactions.filter(
                nav__isnull=False
            ).order_by('-date').first()
            
            if last_nav_update:
                days_since_update = (date.today() - last_nav_update.date).days
                if days_since_update > 30:
                    alert = self.create_alert(
                        project=project,
                        alert_type_code='DATA_QUALITY',
                        title=f"NAV не обновлялся {days_since_update} дней",
                        message="Требуется обновление текущей стоимости активов",
                        severity='MEDIUM' if days_since_update < 60 else 'HIGH',
                        details={'days_since_update': days_since_update}
                    )
                    alerts.append(alert)
            else:
                # Нет NAV вообще для активного проекта
                alert = self.create_alert(
                    project=project,
                    alert_type_code='DATA_QUALITY',
                    title="Отсутствует NAV для активного проекта",
                    message="Необходимо добавить текущую оценку стоимости",
                    severity='HIGH'
                )
                alerts.append(alert)
        
        # Проверка 3: Аномальные значения IRR
        irr = project.get_xirr()
        if irr is not None:
            if irr > 1:  # IRR > 100%
                alert = self.create_alert(
                    project=project,
                    alert_type_code='DATA_QUALITY',
                    title=f"Подозрительно высокий IRR: {irr*100:.1f}%",
                    message="Проверьте корректность данных о транзакциях",
                    severity='MEDIUM',
                    metric_value=irr
                )
                alerts.append(alert)
            elif irr < -0.5:  # IRR < -50%
                alert = self.create_alert(
                    project=project,
                    alert_type_code='DATA_QUALITY',
                    title=f"Критически низкий IRR: {irr*100:.1f}%",
                    message="Возможна ошибка в данных или критическая потеря",
                    severity='HIGH',
                    metric_value=irr
                )
                alerts.append(alert)
        
        return alerts
# ПРОДОЛЖЕНИЕ ФАЙЛА alerts.py - добавьте после check_data_quality
    
    def check_drawdown(self, project: Project) -> Optional[ProjectAlert]:
        """Проверка просадки от пика"""
        if project.status != 'active':
            return None
        
        # Получаем все значения equity/NAV
        transactions = project.transactions.order_by('date')
        values = []
        
        for tx in transactions:
            if tx.nav_usd:
                values.append((tx.date, tx.nav_usd))
            elif tx.equity_usd:
                values.append((tx.date, tx.equity_usd))
        
        if len(values) < 2:
            return None
        
        # Находим максимум и текущее значение
        max_value = max(v[1] for v in values)
        current_value = values[-1][1]
        
        if max_value == 0:
            return None
        
        drawdown_percent = ((max_value - current_value) / max_value) * 100
        
        # Определяем severity
        if drawdown_percent > 20:
            severity = 'CRITICAL'
        elif drawdown_percent > 15:
            severity = 'HIGH'
        elif drawdown_percent > 10:
            severity = 'MEDIUM'
        else:
            return None
        
        return self.create_alert(
            project=project,
            alert_type_code='DRAWDOWN',
            title=f"Просадка {drawdown_percent:.1f}% от максимума",
            message=f"Стоимость упала с ${max_value:,.2f} до ${current_value:,.2f}",
            severity=severity,
            metric_value=current_value,
            threshold_value=max_value,
            details={
                'max_value': max_value,
                'current_value': current_value,
                'drawdown_percent': drawdown_percent
            }
        )
    
    def check_distribution_received(self, project: Project) -> Optional[ProjectAlert]:
        """Проверка новых распределений"""
        # Проверяем последние транзакции возврата
        recent_return = project.transactions.filter(
            transaction_type='Return',
            date__gte=date.today() - timedelta(days=7)
        ).order_by('-date').first()
        
        if not recent_return:
            return None
        
        # Проверяем, не создавали ли мы уже алерт для этой транзакции
        existing_alert = ProjectAlert.objects.filter(
            project=project,
            alert_type__code='DISTRIBUTION',
            created_at__date=recent_return.date
        ).exists()
        
        if existing_alert:
            return None
        
        return self.create_alert(
            project=project,
            alert_type_code='DISTRIBUTION',
            title=f"Получено распределение ${recent_return.return_usd:,.2f}",
            message=f"Новое распределение от {recent_return.date}",
            severity='INFO',
            metric_value=recent_return.return_usd,
            details={
                'amount': recent_return.return_usd,
                'date': str(recent_return.date),
                'transaction_id': recent_return.id
            }
        )
    
    def check_performance_milestone(self, project: Project) -> Optional[ProjectAlert]:
        """Проверка достижения важных метрик"""
        alerts = []
        
        # Проверка достижения целевого IRR
        if project.target_irr:
            current_irr = project.get_xirr()
            if current_irr and current_irr >= project.target_irr:
                # Проверяем, не создавали ли уже такой алерт недавно
                recent_alert = ProjectAlert.objects.filter(
                    project=project,
                    alert_type__code='PERFORMANCE',
                    title__contains="достиг целевого IRR",
                    created_at__gte=timezone.now() - timedelta(days=30)
                ).exists()
                
                if not recent_alert:
                    alert = self.create_alert(
                        project=project,
                        alert_type_code='PERFORMANCE',
                        title=f"Проект достиг целевого IRR!",
                        message=f"IRR {current_irr*100:.2f}% превысил целевой {project.target_irr*100:.2f}%",
                        severity='INFO',
                        metric_value=current_irr,
                        threshold_value=project.target_irr,
                        details={
                            'current_irr': current_irr,
                            'target_irr': project.target_irr,
                            'achievement': 'target_reached'
                        }
                    )
                    alerts.append(alert)
        
        # Проверка MOIC > 2x
        moic = project.get_moic()
        if moic and moic >= 2.0:
            recent_alert = ProjectAlert.objects.filter(
                project=project,
                alert_type__code='PERFORMANCE',
                title__contains="MOIC превысил 2x",
                created_at__gte=timezone.now() - timedelta(days=30)
            ).exists()
            
            if not recent_alert:
                alert = self.create_alert(
                    project=project,
                    alert_type_code='PERFORMANCE',
                    title=f"MOIC превысил 2x!",
                    message=f"Множитель на инвестированный капитал достиг {moic:.2f}x",
                    severity='INFO',
                    metric_value=moic,
                    threshold_value=2.0,
                    details={'moic': moic, 'achievement': 'moic_2x'}
                )
                alerts.append(alert)
        
        return alerts[0] if alerts else None
    
    def check_all_projects(self) -> List[ProjectAlert]:
        """Проверить все проекты и создать алерты"""
        alerts = []
        projects = Project.objects.filter(status='active')
        
        for project in projects:
            # IRR Gap проверка
            alert = self.check_irr_gap(project)
            if alert:
                alerts.append(alert)
            
            # NAV Drop проверка
            alert = self.check_nav_drop(project)
            if alert:
                alerts.append(alert)
            
            # NPV проверка
            alert = self.check_npv_negative(project)
            if alert:
                alerts.append(alert)
            
            # Data Quality проверки
            quality_alerts = self.check_data_quality(project)
            alerts.extend(quality_alerts)
            
            # Drawdown проверка
            alert = self.check_drawdown(project)
            if alert:
                alerts.append(alert)
            
            # Distribution проверка
            alert = self.check_distribution_received(project)
            if alert:
                alerts.append(alert)
            
            # Performance milestones
            alert = self.check_performance_milestone(project)
            if alert:
                alerts.append(alert)
        
        logger.info(f"Alert check completed: {len(alerts)} new alerts created")
        return alerts
    
    def send_notifications(self, alert: ProjectAlert):
        """Отправить уведомления об алерте"""
        # Получаем пользователей для уведомления
        from django.contrib.auth.models import User
        
        # Администраторы всегда получают критические алерты
        if alert.severity == 'CRITICAL':
            admins = User.objects.filter(is_staff=True, is_active=True)
            for admin in admins:
                self.send_email_notification(admin, alert)
        
        # Проверяем настройки пользователей
        for settings in AlertSettings.objects.filter(email_enabled=True):
            if settings.should_send_notification(alert):
                self.send_email_notification(settings.user, alert)
    
    def send_email_notification(self, user, alert: ProjectAlert):
        """Отправить email уведомление"""
        try:
            subject = f"[{alert.get_severity_display()}] {alert.title}"
            
            message = f"""
            {alert.get_severity_icon()} HEDGE FUND TRACKER ALERT
            
            Project: {alert.project.name}
            Type: {alert.alert_type.name}
            Severity: {alert.get_severity_display()}
            
            {alert.message}
            
            {f"Metric Value: {alert.metric_value}" if alert.metric_value else ""}
            {f"Threshold: {alert.threshold_value}" if alert.threshold_value else ""}
            {f"Deviation: {alert.deviation:.1f}%" if alert.deviation else ""}
            
            View details: {settings.SITE_URL}/admin/investments/projectalert/{alert.id}/
            
            ---
            This is an automated message from Hedge Fund Tracker
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            # Обновляем статус отправки
            alert.email_sent = True
            alert.email_sent_at = timezone.now()
            alert.save()
            
            # Логируем
            AlertLog.objects.create(
                alert=alert,
                action='EMAIL_SENT',
                user=user,
                details=f"Email sent to {user.email}"
            )
            
        except Exception as e:
            logger.error(f"Failed to send email for alert {alert.id}: {str(e)}")
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Получить статистику для дашборда"""
        now = timezone.now()
        today = now.date()
        week_ago = today - timedelta(days=7)
        
        # Общая статистика
        total_open = ProjectAlert.objects.filter(
            status__in=['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS']
        ).count()
        
        # По severity
        severity_stats = {}
        for severity, _ in ProjectAlert.SEVERITY_CHOICES:
            count = ProjectAlert.objects.filter(
                status__in=['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS'],
                severity=severity
            ).count()
            severity_stats[severity.lower()] = count
        
        # Недавние алерты
        recent_alerts = ProjectAlert.objects.filter(
            created_at__gte=now - timedelta(hours=24)
        ).select_related('project', 'alert_type')
        
        # Тренды
        week_alerts = ProjectAlert.objects.filter(
            created_at__date__gte=week_ago
        )
        
        resolved_week = week_alerts.filter(status='RESOLVED')
        
        # Среднее время решения
        avg_resolution = None
        if resolved_week.exists():
            times = [a.resolution_time_hours for a in resolved_week if a.resolution_time_hours]
            if times:
                avg_resolution = sum(times) / len(times)
        
        # Топ проекты по алертам
        from django.db.models import Count
        top_projects = ProjectAlert.objects.filter(
            status__in=['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS']
        ).values('project__name').annotate(
            alert_count=Count('id')
        ).order_by('-alert_count')[:5]
        
        # Распределение по типам
        type_distribution = ProjectAlert.objects.filter(
            created_at__date=today
        ).values('alert_type__name').annotate(
            count=Count('id')
        ).order_by('-count')
        
        return {
            'total_open': total_open,
            'severity_stats': severity_stats,
            'recent_alerts': recent_alerts[:10],
            'alerts_today': ProjectAlert.objects.filter(created_at__date=today).count(),
            'alerts_week': week_alerts.count(),
            'resolved_week': resolved_week.count(),
            'avg_resolution_hours': avg_resolution,
            'top_projects': list(top_projects),
            'type_distribution': list(type_distribution),
            'critical_open': severity_stats.get('critical', 0),
            'high_open': severity_stats.get('high', 0),
        }


class AlertAnalyzer:
    """Анализатор для выявления паттернов и трендов в алертах"""
    
    def analyze_project_health(self, project: Project) -> Dict[str, Any]:
        """Анализ здоровья проекта на основе алертов"""
        
        # Получаем алерты за последние 30 дней
        cutoff_date = timezone.now() - timedelta(days=30)
        recent_alerts = ProjectAlert.objects.filter(
            project=project,
            created_at__gte=cutoff_date
        )
        
        # Подсчет по severity
        severity_counts = {}
        for severity, _ in ProjectAlert.SEVERITY_CHOICES:
            severity_counts[severity] = recent_alerts.filter(severity=severity).count()
        
        # Расчет health score (0-100)
        health_score = 100
        health_score -= severity_counts.get('CRITICAL', 0) * 20
        health_score -= severity_counts.get('HIGH', 0) * 10
        health_score -= severity_counts.get('MEDIUM', 0) * 5
        health_score -= severity_counts.get('LOW', 0) * 2
        health_score = max(0, min(100, health_score))
        
        # Определение статуса
        if health_score >= 80:
            health_status = 'GOOD'
        elif health_score >= 60:
            health_status = 'FAIR'
        elif health_score >= 40:
            health_status = 'POOR'
        else:
            health_status = 'CRITICAL'
        
        # Тренды
        week_ago = timezone.now() - timedelta(days=7)
        alerts_this_week = recent_alerts.filter(created_at__gte=week_ago).count()
        alerts_last_week = recent_alerts.filter(
            created_at__lt=week_ago,
            created_at__gte=week_ago - timedelta(days=7)
        ).count()
        
        if alerts_last_week > 0:
            trend = ((alerts_this_week - alerts_last_week) / alerts_last_week) * 100
        else:
            trend = 0 if alerts_this_week == 0 else 100
        
        return {
            'health_score': health_score,
            'health_status': health_status,
            'total_alerts_30d': recent_alerts.count(),
            'severity_breakdown': severity_counts,
            'trend_percent': trend,
            'alerts_this_week': alerts_this_week,
            'alerts_last_week': alerts_last_week,
            'unresolved_critical': recent_alerts.filter(
                severity='CRITICAL',
                status__in=['NEW', 'ACKNOWLEDGED']
            ).count(),
            'avg_resolution_time': self._calculate_avg_resolution_time(recent_alerts),
            'most_common_type': self._get_most_common_alert_type(recent_alerts),
        }
    
    def _calculate_avg_resolution_time(self, alerts):
        """Рассчитать среднее время решения"""
        resolved = alerts.filter(resolved_at__isnull=False)
        if not resolved.exists():
            return None
        
        times = [a.resolution_time_hours for a in resolved if a.resolution_time_hours]
        return sum(times) / len(times) if times else None
    
    def _get_most_common_alert_type(self, alerts):
        """Найти самый частый тип алерта"""
        from django.db.models import Count
        
        top_type = alerts.values('alert_type__name').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        return top_type['alert_type__name'] if top_type else None
    
    def generate_portfolio_report(self) -> Dict[str, Any]:
        """Генерация отчета по всему портфолио"""
        projects = Project.objects.filter(status='active')
        
        portfolio_health = []
        total_score = 0
        
        for project in projects:
            health = self.analyze_project_health(project)
            portfolio_health.append({
                'project': project.name,
                'health_score': health['health_score'],
                'health_status': health['health_status'],
                'critical_alerts': health['unresolved_critical']
            })
            total_score += health['health_score']
        
        avg_health = total_score / len(portfolio_health) if portfolio_health else 0
        
        # Общая статистика
        manager = AlertManager()
        stats = manager.get_dashboard_stats()
        
        return {
            'portfolio_health_score': avg_health,
            'projects_at_risk': [p for p in portfolio_health if p['health_score'] < 60],
            'total_critical_alerts': stats['critical_open'],
            'total_high_alerts': stats['high_open'],
            'projects_health': portfolio_health,
            'dashboard_stats': stats,
            'generated_at': timezone.now()
        }
