from django.core.management.base import BaseCommand
from investments.models import Transaction

class Command(BaseCommand):
    help = "Removes duplicate transactions from the database."

    def handle(self, *args, **options):
        seen = set()
        duplicates = []

        for tx in Transaction.objects.all().order_by('project_id', 'date'):
            key = (
                tx.project_id,
                tx.date,
                float(tx.investment_usd or 0),
                float(tx.return_usd or 0),
                float(tx.equity_usd or 0),
                float(tx.nav_usd or 0),
                float(tx.x_rate or 1),
            )
            if key in seen:
                duplicates.append(tx.id)
            else:
                seen.add(key)

        if duplicates:
            count = len(duplicates)
            Transaction.objects.filter(id__in=duplicates).delete()
            self.stdout.write(self.style.SUCCESS(f"✅ Removed {count} duplicate transactions."))
        else:
            self.stdout.write(self.style.SUCCESS("✅ No duplicates found."))