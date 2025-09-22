# apps/events/models.py
from django.db import models
from django.urls import reverse
from django.conf import settings

from ..participation.models import Participation


class Event(models.Model):
    """Модель конкурса/мероприятия"""
    LEVEL_CHOICES = [
        ('center', 'Центровский'),
        ('city', 'Городской'),
        ('district', 'Районный'),
        ('republic', 'Республиканский'),
        ('regional', 'Региональный'),
        ('interregional', 'Межрегиональный'),
        ('allrussian', 'Всероссийский'),
        ('international', 'Международный'),
    ]

    name = models.CharField(
        max_length=255,
        verbose_name='Название конкурса'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        verbose_name='Уровень'
    )
    application_deadline = models.DateField(
        null=True,
        blank=True,
        verbose_name='Срок подачи заявок'
    )
    result_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата объявления результатов'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    sort_order = models.IntegerField(
        default=0,
        verbose_name='Порядок сортировки'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Создал'
    )

    class Meta:
        verbose_name = 'Конкурс'
        verbose_name_plural = 'Конкурсы'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('events:detail', kwargs={'pk': self.pk})

    def can_be_deleted(self):
        """Проверка, можно ли удалить конкурс"""
        # Проверяем, есть ли участия в этом конкурсе
        try:
            from ..participation.models import Participation
            if Participation.objects.filter(event=self).exists():
                return False
            return True
        except:
            # Если приложение participation недоступно, разрешаем удаление
            return True

    def get_related_objects(self):
        """Получение списка связанных объектов"""
        related = {}
        try:
            from ..participation.models import Participation
            participations = Participation.objects.filter(event=self)
            if participations.exists():
                related['Участия детей'] = participations.count()
        except:
            pass
        return related


class ResultType(models.Model):
    """Модель типа результата"""
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Код'
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Название'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание'
    )

    class Meta:
        verbose_name = 'Тип результата'
        verbose_name_plural = 'Типы результатов'
        ordering = ['name']

    def __str__(self):
        return self.name

    def can_be_deleted(self):
        """Проверка, можно ли удалить тип результата"""
        # Нельзя удалить, если есть участия с этим типом результата
        if Participation.objects.filter(result_type=self).exists():
            return False
        return True

    def get_related_objects(self):
        """Получение списка связанных объектов"""
        related = {}
        participations = Participation.objects.filter(result_type=self)
        if participations.exists():
            related['Участия'] = participations.count()
        return related

# Импортируем Participation из participation app для использования в can_be_deleted
# Но так как у нас еще нет этого приложения, создадим заглушку
# В реальности это будет импорт из apps.participation.models