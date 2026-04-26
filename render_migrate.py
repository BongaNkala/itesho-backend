import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'itesho.settings')
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model

print("Running migrations...")
call_command('migrate', interactive=False)

print("Creating superuser...")
User = get_user_model()
if not User.objects.filter(username='bonga').exists():
    User.objects.create_superuser('bonga', 'admin@itesho.com', 'bonga')
    print("Superuser 'bonga' created!")
else:
    print("Superuser already exists.")
