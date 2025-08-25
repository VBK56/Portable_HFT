# ✅ ПОЛНОСТЬЮ ИСПРАВЛЕННЫЙ utils.py
# Устранены все критические ошибки

from datetime import datetime, date
from typing import List, Tuple, Optional
from scipy.optimize import newton

# --- XIRR и XNPV ---

def xnpv(rate: float, cashflows: List[Tuple[datetime, float]]) -> float:
    """Расчет XNPV для datetime объектов"""
    t0 = cashflows[0][0]
    return sum(cf / (1 + rate) ** ((t - t0).days / 365.0) for t, cf in cashflows)

def xirr(cashflows: List[Tuple[datetime, float]], guess: float = 0.1) -> Optional[float]:
    """Расчет XIRR используя метод Ньютона"""
    try:
        return newton(lambda r: xnpv(r, cashflows), guess)
    except Exception:
        return None

# ✅ ИСПРАВЛЕНО: Убрано дублирование, оставлена одна корректная функция
def calculate_xnpv(amounts, dates, rate):
    """
    Расчет XNPV (Net Present Value) для списка кэшфлоу
    
    Args:
        amounts: список сумм кэшфлоу
        dates: список дат (date объекты)
        rate: ставка дисконтирования (например, 0.042 для 4.2%)
    
    Returns:
        float: приведенная стоимость или None при ошибке
    """
    try:
        if not amounts or not dates:
            return None
        
        if len(amounts) != len(dates):
            return None

        t0 = dates[0]

        # Обработка нулевой ставки
        if rate == 0:
            return round(sum(amounts), 2)

        # Основной расчет XNPV
        return round(
            sum(cf / (1 + rate) ** ((dt - t0).days / 365.0) for cf, dt in zip(amounts, dates)),
            2
        )
    except Exception as e:
        print(f"[XNPV ERROR] {e}")
        return None

# --- Метрики проекта ---

def calculate_xirr(project):
    """Расчет XIRR для проекта с учетом его статуса"""
    from scipy.optimize import root_scalar

    # Получаем cash flows с учетом статуса проекта
    cashflows = project.get_cash_flows(include_nav=True)
    
    if not cashflows or len(cashflows) < 2:
        return None

    # Проверяем, что есть хотя бы один положительный и один отрицательный поток
    has_positive = any(cf > 0 for _, cf in cashflows)
    has_negative = any(cf < 0 for _, cf in cashflows)
    
    if not (has_positive and has_negative):
        print(f"[XIRR WARNING] {project.name}: Missing positive or negative cash flows")
        return None

    def xnpv_func(rate):
        try:
            return calculate_xnpv(
                [cf for _, cf in cashflows],
                [dt for dt, _ in cashflows],
                rate
            )
        except Exception:
            return float("nan")

    try:
        # Для закрытых убыточных проектов XIRR может быть сильно отрицательным
        # Расширяем диапазон поиска
        result = root_scalar(
            xnpv_func,
            bracket=[-0.99, 10],  # от -99% до 1000%
            method="brentq"
        )
        
        if result.converged:
            irr_value = round(result.root, 6)
            print(f"[XIRR SUCCESS] {project.name} ({project.status}): {irr_value:.2%}")
            return irr_value
        else:
            print(f"[XIRR ERROR] {project.name}: Did not converge")
            return None
            
    except Exception as e:
        print(f"[XIRR ERROR] {project.name}: {e}")
        # Для отладки выводим cash flows
        print(f"  Cash flows: {cashflows}")
        return None

# ✅ ИСПРАВЛЕНО: Заменено project.get_start_date() на project.start_date
def calculate_project_duration_years(project):
    """Расчет длительности проекта в годах"""
    start = project.start_date  # ✅ Используем поле модели напрямую
    if not start:
        return 0
    return (date.today() - start).days / 365.25

def calculate_gap_to_target_irr(project):
    """Расчет разрыва между фактическим и целевым IRR"""
    actual = calculate_xirr(project)
    target = project.target_irr
    if actual is None or target is None:
        return None
    return round(actual - target, 4)

def calculate_dpi(project):
    """Distribution to Paid-In ratio"""
    try:
        invested = project.get_total_invested()
        returned = project.get_total_returned()
        if not invested:
            return None
        return round(returned / invested, 2)
    except Exception:
        return None

def calculate_tvpi(project):
    """Total Value to Paid-In ratio с учетом статуса проекта"""
    try:
        invested = project.get_total_invested()
        returned = project.get_total_returned()
        
        if invested is None or invested == 0:
            return 0.0

        if project.status == 'active':
            # Для активных проектов включаем NAV
            nav = project.get_nav() or 0
            total_value = (returned or 0) + (nav or 0)
        else:
            # Для закрытых проектов только возвраты
            total_value = returned or 0
        
        result = round(total_value / invested, 2)
        return result
    except Exception as e:
        print(f"[TVPI ERROR] {e}")
        return 0.0

