# apps/children/admin.py
from django.contrib import admin
from django.db import models
from .models import Child, Direction, Studio, Teacher, StudioEnrollment, ChildList, TeacherStudioAccess

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
    list_display = ('fio', 'date_of_birth', 'age', 'gender', 'created_at')
    list_filter = ('gender', 'created_at')
    search_fields = ('fio',)
    ordering = ('fio',)


from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Direction


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ['display_name']
    search_fields = ['name']

    def display_name(self, obj):
        # Принудительное отображение в UTF-8
        try:
            return mark_safe(f'<span style="font-family: Arial, sans-serif;">{obj.name}</span>')
        except:
            return obj.name

    display_name.short_description = 'Название направления'

@admin.register(Studio)
class StudioAdmin(admin.ModelAdmin):
    list_display = ('name', 'direction')
    list_filter = ('direction',)
    search_fields = ('name', 'direction__name')
    ordering = ('direction', 'name')

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'user')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')

@admin.register(StudioEnrollment)
class StudioEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('child', 'studio', 'teacher', 'academic_year', 'enrollment_date')
    list_filter = ('studio__direction', 'studio', 'teacher', 'academic_year')
    search_fields = ('child__fio', 'studio__name')
    ordering = ('-enrollment_date',)

@admin.register(ChildList)
class ChildListAdmin(admin.ModelAdmin):
    list_display = ('child',)
    search_fields = ('child__fio',)


# apps/children/admin.py (добавляем в конец)
@admin.register(TeacherStudioAccess)
class TeacherStudioAccessAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'studio', 'granted_by', 'granted_at')
    list_filter = ('studio__direction', 'studio', 'granted_at')
    search_fields = ('teacher__user__username', 'teacher__user__first_name', 'studio__name')