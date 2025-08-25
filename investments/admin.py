import datetime
import os
import zipfile

from django.contrib import admin, messages
from django import forms
from django.db import models
from django.shortcuts import render, redirect
from django.urls import path, reverse

from .models import Project, Transaction
from . import utils
from investments.management.commands.export_transactions import Command as ExportCommand
from django.template.response import TemplateResponse
from django.shortcuts import render
from django.utils.timezone import now
from django.utils.html import format_html
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .models import Project, Transaction, Portfolio
from django.core.exceptions import ValidationError

# ЗАМЕНИТЬ ВЕСЬ класс PercentageField в admin.py:

class PercentageField(forms.FloatField):
    """
    Кастомное поле для процентов: простое и надежное решение
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', forms.NumberInput(attrs={
            'style': 'width: 120px;', 
            'step': '0.01',
            'placeholder': 'Введите проценты (напр. 15.5 для 15.5%)'
        }))
        kwargs.setdefault('help_text', 'Введите значение в процентах (например, 15.5 для 15.5%)')
        super().__init__(*args, **kwargs)
    
    def prepare_value(self, value):
        """
        Конвертирует значение из БД (0.15) для отображения в форме (15.00)
        """
        if value is None:
            return value
        try:
            # 0.15 → 15.00
            return f"{float(value) * 100:.2f}"
        except (ValueError, TypeError):
            return value
    
    def clean(self, value):
        """
        🔧 ИСПРАВЛЕНИЕ: Используем clean() вместо to_python()
        clean() вызывается только при обработке данных от пользователя
        """
        if value in self.empty_values:
            return None
        
        try:
            # Конвертируем проценты в десятичное: 15.5 → 0.155
            percentage_value = float(value)
            return percentage_value / 100
        except (ValueError, TypeError):
            raise ValidationError('Введите корректное числовое значение для процентов')

class TransactionInlineForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = (
            "project", "date", "transaction_type",
            "investment", "return_amount", "nav", "x_rate"
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        float_fields = ["investment", "return_amount", "nav", "x_rate"]
        for field_name in float_fields:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.NumberInput(attrs={'style': 'width: 100px;', 'step': '0.01'})
                initial = self.fields[field_name].initial
                if initial is not None:
                    try:
                        self.fields[field_name].initial = f"{float(initial):.2f}"
                    except (ValueError, TypeError):
                        pass


class TransactionInline(admin.TabularInline):
    model = Transaction
    form = TransactionInlineForm
    extra = 0
    ordering = ("date",)
    readonly_fields = ("equity", "action_buttons")
    fields = (
        "project", "date", "transaction_type", "investment",
        "return_amount", "equity", "nav", "x_rate", "action_buttons"
    )
        
    def action_buttons(self, obj):
        """Добавляет кнопки действий для каждой транзакции"""
        if obj and obj.pk:
            return format_html(
                '''
                <div class="transaction-actions">
                    <button type="button" 
                            class="django-btn-edit" 
                            data-id="{}" 
                            title="Редактировать">
                        ✏️
                    </button>
                    <button type="button" 
                            class="django-btn-delete" 
                            data-id="{}" 
                            title="Удалить">
                        🗑️
                    </button>
                </div>
                ''',
                obj.pk, obj.pk
            )
        return ""
    
    action_buttons.short_description = "Actions"


# 1. ДОБАВИТЬ эти классы ПЕРЕД ProjectAdminForm (найдите строку "class ProjectAdminForm" и добавьте ЭТО ВЫШЕ):

class PercentageWidget(forms.NumberInput):
    """
    Кастомный виджет который ВСЕГДА показывает проценты
    """
    
    def format_value(self, value):
        """
        Этот метод вызывается при КАЖДОМ рендере виджета
        """
        if value is None or value == '':
            return ''
        try:
            # 0.15 → "15.00"
            return f"{float(value) * 100:.2f}"
        except (ValueError, TypeError):
            return str(value)

class SimplePercentageField(forms.FloatField):
    """
    Простейшее решение: обычное FloatField + кастомный виджет
    """
    
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', PercentageWidget(attrs={
            'style': 'width: 120px;', 
            'step': '0.01',
            'placeholder': 'Введите проценты (напр. 15.5 для 15.5%)'
        }))
        kwargs.setdefault('help_text', 'Введите значение в процентах (например, 15.5 для 15.5%)')
        super().__init__(*args, **kwargs)
    
    def clean(self, value):
        """
        Конвертируем проценты в десятичное при сохранении
        """
        if value in self.empty_values:
            return None
        
        try:
            # 15.5 → 0.155
            percentage_value = float(value)
            return percentage_value / 100
        except (ValueError, TypeError):
            raise ValidationError('Введите корректное числовое значение для процентов')


# 2. ЗАМЕНИТЬ ВЕСЬ класс ProjectAdminForm на ЭТО:

class ProjectAdminForm(forms.ModelForm):
    # 🔧 КАСТОМНОЕ ПОЛЕ для target_irr
    target_irr = SimplePercentageField(
        label='Target IRR (%)',
        required=False,
        help_text='Введите целевой IRR в процентах (например, 15.5 для 15.5%)'
    )
    
    class Meta:
        model = Project
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 🔧 ОБЫЧНЫЕ FLOAT ПОЛЯ (target_irr теперь кастомный, убрали его отсюда)
        float_fields = ["nav", "estimated_return", "xnpv"]
        for field_name in float_fields:
            if field_name in self.fields:
                self.fields[field_name].widget = forms.NumberInput(
                    attrs={'style': 'width: 120px;', 'step': '0.01'}
                )
                value = self.fields[field_name].initial
                if value is not None:
                    try:
                        self.fields[field_name].initial = f"{float(value):.2f}"
                    except (ValueError, TypeError):
                        pass


@admin.action(description="📊 Print Portfolio Metrics")
def print_portfolio_metrics(modeladmin, request, queryset):
    raw_summary = modeladmin.get_portfolio_summary(queryset)
    
    # Форматируем для печати с правильными значениями
    formatted_summary = {}
    for key, values in raw_summary.items():
        formatted_summary[key] = {}
        for category in ['ALL', 'ACTIVE', 'YTD']:
            value = values.get(category)
            if value is not None:
                if key.upper() in ['XIRR', 'TARGET_IRR', 'GAP_TO_TARGET_IRR', 'PORTFOLIO_AVG_IRR']:
                    # Проценты: умножаем на 100 и добавляем %
                    formatted_summary[key][category] = f"{value * 100:.2f}%"
                elif key.upper() in ['DPI', 'TVPI']:
                    # Множители: добавляем x
                    formatted_summary[key][category] = f"{value:.2f}x"
                elif key.upper() in ['TOTAL_INVESTED', 'TOTAL_RETURNED', 'NAV', 'ESTIMATED_RETURN', 'XNPV']:
                    # Валюты: добавляем $ и запятые
                    formatted_summary[key][category] = f"${value:,.2f}"
                else:
                    formatted_summary[key][category] = f"{value:.2f}"
            else:
                formatted_summary[key][category] = "-"
    
    context = {
        "summary": formatted_summary,
        "categories": ["ALL", "ACTIVE", "YTD"],
        "title": "Portfolio Metrics Summary",
        "now": now(),
    }
    return render(request, "admin/print_portfolio_metrics.html", context)


@admin.action(description="🖨️ Print Selected Projects")
def print_selected_projects(modeladmin, request, queryset):
    project_data = []
    for project in queryset:
        project_data.append({
            'name': project.name,
            'status': project.status,
            'start_date': project.start_date,
            'total_invested': utils.format_dollar_no_symbol(project.get_total_invested()),
            'total_returned': utils.format_dollar_no_symbol(project.get_total_returned()),
            'nav': utils.format_dollar_no_symbol(project.nav),
            'xirr': utils.format_percent(project.get_xirr()),
            'dpi': utils.format_multiple(project.get_dpi()),
            'tvpi': utils.format_multiple(project.get_tvpi()),
            'xnpv': utils.format_dollar_no_symbol(project.get_xnpv()),
            'estimated_return': utils.format_dollar_no_symbol(project.estimated_return),
        })

    return render(request, "admin/print_selected_projects.html", {
        "projects": project_data
    })


@admin.action(description="📤 Export all transactions to CSV")
def export_transactions_action(modeladmin, request, queryset):
    cmd = ExportCommand()
    cmd.handle()
    path = os.path.abspath('export/transactions.csv')
    modeladmin.message_user(request, f"✅ Transactions exported to: {path}")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    change_list_template = "admin/projects_changelist.html"
    change_form_template = "admin/investments/project/change_form.html"
    form = ProjectAdminForm
    list_display = (
        'name', 'target_irr_display', 'status', 'start_date',
        'total_invested', 'total_returned', 'nav_display',
        'xirr_display', 'tvpi_formatted', 'dpi_formatted',
        'rvpi_display',  # ← ДОБАВИТЬ ЭТО!
        'gap_to_target_irr_display', 'estimated_return_display', 'xnpv_formatted'
    )
    inlines = [TransactionInline]
    actions = [
        export_transactions_action,
        print_selected_projects,
        print_portfolio_metrics,
        'calculate_mirr_for_selected',  # НОВОЕ!
        'compare_mirr_vs_xirr'          # НОВОЕ!
    ]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("recalculate/", self.admin_site.admin_view(self.recalculate_all), name="recalculate_all"),
            path('<int:project_id>/validate/', self.admin_site.admin_view(self.validate_project), name='validate_project'),
            path('backup/', self.admin_site.admin_view(self.create_backup), name='create_backup'),
            path('ajax/toggle-edit/<int:transaction_id>/', 
                self.admin_site.admin_view(self.ajax_toggle_edit), 
                name='ajax_toggle_transaction_edit'),
            path('ajax/soft-delete/<int:transaction_id>/', 
                self.admin_site.admin_view(self.ajax_soft_delete), 
                name='ajax_soft_delete_transaction'),
        ]
        return custom_urls + urls

    def validate_project(self, request, project_id):
        project = self.get_object(request, project_id)
        transactions = project.transactions.order_by("date")
        errors = []
        seen_dates = set()
        nav_found = False

        for tx in transactions:
            if not tx.date:
                errors.append(f"❌ Transaction ID {tx.id} is missing a date.")
            # 🔧 УЛУЧШЕННАЯ ВАЛИДАЦИЯ с учетом типа NAV
            if tx.transaction_type == 'Investment':
                if not tx.investment:
                    errors.append(f"❌ Transaction ID {tx.id} is Investment type but has no investment amount.")
            elif tx.transaction_type == 'Return':
                if not tx.return_amount:
                    errors.append(f"❌ Transaction ID {tx.id} is Return type but has no return amount.")
            elif tx.transaction_type == 'NAV':
                if not tx.nav:
                    errors.append(f"❌ Transaction ID {tx.id} is NAV type but has no NAV value.")
            else:
                # Для старых транзакций применяем старую логику
                if not tx.investment and not tx.return_amount:
                    errors.append(f"❌ Transaction ID {tx.id} has neither investment nor return filled.")
            if tx.date in seen_dates:
                errors.append(f"❌ Duplicate transaction date {tx.date} in project {project.name}.")
            seen_dates.add(tx.date)
            if tx.nav:
                nav_found = True

        if not nav_found:
            errors.append(f"⚠️ No NAV recorded for project {project.name}.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            messages.success(request, "✅ Validation passed with no errors.")

        return redirect(f"/admin/investments/project/{project_id}/change/")

    def recalculate_all(self, request):
        from .models import recalculate_all_metrics
        recalculate_all_metrics()
        messages.success(request, "✅ All project metrics recalculated successfully.")
        return redirect("..")

    # Добавьте этот код временно в метод create_backup для диагностики
    def create_backup(self, request):
        """Создает полный backup проекта"""
        try:
            from django.conf import settings
            
            # 🎯 ИСПРАВЛЕНИЕ: Используем Django settings.BASE_DIR вместо расчета через __file__
            base_dir = settings.BASE_DIR
            backup_dir = os.path.join(base_dir, "BackupInvestmentDjango")
            os.makedirs(backup_dir, exist_ok=True)

            print(f"✅ ИСПРАВЛЕННЫЙ base_dir: {base_dir}")

            # Имя архива с временной меткой
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M')
            archive_name = f"InvestmentDjango_{timestamp}.zip"
            archive_path = os.path.join(backup_dir, archive_name)

            # Список файлов и папок для включения в backup
            include_items = [
                "manage.py",
                "db.sqlite3", 
                "investments",
                "tracker",
                "scripts",
                "static",
                "export",
                "urls.py",
                "requirements.txt", 
                "README.md",
                "VERSION.txt",
                "install.sh",
                "RunApplication.command",
                ".env.example"
            ]

            # Список исключений
            exclude_patterns = [
                "__pycache__",
                "*.pyc", 
                ".DS_Store",
                "venv",
                "env",
                ".git",
                "node_modules",
                ".pytest_cache",
                "BackupInvestmentDjango"
            ]

            files_added = 0
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # НЕ меняем директорию! Работаем с абсолютными путями
                
                for item in include_items:
                    item_path = os.path.join(base_dir, item)
                    print(f"🔍 Checking: {item} -> {item_path}")
                    
                    if os.path.isfile(item_path):
                        # Добавляем файл
                        print(f"✅ Adding file: {item}")
                        zipf.write(item_path, item)  # item как архивное имя (без полного пути)
                        files_added += 1
                    elif os.path.isdir(item_path):
                        # Добавляем директорию рекурсивно
                        print(f"✅ Adding directory: {item}")
                        
                        for root, dirs, files in os.walk(item_path):
                            # Исключаем нежелательные директории
                            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]
                            
                            for file in files:
                                # Исключаем нежелательные файлы
                                if any(pattern in file for pattern in exclude_patterns):
                                    continue
                                    
                                file_path = os.path.join(root, file)
                                # 🎯 КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ: правильный архивный путь
                                arc_path = os.path.relpath(file_path, base_dir)
                                zipf.write(file_path, arc_path)
                                files_added += 1
                                print(f"   📄 Added: {arc_path}")
                    else:
                        print(f"❌ Not found: {item_path}")

            # Получаем размер архива
            archive_size = round(os.path.getsize(archive_path) / (1024 * 1024), 2)
            
            # Подсчитываем количество файлов в архиве
            with zipfile.ZipFile(archive_path, 'r') as zipf:
                file_count = len(zipf.namelist())
                print(f"✅ Archive created with {file_count} files")
                print("📋 First 20 files in archive:")
                for i, filename in enumerate(zipf.namelist()[:20]):
                    print(f"  {i+1:2d}. {filename}")
                if file_count > 20:
                    print(f"     ... and {file_count - 20} more files")

            success_message = (
                f"✅ Backup created successfully!\n"
                f"📦 Location: {archive_path}\n" 
                f"📊 Size: {archive_size} MB\n"
                f"📁 Files: {file_count}\n"
                f"📅 Created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            messages.success(request, success_message)
            return render(request, "admin/backup.html", {
                'backup_info': {
                    'path': archive_path,
                    'size': f"{archive_size} MB", 
                    'file_count': file_count,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            })

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"❌ Backup error: {error_details}")
            error_message = f"❌ Backup failed: {str(e)}"
            messages.error(request, error_message)
            return redirect("/admin/")

        # ==================== НОВЫЕ МЕТОДЫ mIRR (строка 476) ====================

    @admin.action(description='📊 Calculate mIRR for selected projects')
    def calculate_mirr_for_selected(self, request, queryset):
        """Расчет mIRR для выбранных проектов"""
        from investments.metrics import calculate_portfolio_mirr
        
        if queryset.count() == 0:
            messages.error(request, "Please select at least one project")
            return
        
        # Рассчитываем mIRR
        mirr = calculate_portfolio_mirr(
            queryset,
            finance_rate=0.08,
            reinvest_rate=0.06
        )
        
        # Собираем статистику
        total_invested = sum(p.get_total_invested() or 0 for p in queryset)
        total_returned = sum(p.get_total_returned() or 0 for p in queryset)
        total_nav = sum(p.get_nav() or 0 for p in queryset if p.status == 'active')
        
        # XIRR для сравнения
        xirr_values = []
        for p in queryset:
            xirr = p.get_xirr()
            if xirr:
                xirr_values.append(xirr * 100)
        
        avg_xirr = sum(xirr_values) / len(xirr_values) if xirr_values else None
        
        # Показываем результат
        if mirr:
            tvpi = (total_returned + total_nav) / total_invested if total_invested else 0
            message = f"""
            ✅ mIRR Analysis Results:
            ━━━━━━━━━━━━━━━━━━━━
            Projects: {queryset.count()}
            Portfolio mIRR: {mirr:.2f}%
            Avg XIRR: {avg_xirr:.2f}% if avg_xirr else 'N/A'
            Invested: ${total_invested:,.0f}
            Returned: ${total_returned:,.0f}
            NAV: ${total_nav:,.0f}
            TVPI: {tvpi:.2f}x
            """
            messages.success(request, message)
        else:
            messages.error(request, "Could not calculate mIRR")
        
        return  # Остаемся на странице
    
    @admin.action(description='📈 Compare mIRR vs XIRR')
    def compare_mirr_vs_xirr(self, request, queryset):
        """Сравнение mIRR с XIRR для каждого проекта"""
        from investments.metrics import calculate_portfolio_mirr
        
        if queryset.count() == 0:
            messages.error(request, "Please select at least one project")
            return
        
        # Сравнение для каждого проекта
        comparison = []
        for project in queryset:
            single_mirr = calculate_portfolio_mirr([project])
            xirr = project.get_xirr()
            xirr_percent = xirr * 100 if xirr else None
            
            if single_mirr and xirr_percent:
                diff = abs(single_mirr - xirr_percent)
                comparison.append(
                    f"• {project.name}: mIRR={single_mirr:.1f}% | XIRR={xirr_percent:.1f}% | Δ={diff:.1f}%"
                )
            else:
                comparison.append(
                    f"• {project.name}: mIRR={single_mirr:.1f}% | XIRR=N/A"
                )
        
        # Общий mIRR
        portfolio_mirr = calculate_portfolio_mirr(queryset)
        
        message = f"""
        📊 mIRR vs XIRR Comparison:
        
        Portfolio mIRR: {portfolio_mirr:.2f}%
        
        Individual projects:
        {chr(10).join(comparison)}
        """
        
        messages.info(request, message)
        return
    
    # ==================== КОНЕЦ НОВЫХ МЕТОДОВ ====================

    def get_portfolio_summary(self, queryset):
        from investments.utils import compute_project_metrics

        def sum_metric(projects, metric):
            values = []
            for project in projects:
                value = compute_project_metrics(project).get(metric)
                if isinstance(value, (int, float)):
                    values.append(value)
            return round(sum(values), 2) if values else None

        def avg_metric(projects, metric):
            values = []
            for project in projects:
                value = compute_project_metrics(project).get(metric)
                if isinstance(value, (int, float)):
                    values.append(value)
            return round(sum(values) / len(values), 4) if values else None

        def compute_weighted_tvpi(projects):
            total_invested = 0.0
            total_value = 0.0
            for project in projects:
                invested = project.get_total_invested() or 0
                returned = project.get_total_returned() or 0
                nav = project.get_nav() or 0
                total_invested += invested
                total_value += returned + nav
            return round(total_value / total_invested, 2) if total_invested else None

        current_year = datetime.datetime.now().year
        all_projects = queryset
        active_projects = [p for p in queryset if str(p.status).strip().lower() == 'active']
        ytd_projects = [p for p in queryset if p.transactions.filter(date__year=current_year).exists()]

        metrics = ['total_invested', 'total_returned', 'nav', 'estimated_return',
               'xirr', 'target_irr', 'gap_to_target_irr', 'dpi']
                        
        summary = {}
        for metric in metrics:
            method = avg_metric if metric in ['xirr', 'target_irr', 'gap_to_target_irr', 'dpi'] else sum_metric
            summary[metric.upper()] = {
                'ALL': method(all_projects, metric),
                'ACTIVE': method(active_projects, metric),
                'YTD': method(ytd_projects, metric),
            }

        # Отдельная обработка TVPI
        summary['TVPI'] = {
            'ALL': compute_weighted_tvpi(all_projects),
            'ACTIVE': compute_weighted_tvpi(active_projects),
            'YTD': compute_weighted_tvpi(ytd_projects),
        }

                # После блока с TVPI добавьте:
        # Portfolio RVPI (взвешенный)
        summary['RVPI'] = {
            'ALL': round(sum(p.get_nav() or 0 for p in all_projects) / 
                        sum(p.get_total_invested() or 0 for p in all_projects), 4) 
                if sum(p.get_total_invested() or 0 for p in all_projects) > 0 else 0,
            'ACTIVE': round(sum(p.get_nav() or 0 for p in active_projects) / 
                            sum(p.get_total_invested() or 0 for p in active_projects), 4)
                    if sum(p.get_total_invested() or 0 for p in active_projects) > 0 else 0,
            'YTD': round(sum(p.get_nav() or 0 for p in ytd_projects if p.status == 'active') / 
                        sum(p.get_total_invested() or 0 for p in ytd_projects), 4)
                if sum(p.get_total_invested() or 0 for p in ytd_projects) > 0 else 0,
        }


    # Portfolio Average IRR (mIRR) - новая метрика
        try:
            from investments.models import Portfolio
            from investments.metrics import calculate_portfolio_mirr as calc_mirr
            
            portfolio, _ = Portfolio.objects.get_or_create(
                name="Main Portfolio",
                defaults={'mirr_finance_rate': 0.08, 'mirr_reinvest_rate': 0.06}
            )
            
            # Конвертируем в списки для функции
            all_list = list(all_projects)
            active_list = list(active_projects)
            ytd_list = list(ytd_projects)
            
            # Расчет mIRR для каждой категории
            all_mirr = calc_mirr(all_list, portfolio.mirr_finance_rate, portfolio.mirr_reinvest_rate) if all_list else None
            active_mirr = calc_mirr(active_list, portfolio.mirr_finance_rate, portfolio.mirr_reinvest_rate) if active_list else None
            ytd_mirr = calc_mirr(ytd_list, portfolio.mirr_finance_rate, portfolio.mirr_reinvest_rate) if ytd_list else None
            
            # calc_mirr возвращает проценты (15.5), конвертируем в десятичное (0.155) для консистентности
            summary['PORTFOLIO_AVG_IRR'] = {
                'ALL': all_mirr / 100 if all_mirr is not None else None,
                'ACTIVE': active_mirr / 100 if active_mirr is not None else None,
                'YTD': ytd_mirr / 100 if ytd_mirr is not None else None,
            }
        except Exception as e:
            print(f"[Portfolio mIRR Error] {e}")
            import traceback
            traceback.print_exc()
            summary['PORTFOLIO_AVG_IRR'] = {'ALL': None, 'ACTIVE': None, 'YTD': None}

        return summary

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        if isinstance(response, TemplateResponse):
            try:
                cl = response.context_data['cl']
                queryset = cl.queryset
                
                # Получаем сырые данные БЕЗ форматирования
                raw_summary = self.get_portfolio_summary(queryset)

                print("=" * 50)
                print("PORTFOLIO_AVG_IRR в raw_summary:", 'PORTFOLIO_AVG_IRR' in raw_summary)
                print("Все ключи в raw_summary:", list(raw_summary.keys()))
                
                # Передаем СЫРЫЕ данные в шаблон
                response.context_data['portfolio_summary'] = raw_summary
                response.context_data['table_class'] = 'table-unified'
                
            except Exception as e:
                print(f"❌ ERROR in changelist_view: {e}")
                response.context_data['portfolio_summary'] = {}
        else:
            response.context_data = getattr(response, 'context_data', {})
            response.context_data['portfolio_summary'] = {}

        return response

    def render_change_form(self, request, context, *args, **kwargs):
        response = super().render_change_form(request, context, *args, **kwargs)
        obj = context.get("original")
        if obj:
            validate_url = reverse("admin:validate_project", args=[obj.pk])
            if "adminform" in context:
                context["adminform"].form.fields["name"].help_text = (
                    f"<a class='button' href='{validate_url}' "
                    f"style='margin-left: 20px; font-size: 13px;'>🧪 Validate Project (Debug Only)</a>"
                )
        return response

    def start_date(self, obj):
        return obj.get_start_date()

    # Display методы
    @admin.display(description="Total Invested (USD)")
    def total_invested(self, obj):
        value = obj.get_total_invested()
        return f"{value:,.2f}" if value is not None else "-"

    @admin.display(description="Total Returned (USD)")
    def total_returned(self, obj):
        value = obj.get_total_returned()
        return f"{value:,.2f}" if value is not None else "-"

    @admin.display(description="Target IRR (%)")
    def target_irr_display(self, obj):
        if obj.target_irr is not None:
            return f"{obj.target_irr * 100:.2f}"
        return "-"

    @admin.display(description="XIRR (%)")
    def xirr_display(self, obj):
        xirr = obj.get_xirr()
        if xirr is not None:
            return f"{xirr * 100:.2f}"
        return "-"

    @admin.display(description="TVPI")
    def tvpi_formatted(self, obj):
        tvpi = obj.get_tvpi()
        return f"{tvpi:.2f}" if tvpi is not None else "-"

    @admin.display(description="DPI")
    def dpi_formatted(self, obj):
        dpi = obj.get_dpi()
        return f"{dpi:.2f}" if dpi is not None else "-"
    
    @admin.display(description="RVPI")
    def rvpi_display(self, obj):
        rvpi_data = obj.get_rvpi()
        rvpi = rvpi_data['value']    
        if obj.status == 'closed':
            # Для закрытых проектов RVPI всегда 0
            return format_html('<span style="color: #999;">—</span>')
        
        # Цветовая кодировка
        if rvpi > 1.0:
            color = '#00aa00'  # зеленый - отлично
        elif rvpi > 0.5:
            color = '#ff9900'  # оранжевый - хорошо
        elif rvpi > 0:
            color = '#7c3aed'  # фиолетовый - низко
        else:
            color = '#999999'  # серый - ноль
            
        rvpi_formatted = f"{rvpi:.2f}"  # Форматируем заранее
        return format_html(
            '<span style="color: {}; font-weight: 600;">{}x</span>',
            color, rvpi_formatted
        )
    
    @admin.display(description="Gap to Target IRR (%)")
    def gap_to_target_irr_display(self, obj):
        gap = obj.get_gap_to_target_irr()
        if gap is not None:
            return f"{gap * 100:.2f}"
        return "-"

    @admin.display(description="Estimated Return (USD)")
    def estimated_return_display(self, obj):
        return f"{obj.estimated_return:,.2f}" if obj.estimated_return is not None else "-"

    @admin.display(description="XNPV (USD)")
    def xnpv_formatted(self, obj):
        value = obj.get_xnpv()
        return f"{value:,.2f}" if value is not None else "-"

    @admin.display(description="NAV (USD)")
    def nav_display(self, obj):
        return f"{obj.nav:,.2f}" if obj.nav is not None else "-"

    # AJAX методы
    @method_decorator(csrf_exempt)
    def ajax_toggle_edit(self, request, transaction_id):
        """AJAX обработчик переключения режима редактирования"""
        if request.method == 'POST':
            try:
                transaction = Transaction.objects.get(id=transaction_id)
                
                # Сохраняем состояние в сессии
                edit_mode = set(request.session.get('edit_mode_transactions', []))
                
                if transaction_id in edit_mode:
                    edit_mode.discard(transaction_id)
                    status = 'readonly'
                    message = 'Режим только для чтения'
                else:
                    edit_mode.add(transaction_id)
                    status = 'editable'
                    message = 'Режим редактирования включен'
                
                request.session['edit_mode_transactions'] = list(edit_mode)
                
                return JsonResponse({
                    'status': 'success',
                    'mode': status,
                    'message': message,
                    'transaction_id': transaction_id
                })
            except Transaction.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Транзакция не найдена'
                })
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                })
        
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})

    @method_decorator(csrf_exempt)
    def ajax_soft_delete(self, request, transaction_id):
        """AJAX обработчик мягкого удаления"""
        if request.method == 'POST':
            try:
                transaction = Transaction.objects.get(id=transaction_id)
                
                # Сохраняем ID для удаления в сессии
                delete_queue = set(request.session.get('delete_queue_transactions', []))
                delete_queue.add(transaction_id)
                request.session['delete_queue_transactions'] = list(delete_queue)
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Транзакция помечена для удаления. Нажмите "SAVE" для применения.',
                    'transaction_id': transaction_id
                })
            except Transaction.DoesNotExist:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Транзакция не найдена'
                })
            except Exception as e:
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                })
        
        return JsonResponse({'status': 'error', 'message': 'Invalid request'})

    class Media:
        css = {
            'all': (
                'admin/css/custom_admin.css',
                'admin/css/tables-unified.css',
                'admin/css/transaction_actions.css',
            )
        }
        js = ('admin/js/transaction_actions.js',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "project", "date", "transaction_type",
        "investment", "return_amount", "equity", "nav", "x_rate"
    )
    list_filter = ("project", "transaction_type")
    ordering = ("-date",)
    readonly_fields = ("equity",)

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, **kwargs)
        if isinstance(db_field, models.FloatField):
            formfield.widget = forms.NumberInput(attrs={'style': 'width: 100px;', 'step': '0.01'})
            def clean_float(val):
                try:
                    return f"{float(val):.2f}"
                except (ValueError, TypeError):
                    return val
            if hasattr(formfield, 'initial') and formfield.initial is not None:
                formfield.initial = clean_float(formfield.initial)
        return formfield

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'total_projects',
        'portfolio_mirr_display',
        'portfolio_xirr_comparison',
        'total_invested_display',
    ]

    def total_projects(self, obj):
        return Project.objects.count()
    total_projects.short_description = 'Projects'

    def portfolio_mirr_display(self, obj):
        """Новый метод — mIRR (стабильный)"""
        mirr = obj.calculate_portfolio_mirr()
        if mirr is None:
            return "-"
        try:
            val = float(mirr)
        except (TypeError, ValueError):
            return "-"
        return format_html(
            '<span style="color: green; font-weight: 600;">{}%</span>',
            f"{val:.2f}"
        )
    portfolio_mirr_display.short_description = 'Portfolio mIRR'

    def portfolio_xirr_comparison(self, obj):
        """Старый метод для сравнения"""
        try:
            xirr = obj.calculate_portfolio_xirr_old()
        except Exception:
            return format_html('<span style="color: red;">Multiple IRR</span>')
        if xirr is None:
            return "-"
        try:
            return f"{float(xirr)*100:.2f}%"
        except (TypeError, ValueError):
            return "-"
    portfolio_xirr_comparison.short_description = 'Old XIRR (compare)'

    def total_invested_display(self, obj):
        """Сводка по суммам; форматируем числа до вставки в HTML"""
        metrics = obj.get_portfolio_metrics() or {}

        def to_num(v, default=0.0):
            try:
                return float(v)
            except (TypeError, ValueError):
                return default

        invested = to_num(metrics.get('total_invested'))
        returned = to_num(metrics.get('total_returned'))
        nav = to_num(metrics.get('total_nav'))

        return format_html(
            'Invested: ${}<br>Returned: ${}<br>NAV: ${}',
            f"{invested:,.0f}",
            f"{returned:,.0f}",
            f"{nav:,.0f}",
        )
    total_invested_display.short_description = 'Portfolio Summary'
#@admin.register(ProjectAlert) 
#class ProjectAlertAdmin(admin.ModelAdmin):
    #list_display = ['project', 'alert_type', 'severity', 'created_at', 'resolved']
    #list_filter = ['severity', 'resolved', 'alert_type']
    #actions = ['mark_resolved']
    
    #def mark_resolved(self, request, queryset):
        #queryset.update(resolved=True, resolved_at=datetime.datetime.now())
    #mark_resolved.short_description = "Mark selected alerts as resolved"  
# === ИМПОРТ АДМИНКИ АЛЕРТОВ === 
# Добавьте эти строки в конец файла admin.py
try:
    from .alerts_admin import (
        AlertTypeAdmin, ProjectAlertAdmin,
        AlertSettingsAdmin, AlertRuleAdmin, 
        AlertLogAdmin, AlertStatisticsAdmin
    )
    print("✅ Alert admin loaded successfully")
except ImportError as e:
    print(f"⚠️ Alert admin not loaded: {e}")    