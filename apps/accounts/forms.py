# apps/accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, UserProfile


class CustomUserCreationForm(UserCreationForm):
    """Форма создания пользователя"""
    first_name = forms.CharField(max_length=30, required=True, label='Имя')
    last_name = forms.CharField(max_length=30, required=True, label='Фамилия')
    email = forms.EmailField(required=True, label='Email')

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'password1', 'password2')


class CustomUserChangeForm(UserChangeForm):
    """Форма редактирования пользователя"""

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role')


class UserProfileForm(forms.ModelForm):
    """Форма редактирования профиля пользователя"""

    class Meta:
        model = UserProfile
        fields = ('academic_year_start', 'academic_year_end', 'default_level_filter', 'items_per_page')
        widgets = {
            'academic_year_start': forms.NumberInput(attrs={'class': 'form-control'}),
            'academic_year_end': forms.NumberInput(attrs={'class': 'form-control'}),
            'default_level_filter': forms.Select(attrs={'class': 'form-control'}),
            'items_per_page': forms.Select(
                choices=[(10, '10'), (20, '20'), (50, '50'), (100, '100')],
                attrs={'class': 'form-control'}
            ),
        }