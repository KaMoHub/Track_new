# apps/accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
    """Расширенная модель пользователя"""
    ROLE_CHOICES = [
        ('teacher', 'Педагог'),
        ('methodist', 'Методист'),
        ('admin', 'Администратор'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='teacher',
        verbose_name='Роль'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class UserProfile(models.Model):
    """Профиль пользователя с дополнительными настройками"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    academic_year_start = models.IntegerField(
        default=2024,
        verbose_name='Начало учебного года'
    )
    academic_year_end = models.IntegerField(
        default=2025,
        verbose_name='Конец учебного года'
    )
    default_level_filter = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Фильтр по уровням по умолчанию'
    )
    items_per_page = models.IntegerField(
        default=20,
        verbose_name='Записей на странице'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'

    def __str__(self):
        return f"Профиль {self.user.username}"

    @property
    def academic_year(self):
        return f"{self.academic_year_start}-{self.academic_year_end}"


class UserActionLog(models.Model):
    """Лог действий пользователей"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    action_type = models.CharField(
        max_length=50,
        verbose_name='Тип действия'
    )
    table_name = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Таблица'
    )
    record_id = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='ID записи'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name='IP адрес'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата действия'
    )

    class Meta:
        verbose_name = 'Лог действий'
        verbose_name_plural = 'Логи действий'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.action_type} - {self.created_at}"