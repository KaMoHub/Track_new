# apps/participation/views.py (обновленный файл)
from .views import *

# # apps/participation/views.py
# from django.shortcuts import render, get_object_or_404
# from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
# from django.contrib.auth.mixins import LoginRequiredMixin
# from django.urls import reverse_lazy, reverse
# from django.contrib import messages
# from django.db.models import Q
# from django.http import HttpResponseRedirect, Http404, FileResponse
# from django.utils import timezone
# from django.contrib.auth.decorators import login_required
# from django.utils.decorators import method_decorator
# from django.db import transaction, IntegrityError
# from django.core.files.storage import default_storage
# from django.core.files.base import ContentFile
# import os
#
# # Импортируем модели напрямую
# from .models import Participation, UploadedFile
# from ..children.models import Child, Studio, StudioEnrollment, Teacher
# from ..events.models import Event, ResultType
#
#
# class ParticipationListView(LoginRequiredMixin, ListView):
#     """Список участий"""
#     model = Participation
#     template_name = 'participation/participation_list.html'
#     context_object_name = 'participations'
#     paginate_by = 20
#
#     def get_queryset(self):
#         user = self.request.user
#         queryset = Participation.objects.select_related(
#             'child', 'event', 'result_type', 'enrollment__studio', 'enrollment__teacher'
#         ).order_by('-report_date', 'child__fio')
#
#         # Фильтрация по доступу в зависимости от роли пользователя
#         if hasattr(user, 'role'):
#             if user.role == 'teacher':
#                 # Для педагогов - только их ученики
#                 try:
#                     teacher = Teacher.objects.get(user=user)
#                     # Получаем записи детей, записанных к этому педагогу
#                     accessible_enrollments = StudioEnrollment.objects.filter(
#                         teacher=teacher
#                     ).values_list('id', flat=True)
#                     queryset = queryset.filter(enrollment_id__in=accessible_enrollments)
#                 except Teacher.DoesNotExist:
#                     queryset = queryset.none()
#                 except Exception:
#                     queryset = queryset.none()
#             elif user.role in ['methodist', 'admin']:
#                 # Для методистов и админов - все участия
#                 pass
#             else:
#                 # Для других ролей - пустой список
#                 queryset = queryset.none()
#         else:
#             # Для пользователей без роли - пустой список
#             queryset = queryset.none()
#
#         # Фильтры
#         child_id = self.request.GET.get('child')
#         event_id = self.request.GET.get('event')
#         result_type_id = self.request.GET.get('result_type')
#         search = self.request.GET.get('search')
#
#         if child_id:
#             queryset = queryset.filter(child_id=child_id)
#         if event_id:
#             queryset = queryset.filter(event_id=event_id)
#         if result_type_id:
#             queryset = queryset.filter(result_type_id=result_type_id)
#         if search:
#             queryset = queryset.filter(
#                 Q(child__fio__icontains=search) |
#                 Q(event__name__icontains=search) |
#                 Q(custom_result__icontains=search) |
#                 Q(enrollment__studio__name__icontains=search)
#             )
#
#         return queryset
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         user = self.request.user
#
#         # Для фильтров - только доступные данные
#         if hasattr(user, 'role'):
#             if user.role == 'teacher':
#                 try:
#                     teacher = Teacher.objects.get(user=user)
#                     # Только дети этого педагога
#                     context['children'] = Child.objects.filter(
#                         studioenrollment__teacher=teacher
#                     ).distinct().order_by('fio')
#                     # Только студии этого педагога
#                     context['studios'] = Studio.objects.filter(
#                         studioenrollment__teacher=teacher
#                     ).distinct().order_by('name')
#                     # Только конкурсы этого педагога
#                     context['events'] = Event.objects.filter(
#                         participation__enrollment__teacher=teacher
#                     ).distinct().filter(is_active=True).order_by('name')
#                 except (Teacher.DoesNotExist, Exception):
#                     context['children'] = Child.objects.none()
#                     context['studios'] = Studio.objects.none()
#                     context['events'] = Event.objects.none()
#             elif user.role in ['methodist', 'admin']:
#                 # Для методистов и админов - все данные
#                 context['children'] = Child.objects.all().order_by('fio')
#                 context['studios'] = Studio.objects.all().order_by('name')
#                 context['events'] = Event.objects.filter(is_active=True).order_by('name')
#             else:
#                 context['children'] = Child.objects.none()
#                 context['studios'] = Studio.objects.none()
#                 context['events'] = Event.objects.none()
#         else:
#             context['children'] = Child.objects.none()
#             context['studios'] = Studio.objects.none()
#             context['events'] = Event.objects.none()
#
#         context['result_types'] = ResultType.objects.all().order_by('name')
#
#         # Текущие значения фильтров
#         context['current_child'] = self.request.GET.get('child', '')
#         context['current_event'] = self.request.GET.get('event', '')
#         context['current_result_type'] = self.request.GET.get('result_type', '')
#         context['current_search'] = self.request.GET.get('search', '')
#
#         return context
#
#
# class ParticipationDetailView(LoginRequiredMixin, DetailView):
#     """Детали участия"""
#     model = Participation
#     template_name = 'participation/participation_detail.html'
#     context_object_name = 'participation'
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#
#         # Проверяем, имеет ли пользователь доступ к редактированию
#         user = self.request.user
#         participation = self.object
#
#         can_edit = False
#         if hasattr(user, 'role'):
#             if user.role in ['methodist', 'admin']:
#                 # Методисты и админы могут редактировать всё
#                 can_edit = True
#             elif user.role == 'teacher':
#                 # Педагоги могут редактировать только свои записи
#                 try:
#                     teacher = Teacher.objects.get(user=user)
#                     if participation.enrollment.teacher == teacher:
#                         can_edit = True
#                 except Teacher.DoesNotExist:
#                     can_edit = False
#                 except Exception:
#                     can_edit = False
#             else:
#                 can_edit = False
#         else:
#             can_edit = False
#
#         context['can_edit_participation'] = can_edit
#
#         # Получаем прикрепленные файлы
#         files = UploadedFile.objects.filter(participation=participation).order_by('-upload_date')
#         context['files'] = files
#
#         return context
#
#
# class ParticipationCreateView(LoginRequiredMixin, CreateView):
#     """Создание участия"""
#     model = Participation
#     template_name = 'participation/participation_form.html'
#     fields = ['enrollment', 'event', 'result_type', 'custom_result', 'report_date']
#     success_url = reverse_lazy('participation:list')
#
#     def get_form(self, form_class=None):
#         form = super().get_form(form_class)
#         user = self.request.user
#
#         # Фильтруем доступные записи в студии в зависимости от роли пользователя
#         if hasattr(user, 'role'):
#             if user.role == 'teacher':
#                 try:
#                     teacher = Teacher.objects.get(user=user)
#                     # Только доступные записи для педагога
#                     accessible_enrollments = StudioEnrollment.objects.filter(
#                         teacher=teacher
#                     ).select_related('child', 'studio').order_by('child__fio')
#                     form.fields['enrollment'].queryset = accessible_enrollments
#                 except Teacher.DoesNotExist:
#                     form.fields['enrollment'].queryset = StudioEnrollment.objects.none()
#                 except Exception:
#                     form.fields['enrollment'].queryset = StudioEnrollment.objects.none()
#             elif user.role in ['methodist', 'admin']:
#                 # Для методистов и админов все записи
#                 form.fields['enrollment'].queryset = StudioEnrollment.objects.select_related(
#                     'child', 'studio'
#                 ).order_by('child__fio')
#             else:
#                 form.fields['enrollment'].queryset = StudioEnrollment.objects.none()
#         else:
#             form.fields['enrollment'].queryset = StudioEnrollment.objects.none()
#
#         # Только активные конкурсы
#         form.fields['event'].queryset = Event.objects.filter(is_active=True).order_by('name')
#         # Все типы результатов
#         form.fields['result_type'].queryset = ResultType.objects.all().order_by('name')
#
#         # Устанавливаем текущую дату по умолчанию
#         if not form.initial.get('report_date'):
#             from datetime import date
#             form.initial['report_date'] = date.today()
#
#         return form
#
#     def form_valid(self, form):
#         form.instance.created_by = self.request.user
#         enrollment = form.cleaned_data['enrollment']
#         form.instance.child = enrollment.child
#
#         # Проверяем, не существует ли уже такое участие (до сохранения)
#         child = form.instance.child
#         event = form.cleaned_data['event']
#
#         # Используем транзакцию для обеспечения целостности данных
#         try:
#             with transaction.atomic():
#                 # Проверяем существование участия
#                 if Participation.objects.filter(child=child, event=event).exists():
#                     messages.error(
#                         self.request,
#                         f'Ребенок {child.fio} уже участвует в конкурсе "{event.name}"'
#                     )
#                     return self.form_invalid(form)
#
#                 # Сохраняем участие
#                 response = super().form_valid(form)
#
#                 # Обрабатываем загрузку файла, если она есть
#                 file_upload = self.request.FILES.get('file_upload')
#                 if file_upload:
#                     try:
#                         self.handle_file_upload(file_upload)
#                     except Exception as e:
#                         messages.warning(
#                             self.request,
#                             f'Файл не был загружен из-за ошибки: {str(e)}'
#                         )
#
#                 messages.success(self.request, 'Участие успешно зарегистрировано.')
#                 return response
#
#         except IntegrityError:
#             # Если произошла ошибка целостности (дубликат), показываем сообщение
#             messages.error(
#                 self.request,
#                 f'Ребенок {child.fio} уже участвует в конкурсе "{event.name}"'
#             )
#             return self.form_invalid(form)
#
#     # apps/participation/views.py (обновляем handle_file_upload в ParticipationCreateView)
#     def handle_file_upload(self, file_upload):
#         """Обработка загрузки файла"""
#         print(f"DEBUG: Начало загрузки файла: {file_upload.name}")
#
#         # Создаем запись файла
#         uploaded_file = UploadedFile(
#             participation=self.object,
#             original_name=file_upload.name,
#             file_size=file_upload.size,
#             mime_type=file_upload.content_type,
#             uploaded_by=self.request.user
#         )
#
#         # Генерируем уникальное имя файла
#         import uuid
#         file_extension = os.path.splitext(file_upload.name)[1].lower()
#         stored_name = f"{uuid.uuid4()}{file_extension}"
#         uploaded_file.stored_name = stored_name
#         print(f"DEBUG: Уникальное имя файла: {stored_name}")
#
#         # Определяем путь для сохранения файла
#         # Используем стандартную директорию Django media
#         from django.conf import settings
#         if hasattr(settings, 'MEDIA_ROOT'):
#             upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'participation_files')
#         else:
#             upload_dir = os.path.join('media', 'uploads', 'participation_files')
#
#         # Создаем директорию, если она не существует
#         os.makedirs(upload_dir, exist_ok=True)
#         print(f"DEBUG: Директория для загрузки: {upload_dir}")
#
#         # Полный путь к файлу
#         file_path = os.path.join(upload_dir, stored_name)
#         uploaded_file.file_path = file_path
#         print(f"DEBUG: Полный путь к файлу: {file_path}")
#
#         try:
#             # Сохраняем файл в файловой системе
#             with open(file_path, 'wb+') as destination:
#                 for chunk in file_upload.chunks():
#                     destination.write(chunk)
#             print(f"DEBUG: Файл успешно сохранен")
#
#             # Сохраняем запись о файле в БД
#             uploaded_file.save()
#             print(f"DEBUG: Запись о файле сохранена в БД, ID={uploaded_file.id}")
#
#         except Exception as e:
#             print(f"DEBUG: Ошибка при сохранении файла: {e}")
#             raise e
#
#     def form_invalid(self, form):
#         messages.error(
#             self.request,
#             'Пожалуйста, исправьте ошибки в форме.'
#         )
#         return super().form_invalid(form)
#
#
# class ParticipationUpdateView(LoginRequiredMixin, UpdateView):
#     """Редактирование участия"""
#     model = Participation
#     template_name = 'participation/participation_form.html'
#     fields = ['enrollment', 'event', 'result_type', 'custom_result', 'report_date']
#     success_url = reverse_lazy('participation:list')
#
#     def dispatch(self, request, *args, **kwargs):
#         """Проверка прав доступа перед выполнением действия"""
#         # Проверяем доступ перед выполнением действия
#         user = request.user
#         participation = self.get_object()
#
#         has_access = False
#         if hasattr(user, 'role'):
#             if user.role in ['methodist', 'admin']:
#                 # Методисты и админы могут редактировать всё
#                 has_access = True
#             elif user.role == 'teacher':
#                 # Педагоги могут редактировать только свои записи
#                 try:
#                     teacher = Teacher.objects.get(user=user)
#                     if participation.enrollment.teacher == teacher:
#                         has_access = True
#                 except Teacher.DoesNotExist:
#                     has_access = False
#                 except Exception:
#                     has_access = False
#             else:
#                 has_access = False
#         else:
#             has_access = False
#
#         if not has_access:
#             messages.error(request, 'У вас нет прав для редактирования этого участия.')
#             return HttpResponseRedirect(reverse_lazy('participation:detail', kwargs={'pk': participation.pk}))
#
#         return super().dispatch(request, *args, **kwargs)
#
#     def get_form(self, form_class=None):
#         form = super().get_form(form_class)
#         user = self.request.user
#         instance = self.get_object()
#
#         # Фильтруем доступные записи в студии в зависимости от роли пользователя
#         if hasattr(user, 'role'):
#             if user.role == 'teacher':
#                 try:
#                     teacher = Teacher.objects.get(user=user)
#                     # Получаем записи детей, записанных к этому педагогу
#                     accessible_enrollments = StudioEnrollment.objects.filter(
#                         teacher=teacher
#                     ).select_related('child', 'studio').order_by('child__fio')
#                     form.fields['enrollment'].queryset = accessible_enrollments
#
#                     # Если текущая запись не в списке доступных, добавляем её
#                     if instance.enrollment and instance.enrollment not in accessible_enrollments:
#                         form.fields['enrollment'].queryset = accessible_enrollments | StudioEnrollment.objects.filter(
#                             id=instance.enrollment.id
#                         ).select_related('child', 'studio')
#
#                 except Teacher.DoesNotExist:
#                     form.fields['enrollment'].queryset = StudioEnrollment.objects.none()
#                 except Exception as e:
#                     print(f"DEBUG: Ошибка при фильтрации enrollment: {e}")
#                     form.fields['enrollment'].queryset = StudioEnrollment.objects.none()
#             elif user.role in ['methodist', 'admin']:
#                 # Для методистов и админов все записи
#                 form.fields['enrollment'].queryset = StudioEnrollment.objects.select_related(
#                     'child', 'studio'
#                 ).order_by('child__fio')
#             else:
#                 form.fields['enrollment'].queryset = StudioEnrollment.objects.none()
#         else:
#             form.fields['enrollment'].queryset = StudioEnrollment.objects.select_related(
#                 'child', 'studio'
#             ).order_by('child__fio')
#
#         # Только активные конкурсы
#         form.fields['event'].queryset = Event.objects.filter(is_active=True).order_by('name')
#         # Все типы результатов
#         form.fields['result_type'].queryset = ResultType.objects.all().order_by('name')
#
#         return form
#
#     def form_valid(self, form):
#         enrollment = form.cleaned_data['enrollment']
#         form.instance.child = enrollment.child
#
#         # Проверяем, не создаст ли это дубликат
#         child = form.instance.child
#         event = form.cleaned_data['event']
#         current_object = self.get_object()
#
#         if Participation.objects.filter(
#                 child=child, event=event
#         ).exclude(pk=current_object.pk).exists():
#             messages.error(
#                 self.request,
#                 f'Ребенок {child.fio} уже участвует в конкурсе "{event.name}"'
#             )
#             return self.form_invalid(form)
#
#         # Сохраняем участие
#         response = super().form_valid(form)
#
#         # Обрабатываем загрузку файла, если она есть
#         file_upload = self.request.FILES.get('file_upload')
#         if file_upload:
#             try:
#                 self.handle_file_upload(file_upload)
#                 messages.success(
#                     self.request,
#                     f'Файл "{file_upload.name}" успешно загружен.'
#                 )
#             except Exception as e:
#                 messages.warning(
#                     self.request,
#                     f'Файл не был загружен из-за ошибки: {str(e)}'
#                 )
#
#         messages.success(self.request, 'Участие успешно обновлено.')
#         return response
#
#     def handle_file_upload(self, file_upload):
#         """Обработка загрузки файла"""
#         # Создаем запись файла
#         uploaded_file = UploadedFile(
#             participation=self.object,
#             original_name=file_upload.name,
#             file_size=file_upload.size,
#             mime_type=file_upload.content_type,
#             uploaded_by=self.request.user
#         )
#
#         # Генерируем уникальное имя файла
#         import uuid
#         file_extension = os.path.splitext(file_upload.name)[1].lower()
#         stored_name = f"{uuid.uuid4()}{file_extension}"
#         uploaded_file.stored_name = stored_name
#
#         # Сохраняем файл в файловой системе
#         file_path = os.path.join('uploads', 'participation_files', stored_name)
#         path = default_storage.save(file_path, ContentFile(file_upload.read()))
#         uploaded_file.file_path = path
#
#         # Сохраняем запись о файле
#         uploaded_file.save()
#
#     def form_invalid(self, form):
#         messages.error(
#             self.request,
#             'Пожалуйста, исправьте ошибки в форме.'
#         )
#         return super().form_valid(form)
#
#
# class ParticipationDeleteView(LoginRequiredMixin, DeleteView):
#     """Удаление участия"""
#     model = Participation
#     template_name = 'participation/participation_confirm_delete.html'
#     success_url = reverse_lazy('participation:list')
#
#     def dispatch(self, request, *args, **kwargs):
#         # Проверяем доступ перед выполнением действия
#         user = request.user
#         participation = self.get_object()
#
#         has_access = False
#         if hasattr(user, 'role'):
#             if user.role in ['methodist', 'admin']:
#                 # Методисты и админы могут удалять всё
#                 has_access = True
#             elif user.role == 'teacher':
#                 # Педагоги могут удалять только свои записи
#                 try:
#                     teacher = Teacher.objects.get(user=user)
#                     if participation.enrollment.teacher == teacher:
#                         has_access = True
#                 except:
#                     has_access = False
#             else:
#                 has_access = False
#         else:
#             has_access = False
#
#         if not has_access:
#             messages.error(request, 'У вас нет прав для удаления этого участия.')
#             return HttpResponseRedirect(reverse_lazy('participation:detail', kwargs={'pk': participation.pk}))
#
#         return super().dispatch(request, *args, **kwargs)
#
#     def delete(self, request, *args, **kwargs):
#         messages.success(
#             request,
#             f'Участие ребенка {self.get_object().child.fio} в конкурсе "{self.get_object().event.name}" успешно удалено.'
#         )
#         return super().delete(request, *args, **kwargs)
#
#
# # Views для загруженных файлов
# class UploadedFileListView(LoginRequiredMixin, ListView):
#     """Список загруженных файлов"""
#     model = UploadedFile
#     template_name = 'participation/file_list.html'
#     context_object_name = 'files'
#     paginate_by = 20
#
#
# class UploadedFileDetailView(LoginRequiredMixin, DetailView):
#     """Детали загруженного файла"""
#     model = UploadedFile
#     template_name = 'participation/file_detail.html'
#     context_object_name = 'file'
#
#
# class UploadedFileCreateView(LoginRequiredMixin, CreateView):
#     """Загрузка файла"""
#     model = UploadedFile
#     template_name = 'participation/file_form.html'
#     fields = ['participation', 'original_name', 'file_path', 'file_size', 'mime_type']
#
#     def get_form(self, form_class=None):
#         form = super().get_form(form_class)
#         participation_id = self.request.GET.get('participation')
#
#         if participation_id:
#             try:
#                 participation = Participation.objects.get(id=participation_id)
#                 form.fields['participation'].initial = participation
#             except Participation.DoesNotExist:
#                 pass
#
#         return form
#
#     def form_valid(self, form):
#         form.instance.uploaded_by = self.request.user
#
#         # Обработка загруженного файла
#         file_upload = self.request.FILES.get('file_upload')
#         if file_upload:
#             form.instance.original_name = file_upload.name
#             form.instance.file_size = file_upload.size
#             form.instance.mime_type = file_upload.content_type
#
#             # Сохраняем файл
#             import uuid
#             file_extension = os.path.splitext(file_upload.name)[1].lower()
#             stored_name = f"{uuid.uuid4()}{file_extension}"
#             form.instance.stored_name = stored_name
#
#             file_path = os.path.join('uploads', 'participation_files', stored_name)
#             path = default_storage.save(file_path, ContentFile(file_upload.read()))
#             form.instance.file_path = path
#
#         messages.success(self.request, 'Файл успешно загружен.')
#         return super().form_valid(form)
#
#     def get_success_url(self):
#         participation_id = self.request.GET.get('participation')
#         if participation_id:
#             return reverse_lazy('participation:detail', kwargs={'pk': participation_id})
#         return reverse_lazy('participation:list')
#
#
# class UploadedFileUpdateView(LoginRequiredMixin, UpdateView):
#     """Редактирование файла"""
#     model = UploadedFile
#     template_name = 'participation/file_form.html'
#     fields = ['participation', 'original_name', 'file_path', 'file_size', 'mime_type']
#     success_url = reverse_lazy('participation:file_list')
#
#     def form_valid(self, form):
#         messages.success(self.request, 'Файл успешно обновлен.')
#         return super().form_valid(form)
#
#
# class UploadedFileDeleteView(LoginRequiredMixin, DeleteView):
#     """Удаление файла"""
#     model = UploadedFile
#     template_name = 'participation/file_confirm_delete.html'
#     success_url = reverse_lazy('participation:file_list')
#
#     def delete(self, request, *args, **kwargs):
#         messages.success(request, f'Файл {self.get_object().original_name} успешно удален.')
#         return super().delete(request, *args, **kwargs)
#
#
# # Функции для работы с файлами
# # apps/participation/views.py (исправляем функции для файлов)
# @login_required
# def download_file(request, pk):
#     """Скачивание файла"""
#     uploaded_file = get_object_or_404(UploadedFile, pk=pk)
#
#     # Проверяем права доступа
#     user = request.user
#     has_access = False
#
#     if hasattr(user, 'role'):
#         if user.role in ['methodist', 'admin']:
#             has_access = True
#         elif user.role == 'teacher':
#             try:
#                 teacher = Teacher.objects.get(user=user)
#                 if uploaded_file.participation.enrollment.teacher == teacher:
#                     has_access = True
#             except:
#                 pass
#     else:
#         has_access = False
#
#     if not has_access:
#         raise Http404("Файл не найден")
#     print(uploaded_file.file_path)
#     # Открываем файл и отправляем его
#     file_path = uploaded_file.file_path
#     if os.path.exists(file_path):
#         response = FileResponse(
#             open(file_path, 'rb'),
#             content_type=uploaded_file.mime_type
#         )
#         response['Content-Disposition'] = f'attachment; filename="{uploaded_file.original_name}"'
#         return response
#     else:
#         raise Http404("Файл не найден")
#
#
# # apps/participation/views.py (обновляем view_file)
# @login_required
# def view_file(request, pk):
#     """Просмотр файла в браузере"""
#     print(f"DEBUG: Попытка просмотра файла с ID={pk}")
#
#     # Проверяем, существует ли файл в базе данных
#     try:
#         uploaded_file = UploadedFile.objects.get(pk=pk)
#         print(f"DEBUG: Файл найден в БД: {uploaded_file.original_name}")
#     except UploadedFile.DoesNotExist:
#         print(f"DEBUG: Файл с ID={pk} не найден в БД")
#         raise Http404("Файл не найден в базе данных")
#     except Exception as e:
#         print(f"DEBUG: Ошибка при поиске файла в БД: {e}")
#         raise Http404("Ошибка при поиске файла")
#
#     # Проверяем права доступа
#     user = request.user
#     print(f"DEBUG: Пользователь: {user.username}, роль: {getattr(user, 'role', 'нет роли')}")
#
#     has_access = False
#     if hasattr(user, 'role'):
#         if user.role in ['methodist', 'admin']:
#             has_access = True
#             print(f"DEBUG: Пользователь {user.username} имеет полный доступ (methodist/admin)")
#         elif user.role == 'teacher':
#             try:
#                 teacher = Teacher.objects.get(user=user)
#                 if uploaded_file.participation.enrollment.teacher == teacher:
#                     has_access = True
#                     print(f"DEBUG: Пользователь {user.username} - владелец файла")
#                 else:
#                     print(f"DEBUG: Пользователь {user.username} НЕ владелец файла")
#                     print(f"DEBUG: Владелец файла: {uploaded_file.participation.enrollment.teacher}")
#                     print(f"DEBUG: Текущий пользователь: {teacher}")
#             except Teacher.DoesNotExist:
#                 print(f"DEBUG: Пользователь {user.username} не найден как учитель")
#             except Exception as e:
#                 print(f"DEBUG: Ошибка при проверке прав учителя: {e}")
#         else:
#             print(f"DEBUG: У пользователя {user.username} неизвестная роль: {user.role}")
#     else:
#         print(f"DEBUG: У пользователя {user.username} нет роли")
#
#     if not has_access:
#         print(f"DEBUG: Доступ запрещен для пользователя {user.username}")
#         raise Http404("У вас нет прав для просмотра этого файла")
#
#     # Проверяем существование файла в файловой системе
#     file_path = uploaded_file.file_path
#     print(f"DEBUG: Путь к файлу в БД: {file_path}")
#     print(f"DEBUG: Абсолютный путь: {os.path.abspath(file_path)}")
#     print(f"DEBUG: Существует ли файл: {os.path.exists(file_path)}")
#
#     if os.path.exists(file_path):
#         print(f"DEBUG: Файл существует, пробуем открыть")
#         try:
#             # Открываем файл и отправляем его
#             file_handle = open(file_path, 'rb')
#             response = FileResponse(
#                 file_handle,
#                 content_type=uploaded_file.mime_type
#             )
#             response['Content-Disposition'] = f'inline; filename="{uploaded_file.original_name}"'
#             print(f"DEBUG: Файл успешно отправлен для просмотра")
#             return response
#         except Exception as e:
#             print(f"DEBUG: Ошибка при открытии файла: {e}")
#             raise Http404(f"Ошибка при открытии файла: {e}")
#     else:
#         print(f"DEBUG: Файл НЕ существует по указанному пути")
#         # Попробуем найти файл в стандартной директории
#         standard_path = os.path.join('media', 'uploads', 'participation_files', uploaded_file.stored_name)
#         print(f"DEBUG: Пробуем стандартный путь: {standard_path}")
#         if os.path.exists(standard_path):
#             print(f"DEBUG: Файл найден по стандартному пути")
#             try:
#                 file_handle = open(standard_path, 'rb')
#                 response = FileResponse(
#                     file_handle,
#                     content_type=uploaded_file.mime_type
#                 )
#                 response['Content-Disposition'] = f'inline; filename="{uploaded_file.original_name}"'
#                 return response
#             except Exception as e:
#                 print(f"DEBUG: Ошибка при открытии файла по стандартному пути: {e}")
#                 raise Http404(f"Ошибка при открытии файла: {e}")
#         else:
#             print(f"DEBUG: Файл НЕ найден и по стандартному пути")
#             raise Http404("Файл не найден на сервере. Возможно, он был удален.")