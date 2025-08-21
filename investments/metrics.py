# investments/metrics.py
"""
Модуль для расчета Modified IRR (mIRR) и других продвинутых метрик
Используется ТОЛЬКО для Portfolio Average, не заменяет XIRR для проектов!
"""

from datetime import datetime, date
from typing import List, Tuple, Optional
import numpy as np


def calculate_mirr(cash_flows: List[float], 
                  dates: List[date], 
                  finance_rate: float = 0.08, 
                  reinvest_rate: float = 0.06) -> Optional[float]:
    """
    Modified IRR - решает проблему множественных IRR при агрегации портфеля
    
    Args:
        cash_flows: Список денежных потоков (отрицательные = инвестиции, положительные = возвраты)
        dates: Список дат транзакций
        finance_rate: Ставка финансирования для отрицательных потоков (default 10%)
        reinvest_rate: Ставка реинвестирования для положительных потоков (default 12%)
    
    Returns:
        mIRR как десятичное число (0.15 = 15%) или None при ошибке
    """
    if not cash_flows or not dates:
        return None
    
    if len(cash_flows) != len(dates):
        return None
    
    # Разделяем положительные и отрицательные потоки
    negative_flows = []
    positive_flows = []
    
    for i, cf in enumerate(cash_flows):
        if cf < 0:
            negative_flows.append((cf, dates[i]))
        elif cf > 0:
            positive_flows.append((cf, dates[i]))
    
    # Проверяем, что есть и инвестиции, и возвраты
    if not negative_flows or not positive_flows:
        print(f"[mIRR] Недостаточно данных: negative={len(negative_flows)}, positive={len(positive_flows)}")
        return None
    
    # Базовая и конечная даты
    base_date = min(dates)
    end_date = max(dates)
    
    # PV отрицательных потоков при finance_rate
    pv_negative = 0
    for cf, cf_date in negative_flows:
        years = (cf_date - base_date).days / 365.25
        pv_negative += abs(cf) / ((1 + finance_rate) ** years)
    
    # FV положительных потоков при reinvest_rate  
    fv_positive = 0
    for cf, cf_date in positive_flows:
        years = (end_date - cf_date).days / 365.25
        fv_positive += cf * ((1 + reinvest_rate) ** years)
    
    # Общий период в годах
    total_years = (end_date - base_date).days / 365.25
    
    if total_years <= 0 or pv_negative <= 0:
        return None
    
    # Расчет mIRR
    try:
        mirr = (fv_positive / pv_negative) ** (1 / total_years) - 1
        print(f"[mIRR] Calculated: {mirr:.4f} ({mirr*100:.2f}%)")
        return mirr
    except Exception as e:
        print(f"[mIRR] Calculation error: {e}")
        return None


def calculate_portfolio_mirr(projects, finance_rate: float = 0.08, reinvest_rate: float = 0.06) -> Optional[float]:
    """
    Расчет Portfolio Average IRR используя mIRR
    ВАЖНО: Это НЕ среднее mIRR проектов, а mIRR от ВСЕХ агрегированных потоков!
    
    Args:
        projects: QuerySet или список проектов
        finance_rate: Ставка финансирования
        reinvest_rate: Ставка реинвестирования
    
    Returns:
        Portfolio mIRR в процентах или None
    """
    # Собираем ВСЕ транзакции от всех проектов
    all_flows = []
    
    for project in projects:
        # Получаем транзакции проекта
        for transaction in project.transactions.all():
            # Инвестиции - отрицательные
            if transaction.investment:
                all_flows.append({
                    'date': transaction.date,
                    'amount': -abs(transaction.investment_usd),
                    'project': project.name
                })
            
            # Возвраты - положительные
            if transaction.return_amount:
                all_flows.append({
                    'date': transaction.date, 
                    'amount': abs(transaction.return_usd),
                    'project': project.name
                })
    
    # Добавляем текущий NAV для активных проектов
    for project in projects:
        if project.status == 'active' and project.nav and project.nav > 0:
            # Используем сегодняшнюю дату для NAV
            all_flows.append({
                'date': date.today(),
                'amount': project.nav,
                'project': f"{project.name} (NAV)"
            })
    
    if not all_flows:
        print("[Portfolio mIRR] No cash flows found")
        return None
    
    # Сортируем по датам
    all_flows.sort(key=lambda x: x['date'])
    
    # Извлекаем списки для расчета
    cash_flows = [f['amount'] for f in all_flows]
    dates = [f['date'] for f in all_flows]
    
    print(f"[Portfolio mIRR] Total flows: {len(cash_flows)}")
    print(f"[Portfolio mIRR] Date range: {dates[0]} to {dates[-1]}")
    print(f"[Portfolio mIRR] Total invested: ${sum(cf for cf in cash_flows if cf < 0):,.0f}")
    print(f"[Portfolio mIRR] Total returned + NAV: ${sum(cf for cf in cash_flows if cf > 0):,.0f}")
    
    # Рассчитываем mIRR
    mirr = calculate_mirr(cash_flows, dates, finance_rate, reinvest_rate)
    
    if mirr is not None:
        return round(mirr * 100, 2)  # Возвращаем в процентах
    return None