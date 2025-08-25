import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from investments.models import Project, Transaction

class Command(BaseCommand):
    help = 'Validate investment data and export issues to CSV'

    def handle(self, *args, **kwargs):
        print("Running investment data validation...\n")

        report_path = os.path.join("investments", "reports")
        os.makedirs(report_path, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d")
        report_file = os.path.join(report_path, f"validation_report_{timestamp}.csv")

        issues = []

        for project in Project.objects.all():
            print(f"Validating project: {project.name}")
            transactions = Transaction.objects.filter(project=project).order_by("date")

            seen_dates = set()
            latest_nav = None

            for tx in transactions:
                if tx.date in seen_dates:
                    issues.append([project.name, tx.date, tx.transaction_type, "Duplicate date detected"])
                else:
                    seen_dates.add(tx.date)

                if tx.transaction_type in ["Investment", "Return"]:
                    if tx.equity is None:
                        issues.append([project.name, tx.date, tx.transaction_type, "Missing Equity"])

                if tx.nav is not None:
                    if latest_nav is None or tx.date > latest_nav[0]:
                        latest_nav = (tx.date, tx.nav)
                    elif tx.date == latest_nav[0] and tx.nav != latest_nav[1]:
                        issues.append([project.name, tx.date, tx.transaction_type, "Conflicting NAV on same date"])

            # Проверка наличия NAV
            if latest_nav is None:
                issues.append([project.name, "-", "-", "Project NAV not set (no NAV found in transactions)"])
            elif project.nav != latest_nav[1]:
                issues.append([project.name, latest_nav[0], "-", f"Mismatch between project.nav and latest NAV: {project.nav} vs {latest_nav[1]}"])

        if issues:
            with open(report_file, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Project", "Date", "Type", "Issue"])
                for row in issues:
                    writer.writerow(row)

            print(f"⚠️  Validation completed with issues. See report: {report_file}\n")
        else:
            print("✅ No issues found. All data is valid.\n")
