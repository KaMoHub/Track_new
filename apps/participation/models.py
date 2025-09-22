# apps/participation/models.py
# apps/participation/models.py
from django.db import models
from django.urls import reverse
from django.conf import settings
from ..children.models import Child, StudioEnrollment
import os


class Participation(models.Model):
    """Модель участия ребенка в конкурсе"""
    child = models.ForeignKey(
        Child,
        on_delete=models.CASCADE,
        verbose_name='Ребенок'
    )
    enrollment = models.ForeignKey(
        StudioEnrollment,
        on_delete=models.CASCADE,
        verbose_name='Запись в студию'
    )
    event = models.ForeignKey(
        'events.Event',  # Строковая ссылка
        on_delete=models.CASCADE,
        verbose_name='Конкурс'
    )
    result_type = models.ForeignKey(
        'events.ResultType',  # Строковая ссылка
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Тип результата'
    )
    custom_result = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Результат (произвольный)'
    )
    report_date = models.DateField(
        verbose_name='Дата отчета'
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
        verbose_name = 'Участие'
        verbose_name_plural = 'Участия'
        unique_together = ['child', 'event']
        ordering = ['-report_date', 'child__fio']

    def __str__(self):
        return f"{self.child.fio} - {self.event.name}"

    @property
    def child_representation(self):
        """Представление ребенка для отображения"""
        return f"{self.child.fio} ({self.enrollment.studio.name})"

    def get_result_display(self):
        """Отображение результата"""
        if self.result_type:
            return self.result_type.name
        return self.custom_result or "Без результата"

    def get_absolute_url(self):
        return reverse('participation:detail', kwargs={'pk': self.pk})

    def can_be_deleted(self):
        """Проверка, можно ли удалить участие"""
        return True

    def get_related_objects(self):
        """Получение списка связанных объектов"""
        related = {}
        return related


# apps/participation/models.py (обновляем UploadedFile)
class UploadedFile(models.Model):
    """Модель загруженного файла"""
    participation = models.ForeignKey(
        'Participation',  # Строковая ссылка на ту же модель в этом приложении
        on_delete=models.CASCADE,
        verbose_name='Участие'
    )
    original_name = models.CharField(
        max_length=255,
        verbose_name='Оригинальное имя файла'
    )
    stored_name = models.CharField(
        max_length=255,
        verbose_name='Имя файла в системе'
    )
    file_path = models.CharField(
        max_length=500,
        verbose_name='Путь к файлу'
    )
    file_size = models.BigIntegerField(
        verbose_name='Размер файла (байт)'
    )
    mime_type = models.CharField(
        max_length=100,
        verbose_name='MIME-тип'
    )
    upload_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата загрузки'
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Загрузил'
    )

    class Meta:
        verbose_name = 'Загруженный файл'
        verbose_name_plural = 'Загруженные файлы'
        ordering = ['-upload_date']

    def __str__(self):
        return self.original_name

    def get_file_extension(self):
        """Получение расширения файла"""
        return os.path.splitext(self.original_name)[1].lower()

    def is_image(self):
        """Проверка, является ли файл изображением"""
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
        return self.get_file_extension() in image_extensions

    def is_pdf(self):
        """Проверка, является ли файл PDF"""
        return self.get_file_extension() == '.pdf'

    def get_absolute_url(self):
        """URL для скачивания файла"""
        return reverse('participation:download_file', kwargs={'pk': self.pk})

    def get_view_url(self):
        """URL для просмотра файла в браузере"""
        return reverse('participation:view_file', kwargs={'pk': self.pk})