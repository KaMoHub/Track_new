# apps/participation/admin.py
from django.contrib import admin
from .models import Participation, UploadedFile

@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ('child', 'event', 'get_result_display', 'report_date', 'created_by')
    list_filter = ('event__level', 'report_date', 'result_type', 'created_by')
    search_fields = ('child__fio', 'event__name', 'custom_result')
    ordering = ('-report_date', 'child__fio')

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'participation', 'upload_date', 'uploaded_by')
    list_filter = ('upload_date', 'uploaded_by')
    search_fields = ('original_name', 'participation__child__fio')