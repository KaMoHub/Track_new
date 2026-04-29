# apps/participation/views/base_views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from ..models import Participation, UploadedFile
from ...children.models import Teacher, StudioEnrollment, Child, Studio
from ...events.models import Event, ResultType


class BaseParticipationView(LoginRequiredMixin):
    """Базовый класс для views участий"""
    model = Participation

    def check_user_access(self, user, participation):
        """Проверка прав доступа пользователя"""
        if hasattr(user, 'role'):
            if user.role in ['methodist', 'admin']:
                return True
            elif user.role == 'teacher':
                try:
                    teacher = Teacher.objects.get(user=user)
                    return participation.enrollment.teacher == teacher
                except Teacher.DoesNotExist:
                    return False
                except Exception:
                    return False
            else:
                return False
        return False

    def get_accessible_enrollments(self, user):
        """Получение доступных записей в студии для пользователя"""
        if hasattr(user, 'role'):
            if user.role == 'teacher':
                try:
                    teacher = Teacher.objects.get(user=user)
                    # Получаем ID студий, к которым у педагога есть доступ
                    from ...children.models import TeacherStudioAccess
                    accessible_studio_ids = TeacherStudioAccess.objects.filter(
                        teacher=teacher
                    ).values_list('studio_id', flat=True)
                    # Возвращаем все записи в этих студиях
                    return StudioEnrollment.objects.filter(
                        studio_id__in=accessible_studio_ids
                    ).select_related('child', 'studio').order_by('child__fio')
                except Teacher.DoesNotExist:
                    return StudioEnrollment.objects.none()
                except Exception:
                    return StudioEnrollment.objects.none()
            elif user.role in ['methodist', 'admin']:
                return StudioEnrollment.objects.select_related(
                    'child', 'studio'
                ).order_by('child__fio')
        return StudioEnrollment.objects.none()


class BaseFileView(LoginRequiredMixin):
    """Базовый класс для views файлов"""
    model = UploadedFile

    def check_file_access(self, user, uploaded_file):
        """Проверка прав доступа к файлу"""
        if hasattr(user, 'role'):
            if user.role in ['methodist', 'admin']:
                return True
            elif user.role == 'teacher':
                # Для педагогов разрешаем просмотр всех файлов
                # (редактирование и удаление контролируется в других местах)
                try:
                    teacher = Teacher.objects.get(user=user)
                    return True  # Педагоги могут просматривать все файлы
                except Teacher.DoesNotExist:
                    return False
                except Exception:
                    return False
        return False

    def check_file_edit_access(self, user, uploaded_file):
        """Проверка прав доступа к редактированию файла"""
        if hasattr(user, 'role'):
            if user.role in ['methodist', 'admin']:
                return True
            elif user.role == 'teacher':
                try:
                    teacher = Teacher.objects.get(user=user)
                    # Педагоги могут редактировать только свои файлы
                    return uploaded_file.participation.enrollment.teacher == teacher
                except Teacher.DoesNotExist:
                    return False
                except Exception:
                    return False
        return False