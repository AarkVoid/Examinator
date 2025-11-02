from django.core.management.base import BaseCommand
from django.contrib.auth.models import Permission

class Command(BaseCommand):
    help = "Save all Django permissions into a text file"

    def handle(self, *args, **kwargs):
        permissions = Permission.objects.all().order_by("content_type__app_label", "codename")
        with open("django_permissions.txt", "w") as f:
            for perm in permissions:
                line = f"{perm.content_type.app_label}.{perm.codename} - {perm.name}\n"
                f.write(line)
        self.stdout.write(self.style.SUCCESS("Permissions saved to django_permissions.txt"))
