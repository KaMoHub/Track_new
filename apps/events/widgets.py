# apps/events/widgets.py
from django import forms


class CustomDateInput(forms.TextInput):
    input_type = 'text'

    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control',
            'placeholder': 'дд.мм.гггг',
            'autocomplete': 'off',
            'maxlength': '10'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)