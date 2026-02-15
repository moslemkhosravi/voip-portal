from django.core.management.base import BaseCommand
import os
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Create superuser from env vars if not exists"

    def handle(self, *args, **opts):
        u=os.environ.get("DJANGO_SUPERUSER_USERNAME","")
        e=os.environ.get("DJANGO_SUPERUSER_EMAIL","")
        p=os.environ.get("DJANGO_SUPERUSER_PASSWORD","")
        if not (u and p):
            self.stdout.write("No superuser env vars set; skipping.")
            return
        User=get_user_model()
        if User.objects.filter(username=u).exists():
            self.stdout.write("Superuser exists; skipping.")
            return
        User.objects.create_superuser(username=u, email=e or "", password=p)
        self.stdout.write("Superuser created.")
