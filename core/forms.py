from django import forms
from .models import BOQItem, Project

class BOQItemForm(forms.ModelForm):
    class Meta:
        model = BOQItem
        fields = ['item_code', 'description', 'unit', 'planned_quantity', 'rate', 'approved_quantity', 'parent', 'level']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'item_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 01'}),
            'unit': forms.Select(attrs={'class': 'form-control'}),
            'planned_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'approved_quantity': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'readonly': 'readonly'}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
            'level': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        project_id = kwargs.pop('project_id', None)
        super().__init__(*args, **kwargs)
        if project_id:
            self.fields['parent'].queryset = BOQItem.objects.filter(project_id=project_id)