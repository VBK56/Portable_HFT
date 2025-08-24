from django.core.management.base import BaseCommand
from investments.models import Project

class Command(BaseCommand):
    help = "Update all project metrics (XIRR, TVPI, DPI, etc.)"

    def handle(self, *args, **kwargs):
        projects = Project.objects.all()
        count = 0
        for project in projects:
            try:
                project.update_metrics()
                project.save()
                count += 1
                self.stdout.write(f"✅ Updated: {project.name}")
            except Exception as e:
                self.stderr.write(f"❌ Error updating {project.name}: {e}")
        self.stdout.write(self.style.SUCCESS(f"✔ Done. Updated {count} projects."))