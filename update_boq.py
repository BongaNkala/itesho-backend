import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'itesho.settings')
django.setup()

from core.models import DailyLog, BOQItem
from django.db.models import Sum

print("Starting BOQ update for approved logs...")

for log in DailyLog.objects.filter(status='approved'):
    print(f"Processing log {log.id}...")
    for entry in log.entries.all():
        boq_item = entry.boq_item
        boq_item.approved_quantity += entry.quantity
        boq_item.save()
        
        parent = boq_item.parent
        while parent:
            total = parent.children.aggregate(total=Sum('approved_quantity'))['total'] or 0
            parent.approved_quantity = total
            parent.save()
            parent = parent.parent
    
    log.project.update_progress()
    print(f"Updated BOQ for log {log.id}")

print("Done!")