def calculate_estimated_return(project):
    """Расчет оценочной доходности"""
    try:
        cash_flows = project.get_cash_flows()
        irr = project.target_irr or 0.0
        if not cash_flows or irr <= 0:
            return None

        today = date.today()
        total = 0.0
        for tx_date, amount in cash_flows:
            if amount < 0:
                years = (today - tx_date).days / 365.25
                future_value = -amount * (1 + irr) ** years
                total += future_value
        return round(total, 2)
    except Exception:
        return None

def calculate_estimated_return_to_date(invested, target_irr, start_date, status=None, end_date=None, transactions=None):
    """Расчет оценочной доходности на конкретную дату"""
    try:
        if not invested or not target_irr or not start_date:
            return None

        today = date.today()

        if status == "Closed" and transactions:
            last_txn_date = max((t.date for t in transactions), default=None)
            final_date = last_txn_date or today
        elif status == "Active":
            final_date = end_date or today
        else:
            final_date = today

        if final_date <= start_date:
            return None

        years = (final_date - start_date).days / 365.25
        projected = invested * ((1 + target_irr) ** years)
        return round(projected, 2)
    except Exception:
        return None

def calculate_moic(project):
    """Multiple on Invested Capital"""
    try:
        invested = project.get_total_invested()
        returned = project.get_total_returned()
        nav = project.get_nav() or 0

        if not invested or invested == 0:
            return None

        return (returned + nav) / invested
    except Exception:
        return None

def calculate_moic_with_status(project):
    """Multiple on Invested Capital с учетом статуса проекта"""
    try:
        invested = project.get_total_invested()
        returned = project.get_total_returned()
        
        if not invested or invested == 0:
            return None

        if project.status == 'active':
            # Для активных проектов включаем NAV
            nav = project.get_nav() or 0
            return (returned + nav) / invested
        else:
            # Для закрытых проектов только возвраты
            return returned / invested
    except Exception:
        return None

# ✅ ДОБАВЛЕНО: Недостающая функция calculate_npv
def calculate_npv(project):
    """NPV проекта - алиас для get_xnpv"""
    return project.get_xnpv()

# --- Централизованное форматирование ---

def format_dollar(value):
    """Форматирование в доллары с символом $"""
    if value is None:
        return "-"
    try:
        return f"${float(value):,.2f}"
    except:
        return "-"

def format_dollar_no_symbol(value):
    """Форматирование в доллары без символа"""
    if value is None:
        return "-"
    try:
        return f"{float(value):,.2f}"
    except:
        return "-"

def format_percent(value):
    """Форматирование в проценты"""
    if value is None:
        return "-"
    try:
        return f"{value * 100:.2f}%"
    except:
        return "-"

def format_ratio(numerator, denominator):
    """Форматирование отношения"""
    if not denominator:
        return "-"
    try:
        return f"{numerator / denominator:.2f}x"
    except:
        return "-"

def format_multiple(value):
    """Форматирование множителя"""
    if value is None:
        return "-"
    try:
        return f"{float(value):.2f}x"
    except:
        return "-"

def format_moic(value):
    """Форматирование MOIC"""
    if value is None:
        return "-"
    try:
        return f"{float(value):.2f}x"
    except:
        return "-"

def safe_sum(values):
    """Безопасное суммирование с обработкой None"""
    try:
        return round(sum(v for v in values if v is not None), 2)
    except:
        return 0.0

# ✅ ДОБАВЛЕНО: Недостающая функция safe_ratio
def safe_ratio(numerator, denominator):
    """Безопасное деление с обработкой None и нуля"""
    try:
        if denominator is None or denominator == 0:
            return None
        if numerator is None:
            return None
        return round(numerator / denominator, 4)
    except:
        return None

# --- Короткие псевдонимы ---
safe_dollar = format_dollar_no_symbol
safe_dollar_admin = format_dollar_no_symbol
safe_percent = format_percent
gap_to_target = calculate_gap_to_target_irr  # ✅ Алиас для совместимости
estimate_return = calculate_estimated_return

# ✅ ИСПРАВЛЕНО: Теперь все функции существуют
def compute_project_metrics(project):
    """Вычисление всех метрик проекта с учетом статуса"""
    nav_value = project.nav if project.status == 'active' else 0
    
    return {
        'total_invested': project.get_total_invested(),
        'total_returned': project.get_total_returned(),
        'nav': nav_value,
        'estimated_return': project.estimated_return or 0,
        'xirr': project.get_xirr(),
        'target_irr': project.target_irr,
        'gap_to_target_irr': project.get_gap_to_target_irr(),
        'TVPI': calculate_tvpi(project),  # Теперь учитывает статус
        'dpi': project.get_dpi(),
        'moic': project.get_moic(),
        'final_npv': calculate_npv(project),
        'status': project.status  # Добавляем статус для отладки
    }