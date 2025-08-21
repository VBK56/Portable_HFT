import os
import pandas as pd
from django.core.management.base import BaseCommand
from investments.models import Project, Transaction
from django.utils.dateparse import parse_date


class Command(BaseCommand):
    help = "Import investment data from Excel file"

    def add_arguments(self, parser):
        parser.add_argument("filepath", type=str, help="Path to Excel file")

    def handle(self, *args, **kwargs):
        filepath = kwargs["filepath"]
        if not os.path.exists(filepath):
            self.stdout.write(self.style.ERROR(f"❌ File not found: {filepath}"))
            return

        xls = pd.ExcelFile(filepath)
        for sheet_name in xls.sheet_names:
            df = xls.parse(sheet_name)
            project_name = sheet_name.strip()
            self.stdout.write(f"\n📄 Processing sheet: {project_name}")

            project, created = Project.objects.get_or_create(name=project_name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"✅ Created new project: {project_name}"))
            else:
                self.stdout.write(self.style.WARNING(f"⚠️ Using existing project: {project_name}"))

            created_count = 0

            for _, row in df.iterrows():
                print("🔍 ROW:", row.to_dict())

                date = parse_date(str(row.get("Date")))
                tx_type = str(row.get("Transaction Type")).strip()
                investment = row.get("Investment ($)", 0) or 0
                returned = row.get("Return ($)", 0) or 0
                equity = row.get("Equity ($)", None)
                nav = row.get("NAV ($)", None)
                cash_flow = row.get("Cash Flow ($)", None)

                if not date or not tx_type:
                    print("⛔️ Skipping row due to missing date or type")
                    continue

                Transaction.objects.create(
                    project=project,
                    date=date,
                    transaction_type=tx_type,
                    investment=investment,
                    return_amount=returned,
                    equity=equity,
                    cash_flow=cash_flow,
                    nav=nav,
                )

                created_count += 1

            self.stdout.write(self.style.SUCCESS(f"📥 Imported {created_count} transactions for: {project_name}"))