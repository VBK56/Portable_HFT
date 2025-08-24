import csv
import os
from decimal import Decimal, InvalidOperation
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from investments.models import Project, Transaction


class Command(BaseCommand):
    help = "Import transactions from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str, help="Path to CSV file")

    def handle(self, *args, **kwargs):
        filepath = kwargs["filepath"]

        if not os.path.exists(filepath):
            self.stderr.write(f"❌ File not found: {filepath}")
            return

        with open(filepath, newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            count = 0

            for row in reader:
                project_name = row.get("project", "").strip()
                date = parse_date(row.get("date", "").strip())
                tx_type = row.get("transaction_type", "").strip()

                # Надёжное чтение чисел как Decimal
                def parse_decimal(value):
                    try:
                        return Decimal(value.strip()) if value and value.strip() else None
                    except (InvalidOperation, AttributeError):
                        return None

                investment = parse_decimal(row.get("investment"))
                returned = parse_decimal(row.get("return"))
                equity = parse_decimal(row.get("equity"))
                nav = parse_decimal(row.get("nav"))
                cash_flow = parse_decimal(row.get("cash_flow"))

                if not project_name or not date or not tx_type:
                    self.stdout.write(f"⛔ Skipping incomplete row: {row}")
                    continue

                project, _ = Project.objects.get_or_create(name=project_name)

                Transaction.objects.create(
                    project=project,
                    date=date,
                    transaction_type=tx_type,
                    investment=investment or Decimal("0"),
                    return_amount=returned or Decimal("0"),
                    equity=equity,
                    nav=nav,
                    cash_flow=cash_flow,
                )

                count += 1

            self.stdout.write(self.style.SUCCESS(f"✅ Imported {count} transactions."))