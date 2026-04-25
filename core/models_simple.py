from django.db import models
from django.contrib.auth.models import User

class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=50, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name


class BOQItem(models.Model):
    UNIT_CHOICES = [
        ('m³', 'm³'), ('m²', 'm²'), ('m', 'm'), ('ton', 'ton'),
        ('kg', 'kg'), ('each', 'each'), ('hour', 'hour'), ('day', 'day'),
        ('lump_sum', 'Lump Sum'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='boq_items')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    
    item_code = models.CharField(max_length=50)
    description = models.TextField()
    unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default='each')
    level = models.IntegerField(default=1)
    
    planned_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    actual_quantity = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    rate = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'item_code']
    
    def __str__(self):
        return f"{self.item_code} - {self.description}"
    
    @property
    def planned_cost(self):
        return self.planned_quantity * self.rate
    
    @property
    def actual_cost(self):
        return self.actual_quantity * self.rate
    
    @property
    def progress_percentage(self):
        if self.planned_quantity > 0:
            return (self.actual_quantity / self.planned_quantity) * 100
        return 0
