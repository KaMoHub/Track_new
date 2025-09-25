# apps/events/forms.py
from django import forms
from .models import Event
from .widgets import CustomDateInput


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'description', 'level', 'application_deadline',
                  'result_date', 'is_active', 'is_offline', 'sort_order']
        widgets = {
            'application_deadline': CustomDateInput(),
            'result_date': CustomDateInput(),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_offline': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_application_deadline(self):
        date_str = self.cleaned_data.get('application_deadline')
        if date_str:
            try:
                # Преобразуем строку в формате дд.мм.гггг в дату
                from datetime import datetime
                return datetime.strptime(date_str, '%d.%m.%Y').date()
            except ValueError:
                raise forms.ValidationError('Введите дату в формате ДД.ММ.ГГГГ')
        return date_str

    def clean_result_date(self):
        date_str = self.cleaned_data.get('result_date')
        if date_str:
            try:
                # Преобразуем строку в формате дд.мм.гггг в дату
                from datetime import datetime
                return datetime.strptime(date_str, '%d.%м.%Y').date()
            except ValueError:
                raise forms.ValidationError('Введите дату в формате ДД.ММ.ГГГГ')
        return date_str