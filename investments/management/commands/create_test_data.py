from django.core.management.base import BaseCommand
from investments.models import Project, Transaction
from datetime import date

class Command(BaseCommand):
    help = 'Create test projects with transactions for 5 years'

    def handle(self, *args, **options):
        # Очистка старых тестовых данных
        Project.objects.filter(name__startswith='Test').delete()
        
        # Проект 1: Alpha Strategy
        alpha = Project.objects.create(
            name='Test Alpha Strategy',
            target_irr=0.15,  # 15%
            status='Active',
            start_date=date(2019, 1, 15),
            nav=2500000.0
        )
        
        # Транзакции для Alpha Strategy
        transactions_alpha = [
            (date(2019, 1, 15), 'Investment', 1000000.0, 0.0),
            (date(2019, 12, 31), 'Return', 0.0, 150000.0),
            (date(2020, 6, 15), 'Investment', 500000.0, 0.0),
            (date(2021, 3, 20), 'Return', 0.0, 200000.0),
            (date(2022, 8, 10), 'Return', 0.0, 300000.0),
            (date(2023, 12, 31), 'Return', 0.0, 400000.0)
        ]
        
        for tx_date, tx_type, investment, return_amount in transactions_alpha:
            Transaction.objects.create(
                project=alpha,
                date=tx_date,
                transaction_type=tx_type,
                investment=investment if investment > 0 else None,
                return_amount=return_amount if return_amount > 0 else None,
                nav=2500000.0,
                x_rate=1.0
            )
        
        # Проект 2: Market Neutral Fund
        neutral = Project.objects.create(
            name='Test Market Neutral Fund',
            target_irr=0.12,  # 12%
            status='Closed',
            start_date=date(2020, 3, 1),
            nav=0.0
        )
        
        # Транзакции для Market Neutral
        transactions_neutral = [
            (date(2020, 3, 1), 'Investment', 2000000.0, 0.0),
            (date(2020, 12, 15), 'Return', 0.0, 250000.0),
            (date(2021, 6, 30), 'Return', 0.0, 300000.0),
            (date(2022, 12, 31), 'Return', 0.0, 400000.0),
            (date(2023, 6, 15), 'Return', 0.0, 500000.0),
            (date(2024, 6, 30), 'Return', 0.0, 800000.0)
        ]
        
        for tx_date, tx_type, investment, return_amount in transactions_neutral:
            Transaction.objects.create(
                project=neutral,
                date=tx_date,
                transaction_type=tx_type,
                investment=investment if investment > 0 else None,
                return_amount=return_amount if return_amount > 0 else None,
                nav=0.0 if tx_date == date(2024, 6, 30) else 1500000.0,
                x_rate=1.0
            )
        
        # Проект 3: Tech Growth
        tech = Project.objects.create(
            name='Test Tech Growth',
            target_irr=0.18,  # 18%
            status='Active',
            start_date=date(2021, 9, 1),
            nav=800000.0
        )
        
        # Транзакции для Tech Growth
        transactions_tech = [
            (date(2021, 9, 1), 'Investment', 1500000.0, 0.0),
            (date(2022, 3, 15), 'Return', 0.0, 100000.0),
            (date(2022, 12, 20), 'Investment', 300000.0, 0.0),
            (date(2023, 8, 10), 'Return', 0.0, 80000.0),
            (date(2024, 2, 28), 'Return', 0.0, 120000.0),
        ]
        
        for tx_date, tx_type, investment, return_amount in transactions_tech:
            Transaction.objects.create(
                project=tech,
                date=tx_date,
                transaction_type=tx_type,
                investment=investment if investment > 0 else None,
                return_amount=return_amount if return_amount > 0 else None,
                nav=800000.0,
                x_rate=1.0
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Created 3 test projects with 17 transactions over 5 years'
            )
        )
