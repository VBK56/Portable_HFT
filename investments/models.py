from django.db import models
from datetime import datetime, timedelta, date
from .utils import (
    calculate_estimated_return,
    gap_to_target,  # ✅ Алиас есть в utils.py
    calculate_xnpv,
    safe_sum,
    safe_ratio,  # ✅ Функция есть в utils.py
    calculate_xirr,
    calculate_tvpi,
    calculate_dpi,
    calculate_gap_to_target_irr,
    calculate_estimated_return_to_date,
)


class Project(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
    ]

    name = models.CharField(max_length=255)
    target_irr = models.FloatField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active'
    )

    created_at = models.DateField(auto_now_add=True)
    end_date = models.DateField(null=True, blank=True)
    invested = models.FloatField(null=True, blank=True)
    returned = models.FloatField(null=True, blank=True)
    irr = models.FloatField(null=True, blank=True)
    tvpi = models.FloatField(null=True, blank=True)
    dpi = models.FloatField(null=True, blank=True)
    gap_to_target = models.FloatField(null=True, blank=True)
    xnpv = models.FloatField(null=True, blank=True)
    nav = models.FloatField(null=True, blank=True, default=0)
    estimated_return = models.FloatField(null=True, blank=True)
    moic = models.FloatField(null=True, blank=True)
    moic_source = models.CharField(
        max_length=20,
        choices=[('provided', 'Provided'), ('calculated', 'Calculated')],
        null=True, blank=True
    )

    def __str__(self):
        return self.name

    def get_transactions(self):
        """Получить все транзакции проекта, отсортированные по дате"""
        return self.transactions.order_by("date")

    def get_total_invested(self):
        """Получить общую сумму инвестиций"""
        return safe_sum(t.investment_usd for t in self.get_transactions())

    def get_total_returned(self):
        """Получить общую сумму возвратов"""
        return safe_sum(t.return_usd for t in self.get_transactions())

    def get_nav(self):
        """Получить текущую стоимость активов (NAV) с учетом статуса проекта"""
        if self.status == 'closed':
            # Для закрытых проектов NAV должен быть 0
            return 0
        
        # Для активных проектов ищем последнее значение NAV или equity
        latest_nav_txn = self.transactions.exclude(nav__isnull=True).order_by("-date").first()
        if latest_nav_txn:
            return round(latest_nav_txn.nav_usd, 2)
        
        # Если NAV нет, используем последнее значение equity
        last_equity_txn = self.transactions.exclude(equity__isnull=True).order_by("-date").first()
        if last_equity_txn:
            return round(last_equity_txn.equity_usd, 2)
        
        return 0

    def get_last_equity(self):
        """Получить последнее значение equity"""
        last_tx = self.transactions.exclude(equity__isnull=True).order_by("-date").first()
        return last_tx.equity_usd if last_tx else None

    def is_nav_missing(self):
        """Проверить, отсутствует ли NAV"""
        return not self.nav and self.get_total_returned() == 0

