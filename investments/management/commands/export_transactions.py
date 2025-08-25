import csv
import os
from django.core.management.base import BaseCommand
from investments.models import Transaction

EXPORT_DIR = 'export'
EXPORT_FILE = 'transactions.csv'

class Command(BaseCommand):
    help = 'Export all transactions to CSV'

    def handle(self, *args, **options):
        os.makedirs(EXPORT_DIR, exist_ok=True)
        filepath = os.path.join(EXPORT_DIR, EXPORT_FILE)

        headers = [
            'Project',
            'Date',
            'Type',
            'Investment',
            'Return',
            'Equity',
            'NAV',
            'X-Rate',
        ]

        transactions = Transaction.objects.select_related('project').order_by('project__name', 'date')

        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)

            for tx in transactions:
                writer.writerow([
                    tx.project.name,
                    tx.date,
                    tx.transaction_type,
                    round(tx.investment or 0, 2),
                    round(tx.return_amount or 0, 2),
                    round(tx.equity or 0, 2),
                    round(tx.nav or 0, 2),
                    round(tx.x_rate or 1, 4),
                ])

        self.stdout.write(self.style.SUCCESS(f'Exported {transactions.count()} transactions to {filepath}'))
