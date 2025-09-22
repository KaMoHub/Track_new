# apps/events/admin.py
from django.contrib import admin
from .models import Event, ResultType

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'level', 'application_deadline', 'result_date', 'is_active')
    list_filter = ('level', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('name',)
    list_editable = ('is_active',)

@admin.register(ResultType)
class ResultTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')
