# apps/children/models.py
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


class Child(models.Model):
    """Модель ребенка"""
    GENDER_CHOICES = [
        ('M', 'Мужской'),
        ('F', 'Женский'),
    ]

    # Новые поля
    last_name = models.CharField(
        max_length=100,
        verbose_name='Фамилия'
    )
    first_name = models.CharField(
        max_length=100,
        verbose_name='Имя'
    )
    patronymic = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Отчество'
    )

    # Старое поле fio оставляем, но сделаем его вычисляемым при сохранении
    fio = models.CharField(
        max_length=255,
        verbose_name='ФИО'
    )
    date_of_birth = models.DateField(
        verbose_name='Дата рождения'
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        verbose_name='Пол'
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
        verbose_name = 'Ребенок'
        verbose_name_plural = 'Дети'
        ordering = ['fio']

    def save(self, *args, **kwargs):
        # Автоматически формируем ФИО из частей
        parts = [self.last_name, self.first_name]
        if self.patronymic:
            parts.append(self.patronymic)
        self.fio = ' '.join(parts)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.fio

    @property
    def age(self):
        """Вычисление возраста"""
        from datetime import date
        today = date.today()
        born = self.date_of_birth
        age = today.year - born.year
        if (today.month, today.day) < (born.month, born.day):
            age -= 1
        return age

    def can_be_deleted(self):
        """Проверка, можно ли удалить ребенка"""
        return not StudioEnrollment.objects.filter(child=self).exists()

    def get_absolute_url(self):
        return reverse('children:detail', kwargs={'pk': self.pk})


# apps/children/models.py (обновляем модель Studio)
class Studio(models.Model):
    """Модель студии"""
    name = models.CharField(
        max_length=100,
        verbose_name='Название студии'
    )
    direction = models.ForeignKey(
        'Direction',
        on_delete=models.CASCADE,
        verbose_name='Направление',
        related_name='studios_in_direction'
    )

    class Meta:
        verbose_name = 'Студия'
        verbose_name_plural = 'Студии'
        ordering = ['direction', 'name']
        unique_together = ['name', 'direction']

    def __str__(self):
        return f"{self.name} ({self.direction.name})"

    def can_be_deleted(self):
        """Проверка, можно ли удалить студию"""
        # Нельзя удалить, если есть записи детей в этой студии
        if StudioEnrollment.objects.filter(studio=self).exists():
            return False
        # Нельзя удалить, если есть доступы к этой студии
        if TeacherStudioAccess.objects.filter(studio=self).exists():
            return False
        return True

    def get_related_objects(self):
        """Получение списка связанных объектов"""
        related = {}
        enrollments = StudioEnrollment.objects.filter(studio=self)
        if enrollments.exists():
            related['Записи детей'] = enrollments.count()

        accesses = TeacherStudioAccess.objects.filter(studio=self)
        if accesses.exists():
            related['Доступы педагогов'] = accesses.count()

        return related



# apps/children/models.py (обновляем модели Teacher и Direction)

class Teacher(models.Model):
    """Модель педагога"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )

    class Meta:
        verbose_name = 'Педагог'
        verbose_name_plural = 'Педагоги'

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"

    def can_be_deleted(self):
        """Проверка, можно ли удалить педагога"""
        # Нельзя удалить, если есть записи в студиях
        if StudioEnrollment.objects.filter(teacher=self).exists():
            return False
        # Нельзя удалить, если есть доступ к студиям
        if TeacherStudioAccess.objects.filter(teacher=self).exists():
            return False
        return True

    def get_related_objects(self):
        """Получение списка связанных объектов"""
        related = {}
        enrollments = StudioEnrollment.objects.filter(teacher=self)
        if enrollments.exists():
            related['Записи в студиях'] = enrollments.count()

        accesses = TeacherStudioAccess.objects.filter(teacher=self)
        if accesses.exists():
            related['Доступы к студиям'] = accesses.count()

        return related


class Direction(models.Model):
    """Модель направления деятельности"""
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Название направления'
    )

    class Meta:
        verbose_name = 'Направление'
        verbose_name_plural = 'Направления'
        ordering = ['name']

    def __str__(self):
        return self.name

    def can_be_deleted(self):
        """Проверка, можно ли удалить направление"""
        # Нельзя удалить, если есть студии в этом направлении
        if Studio.objects.filter(direction=self).exists():
            return False
        return True

    def get_related_objects(self):
        """Получение списка связанных объектов"""
        related = {}
        studios = Studio.objects.filter(direction=self)
        if studios.exists():
            related['Студии'] = studios.count()
        return related



class StudioEnrollment(models.Model):
    """Модель записи ребенка в студию"""
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        verbose_name='Ребенок'
    )
    direction = models.ForeignKey(
        Direction,
        on_delete=models.CASCADE,
        verbose_name='Направление'
    )
    studio = models.ForeignKey(
        Studio,
        on_delete=models.CASCADE,
        verbose_name='Студия'
    )
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        verbose_name='Педагог'
    )
    academic_year = models.CharField(
        max_length=9,  # "2024-2025"
        verbose_name='Учебный год'
    )
    enrollment_date = models.DateField(
        auto_now_add=True,
        verbose_name='Дата записи'
    )

    # Поле "Дата отчисления" (может быть пустым)
    date_of_dismissal = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата отчисления'
    )


    class Meta:
        verbose_name = 'Запись в студию'
        verbose_name_plural = 'Записи в студии'
        unique_together = ['child', 'studio', 'academic_year']

    def __str__(self):
        return f"{self.child.fio} - {self.studio.name} ({self.academic_year})"

    def can_be_deleted(self):
        """Проверка, можно ли удалить запись в студию"""
        # Проверяем, участвует ли ребенок в конкурсах через эту запись
        try:
            from apps.participation.models import Participation
            if Participation.objects.filter(enrollment=self).exists():
                return False
            return True
        except:
            # Если приложение participation недоступно, разрешаем удаление
            return True

    def get_related_objects(self):
        """Получение списка связанных объектов"""
        related = {}
        try:
            from apps.participation.models import Participation
            participations = Participation.objects.filter(enrollment=self)
            if participations.exists():
                related['Участия в конкурсах'] = participations.count()
        except:
            pass
        return related


class ChildList(models.Model):
    """Общий список детей (справочник)"""
    child = models.OneToOneField(
        Child,
        on_delete=models.CASCADE,
        verbose_name='Ребенок'
    )

    class Meta:
        verbose_name = 'Запись в общем списке'
        verbose_name_plural = 'Общий список детей'

    def __str__(self):
        return f"Общий список: {self.child.fio}"


# apps/children/models.py (добавляем в конец)
class TeacherStudioAccess(models.Model):
    """Модель доступа педагога к студиям"""
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.CASCADE,
        verbose_name='Педагог'
    )
    studio = models.ForeignKey(
        Studio,
        on_delete=models.CASCADE,
        verbose_name='Студия'
    )
    granted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Кем предоставлен доступ'
    )
    granted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата предоставления доступа'
    )

    class Meta:
        verbose_name = 'Доступ педагога к студии'
        verbose_name_plural = 'Доступы педагогов к студиям'
        unique_together = ['teacher', 'studio']

    def __str__(self):
        return f"{self.teacher} - {self.studio}"