# Изменения в models.py - метод get_cash_flows класса Project

    def get_cash_flows(self, include_nav=False):
        """
        Получить кэшфлоу проекта с учетом статуса (Active/Closed)
        """
        cash_flows = []
        
        # Добавляем все транзакции
        for t in self.transactions.order_by("date"):
            if t.investment_usd:
                cash_flows.append((t.date, -t.investment_usd))
            if t.return_usd:
                cash_flows.append((t.date, t.return_usd))

        # Логика зависит от статуса проекта
        if include_nav:
            if self.status == 'active':
                nav = self.get_nav()
                if nav and nav != 0:
                    # КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Находим дату последней транзакции с NAV
                    # Это будет датой последней оценки актива
                    last_nav_transaction = self.transactions.exclude(
                        nav__isnull=True
                    ).exclude(
                        nav=0
                    ).order_by("-date").first()
                    
                    if last_nav_transaction:
                        # Используем дату транзакции, когда был установлен NAV
                        nav_date = last_nav_transaction.date
                    else:
                        # Если NAV не был записан в транзакциях, 
                        # используем дату последней транзакции любого типа
                        last_transaction = self.transactions.order_by("-date").first()
                        nav_date = last_transaction.date if last_transaction else date.today()
                    
                    cash_flows.append((nav_date, abs(nav)))
                    print(f"[DEBUG] Active project {self.name}: added NAV {abs(nav)} on date {nav_date} (not today!)")
            
            elif self.status == 'closed':
                # Для закрытых проектов не добавляем NAV
                print(f"[DEBUG] Closed project {self.name}: NAV not added (should be in final transaction)")
        
        return cash_flows

    def get_xirr(self):
        """Получить XIRR проекта"""
        return calculate_xirr(self)

    def get_tvpi(self):
        """Получить TVPI проекта"""
        return calculate_tvpi(self)

    def get_dpi(self):
        """Получить DPI проекта"""
        return calculate_dpi(self)

    def get_gap_to_target_irr(self):
        """Получить разрыв между фактическим и целевым IRR"""
        return calculate_gap_to_target_irr(self)

    def get_xnpv(self):
        """Получить XNPV проекта"""
        if self.target_irr is None:
            return None
        
        cash_flows = self.get_cash_flows(include_nav=True)
        amounts = [cf[1] for cf in cash_flows]
        dates = [cf[0] for cf in cash_flows]
        
        return calculate_xnpv(amounts, dates, self.target_irr)

    def get_moic(self):
        """Получить MOIC проекта"""
        if self.moic is not None:
            return self.moic
        
        # Импортируем здесь, чтобы избежать циклических импортов
        from .utils import calculate_moic_with_status
        return calculate_moic_with_status(self)

    def update_metrics(self):
        """Обновить все метрики проекта с учетом статуса"""
        transactions = self.get_transactions()
        invested = safe_sum(t.investment_usd for t in transactions)
        returned = safe_sum(t.return_usd for t in transactions)
        
        # NAV зависит от статуса
        if self.status == 'active':
            nav = self.get_nav()  # Положительное значение для активных
        else:
            nav = 0  # Для закрытых проектов NAV = 0
        
        # Получаем кэшфлоу для расчетов
        cash_flows = self.get_cash_flows(include_nav=True)
        amounts = [amt for _, amt in cash_flows]
        dates = [dt for dt, _ in cash_flows]

        # Обновляем основные метрики
        self.invested = invested
        self.returned = returned
        self.nav = nav
        self.irr = calculate_xirr(self)

        # TVPI расчет зависит от статуса
        if self.status == 'active':
            # Для активных: (возвраты + текущая стоимость) / инвестиции
            self.tvpi = round((returned + nav) / invested, 4) if invested else None
        else:
            # Для закрытых: только возвраты / инвестиции
            self.tvpi = round(returned / invested, 4) if invested else None
        
        self.dpi = round(returned / invested, 4) if invested else None
        self.gap_to_target = gap_to_target(self)

        # MOIC также учитывает статус
        if self.moic is None:
            from .utils import calculate_moic_with_status
            calculated_moic = calculate_moic_with_status(self)
            if calculated_moic is not None:
                self.moic = round(calculated_moic, 4)
                self.moic_source = 'calculated'
        else:
            self.moic_source = 'provided'

        # Оценочная доходность
        est_return = calculate_estimated_return_to_date(
            invested=invested,
            target_irr=self.target_irr,
            start_date=self.start_date,
            status=self.status,
            end_date=self.end_date,
            transactions=transactions
        )
        self.estimated_return = round(est_return, 2) if est_return is not None else None

        # XNPV
        if self.target_irr is not None:
            xnpv_val = calculate_xnpv(amounts, dates, self.target_irr)
            self.xnpv = round(xnpv_val, 4) if xnpv_val is not None else None
        else:
            self.xnpv = None

    def save(self, *args, **kwargs):
        """Сохранить проект с обновлением метрик"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Обновляем метрики только для существующих проектов
        if not is_new:
            self.update_metrics()
            super().save(update_fields=[
                "invested", "returned", "irr", "tvpi", "dpi",
                "gap_to_target", "xnpv", "nav", "estimated_return",
                "moic", "moic_source"
            ])

    def horizon_years(self):
        """Получить горизонт проекта в годах"""
        if self.start_date and self.end_date and self.end_date > self.start_date:
            delta = self.end_date - self.start_date
            return delta.days / 365.0
        return 1

    def get_rvpi(self):
        """
        Residual Value to Paid-In (RVPI)
        Показывает какая часть стоимости еще не реализована (в NAV)
        Формула: RVPI = NAV / Total Invested
        Для закрытых проектов всегда 0 (нет остаточной стоимости)
        Для активных показывает unrealized множитель
        Returns:
            dict: RVPI значение и цвет для отображения
        """
        # Закрытые проекты не имеют остаточной стоимости
        if self.status == 'closed':
            return {'value': 0.0, 'color': 'gray'}
        
        # Получаем общие инвестиции
        invested = self.get_total_invested()
        if not invested or invested == 0:
            return {'value': 0.0, 'color': 'gray'}
        
        # Получаем текущий NAV
        nav = self.get_nav() or 0
        
        # RVPI = NAV / Invested
        rvpi = nav / invested
        
        # Определяем цвет
        if rvpi >= 1.0:
            color = 'green'
        elif rvpi >= 0.5:
            color = 'orange'
        else:
            color = 'purple'
        
        return {
            'value': round(rvpi, 4),
            'color': color
        }
    
    def validate_metrics_formula(self):
        """
        Проверка ключевого соотношения: TVPI = DPI + RVPI
        Это фундаментальное уравнение в Private Equity
        
        Returns:
            dict: {'valid': bool, 'message': str, 'values': dict}
        """
        tvpi = self.get_tvpi() or 0
        dpi = self.get_dpi() or 0  
        rvpi = self.get_rvpi() or 0
        
        expected_tvpi = dpi + rvpi
        difference = abs(tvpi - expected_tvpi)
        
        # Допуск 0.01 на округление
        is_valid = difference <= 0.01
        
        return {
            'valid': is_valid,
            'message': f"TVPI ({tvpi:.3f}) = DPI ({dpi:.3f}) + RVPI ({rvpi:.3f}) = {expected_tvpi:.3f}",
            'difference': difference,
            'tvpi': tvpi,
            'dpi': dpi,
            'rvpi': rvpi
        }


class Transaction(models.Model):
    """Модель транзакции проекта"""
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="transactions")
    date = models.DateField()
    
    TRANSACTION_TYPES = [
        ("Investment", "Investment"),
        ("Return", "Return"),
        ("NAV", "NAV Update"), 
    ]

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    investment = models.FloatField(null=True, blank=True, help_text="Сумма инвестиции")
    return_amount = models.FloatField(null=True, blank=True, help_text="Сумма возврата")
    equity = models.FloatField(null=True, blank=True, editable=False, help_text="Накопленная equity")
    nav = models.FloatField(null=True, blank=True, help_text="Net Asset Value")
    x_rate = models.FloatField(null=True, blank=True, default=1.0, help_text="Курс валют")

    def __str__(self):
        return f"{self.project.name} - {self.date}"

    def save(self, *args, **kwargs):
        """Сохранить транзакцию с автоматическим заполнением и расчетом equity"""
        
        # 🔧 АВТОМАТИЧЕСКОЕ ЗАПОЛНЕНИЕ в зависимости от типа
        if self.transaction_type == 'Investment':
            if not self.investment:
                self.investment = 0
            self.return_amount = 0  # Обнуляем return для инвестиций
            
        elif self.transaction_type == 'Return':
            if not self.return_amount:
                self.return_amount = 0  
            self.investment = 0  # Обнуляем investment для возвратов
            
        elif self.transaction_type == 'NAV':
            # Для NAV обнуляем и investment и return
            self.investment = 0
            self.return_amount = 0
            if not self.nav:
                self.nav = 0

        # Расчет equity для всех типов кроме NAV
        if self.transaction_type in ['Investment', 'Return']:
            # Находим предыдущую транзакцию для расчета equity
            previous = Transaction.objects.filter(
                project=self.project,
                date__lt=self.date
            ).order_by('-date').first()

            previous_equity = previous.equity if previous else 0
            invest = self.investment or 0
            ret = self.return_amount or 0

            # Equity = предыдущая equity + инвестиции - возвраты
            self.equity = round(previous_equity + invest - ret, 2)
        else:
            # Для NAV транзакций equity не изменяется
            if not self.equity:
                self.equity = 0

        super().save(*args, **kwargs)

    @property
    def investment_usd(self):
        """Инвестиция в USD"""
        return (self.investment or 0) * (self.x_rate or 1)

    @property
    def return_usd(self):
        """Возврат в USD"""
        return (self.return_amount or 0) * (self.x_rate or 1)

    @property
    def equity_usd(self):
        """Equity в USD"""
        return (self.equity or 0) * (self.x_rate or 1)

    @property
    def nav_usd(self):
        """NAV в USD"""
        return (self.nav or 0) * (self.x_rate or 1)

    class Meta:
        ordering = ['date']


def recalculate_all_metrics():
    """Пересчитать метрики для всех проектов"""
    for project in Project.objects.all():
        project.update_metrics()
        project.save()

# Добавить в конец investments/models.py

class Portfolio(models.Model):
    """
    Модель портфеля для агрегированных расчетов
    """
    name = models.CharField(max_length=255, default="Main Portfolio")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Ставки для mIRR расчетов портфеля
    mirr_finance_rate = models.FloatField(
        default=0.08,
        help_text="Стоимость капитала = USD инфляция (3%) + премия за риск (5%) = 8%"
    )
    mirr_reinvest_rate = models.FloatField(
        default=0.06,
        help_text="Ставка реинвестирования = USD инфляция (3%) + мин. премия (3%) = 6%"
    )
    
    class Meta:
        verbose_name = "Portfolio"
        verbose_name_plural = "Portfolios"
    
    def __str__(self):
        return self.name
    
    def get_all_projects(self):
        """Получить все проекты (для будущего можно добавить фильтрацию)"""
        return Project.objects.all()
    
    def get_active_projects(self):
        """Получить только активные проекты"""
        return Project.objects.filter(status='active')
    
    def calculate_portfolio_xirr_old(self):
        """
        СТАРЫЙ метод - может давать множественные IRR
        Оставляем для сравнения
        """
        from .utils import xirr
        
        # Собираем все потоки
        all_flows = []
        for project in self.get_all_projects():
            cash_flows = project.get_cash_flows(include_nav=True)
            all_flows.extend(cash_flows)
        
        if not all_flows:
            return None
        
        # Сортируем по дате
        all_flows.sort(key=lambda x: x[0])
        
        # Конвертируем в datetime для xirr функции
        datetime_flows = [(datetime.combine(dt, datetime.min.time()), amt) 
                         for dt, amt in all_flows]
        
        try:
            return xirr(datetime_flows)
        except Exception as e:
            print(f"[Portfolio XIRR] Error: {e}")
            return None
    
    def calculate_portfolio_mirr(self):
        """
        НОВЫЙ метод - используем mIRR для стабильного решения
        Это основной метод для Portfolio Average IRR!
        """
        from .metrics import calculate_portfolio_mirr
        
        projects = self.get_all_projects()
        return calculate_portfolio_mirr(
            projects,
            finance_rate=self.mirr_finance_rate,
            reinvest_rate=self.mirr_reinvest_rate
        )
    
    def calculate_portfolio_average_irr(self):
        """
        Portfolio Average IRR - теперь использует mIRR!
        """
        return self.calculate_portfolio_mirr()
    
    def get_portfolio_metrics(self):
        """Получить все метрики портфеля"""
        projects = self.get_all_projects()
        active_projects = self.get_active_projects()
        
        # Суммарные показатели
        total_invested = sum(p.get_total_invested() or 0 for p in projects)
        total_returned = sum(p.get_total_returned() or 0 for p in projects)
        total_nav = sum(p.nav or 0 for p in active_projects)
        
        # Portfolio TVPI
        portfolio_tvpi = (total_returned + total_nav) / total_invested if total_invested else 0
        
        # Portfolio DPI
        portfolio_dpi = total_returned / total_invested if total_invested else 0
        
        return {
            'total_projects': projects.count(),
            'active_projects': active_projects.count(),
            'total_invested': total_invested,
            'total_returned': total_returned,
            'total_nav': total_nav,
            'portfolio_tvpi': round(portfolio_tvpi, 2),
            'portfolio_dpi': round(portfolio_dpi, 2),
            'portfolio_xirr_old': self.calculate_portfolio_xirr_old(),  # Может быть None при multiple IRR
            'portfolio_mirr': self.calculate_portfolio_mirr(),  # Всегда стабильное решение
            'portfolio_average_irr': self.calculate_portfolio_average_irr()  # Использует mIRR
        }

    
    def get_portfolio_rvpi(self):
        """
        Взвешенный Portfolio RVPI
        Показывает общую unrealized часть портфеля
        
        Формула: Portfolio RVPI = Total NAV / Total Invested
        
        НЕ среднее RVPI проектов, а взвешенное по размеру!
        """
        # Считаем общий NAV только активных проектов
        total_nav = 0
        total_invested = 0
        
        for project in Project.objects.all():
            invested = project.get_total_invested() or 0
            total_invested += invested
            
            if project.status == 'active':
                nav = project.get_nav() or 0
                total_nav += nav
        
        if total_invested == 0:
            return 0.0
            
        portfolio_rvpi = total_nav / total_invested
        
        return round(portfolio_rvpi, 4)
    
def get_portfolio_metrics(self):
    """
    Возвращает все метрики портфеля
    """
    projects = Project.objects.all()
    
    # Базовые финансовые метрики
    total_invested = sum(p.get_total_invested() or 0 for p in projects)
    total_returned = sum(p.get_total_returned() or 0 for p in projects)
    total_nav = sum(p.get_nav() or 0 for p in projects if p.status == 'active')
    
    # DPI и TVPI
    dpi = total_returned / total_invested if total_invested > 0 else 0
    tvpi = (total_returned + total_nav) / total_invested if total_invested > 0 else 0
    
    # RVPI
    portfolio_rvpi = self.get_portfolio_rvpi()
    
    # Валидация формулы
    expected_tvpi = dpi + portfolio_rvpi
    formula_check = abs(tvpi - expected_tvpi) <= 0.01
    
    return {
        'total_invested': total_invested,
        'total_returned': total_returned,
        'total_nav': total_nav,
        'dpi': round(dpi, 2),
        'tvpi': round(tvpi, 2),
        'portfolio_rvpi': portfolio_rvpi,
        'formula_check': formula_check
    }

# Также добавляем поля mIRR в модель Project (опционально для отдельных проектов)
# Найдите класс Project и добавьте эти поля после существующих полей:

# В классе Project добавить поля (найдите строку где определены поля):
    # mirr_finance_rate = models.FloatField(
    #     default=0.10,
    #     null=True,
    #     blank=True,
    #     help_text="Finance rate for mIRR calculation (0.10 = 10%)"
    # )
    # mirr_reinvest_rate = models.FloatField(
    #     default=0.12,
    #     null=True,
    #     blank=True,
    #     help_text="Reinvestment rate for mIRR calculation (0.12 = 12%)"
    # )

# И добавить метод в класс Project (найдите где методы):
    # def calculate_mirr(self):
    #     """
    #     Рассчитать mIRR для проекта (дополнительная метрика, не замена XIRR!)
    #     """
    #     from .metrics import calculate_mirr
    #     
    #     cash_flows_data = self.get_cash_flows(include_nav=True)
    #     if not cash_flows_data:
    #         return None
    #     
    #     dates = [cf[0] for cf in cash_flows_data]
    #     amounts = [cf[1] for cf in cash_flows_data]
    #     
    #     mirr = calculate_mirr(
    #         amounts, 
    #         dates,
    #         self.mirr_finance_rate or 0.10,
    #         self.mirr_reinvest_rate or 0.12
    #     )
    #     
    #     return round(mirr * 100, 2) if mirr else None  # В процентах        