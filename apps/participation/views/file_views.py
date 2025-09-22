# apps/participation/views/file_views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponseRedirect, Http404, FileResponse
from django.conf import settings
from .base_views import BaseFileView
from ..models import UploadedFile, Participation
from ...children.models import Teacher, StudioEnrollment, Child, Studio
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
import os

class UploadedFileListView(BaseFileView, ListView):
    """Список загруженных файлов"""
    template_name = 'participation/file_list.html'
    context_object_name = 'files'
    paginate_by = 20

class UploadedFileDetailView(BaseFileView, DetailView):
    """Детали загруженного файла"""
    template_name = 'participation/file_detail.html'
    context_object_name = 'file'


# apps/participation/views/file_views.py (обновляем UploadedFileCreateView)
# apps/participation/views/file_views.py (обновляем UploadedFileCreateView)
# apps/participation/views/file_views.py (обновляем UploadedFileCreateView - простой вариант)
# apps/participation/views/file_views.py (обновляем UploadedFileCreateView)
# apps/participation/views/file_views.py (обновляем UploadedFileCreateView)
# apps/participation/views/file_views.py (исправляем form_valid)
class UploadedFileCreateView(LoginRequiredMixin, CreateView):
    """Загрузка файла"""
    template_name = 'participation/file_form.html'
    model = UploadedFile

    def get_form_class(self):
        # Создаем динамическую форму без обязательных полей
        from django import forms

        class UploadedFileForm(forms.ModelForm):
            # Добавляем поле для загрузки файла
            file_upload = forms.FileField(
                label='Файл *',
                required=True,
                widget=forms.FileInput(attrs={
                    'accept': '.pdf,.jpg,.jpeg,.png,.gif,.bmp,.webp,.doc,.docx,.xls,.xlsx',
                    'class': 'form-control'
                })
            )

            class Meta:
                model = UploadedFile
                fields = ['participation']  # Только участие, остальное заполняем автоматически
                widgets = {
                    'participation': forms.HiddenInput(),
                }

        return UploadedFileForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        participation_id = self.request.GET.get('participation')

        if participation_id:
            try:
                participation = Participation.objects.get(id=participation_id)
                # Передаем информацию об участии в контекст для отображения
                context['participation_info'] = {
                    'child_fio': participation.child.fio,
                    'event_name': participation.event.name,
                    'participation_id': participation.id
                }
                context['participation'] = participation
            except Participation.DoesNotExist:
                context['participation_info'] = None
                context['participation'] = None
        else:
            context['participation_info'] = None
            context['participation'] = None

        return context

    def form_valid(self, form):
        print(f"DEBUG: Начало form_valid")

        # Получаем участие
        participation_id = self.request.GET.get('participation')
        print(f"DEBUG: participation_id из form_valid: {participation_id}")

        if not participation_id:
            messages.error(self.request, 'Не указано участие.')
            return self.form_invalid(form)

        try:
            participation = Participation.objects.get(id=participation_id)
            print(f"DEBUG: Найдено участие: {participation}")
        except Participation.DoesNotExist:
            messages.error(self.request, 'Участие не найдено.')
            return self.form_invalid(form)

        # Обработка загруженного файла
        file_upload = self.request.FILES.get('file_upload')
        print(f"DEBUG: file_upload: {file_upload}")

        if not file_upload:
            messages.error(self.request, 'Пожалуйста, выберите файл для загрузки.')
            return self.form_invalid(form)

        # Создаем запись файла вручную БЕЗ поля child
        try:
            uploaded_file = UploadedFile(
                participation=participation,
                original_name=file_upload.name,
                file_size=file_upload.size,
                mime_type=file_upload.content_type,
                uploaded_by=self.request.user
            )

            # Генерируем уникальное имя файла
            import uuid
            file_extension = os.path.splitext(file_upload.name)[1].lower()
            stored_name = f"{uuid.uuid4()}{file_extension}"
            uploaded_file.stored_name = stored_name
            print(f"DEBUG: stored_name: {stored_name}")

            # Сохраняем файл
            from django.conf import settings
            if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
                upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'participation_files')
            else:
                upload_dir = os.path.join('media', 'uploads', 'participation_files')

            os.makedirs(upload_dir, exist_ok=True)
            print(f"DEBUG: upload_dir: {upload_dir}")

            file_path = os.path.join(upload_dir, stored_name)
            uploaded_file.file_path = file_path
            print(f"DEBUG: file_path: {file_path}")

            # Сохраняем файл в файловой системе
            with open(file_path, 'wb+') as destination:
                for chunk in file_upload.chunks():
                    destination.write(chunk)
            print(f"DEBUG: Файл успешно сохранен в файловой системе")

            # Сохраняем запись в БД
            uploaded_file.save()
            print(f"DEBUG: Запись о файле сохранена в БД")

            messages.success(self.request, f'Файл "{file_upload.name}" успешно загружен.')
            return HttpResponseRedirect(self.get_success_url())

        except Exception as e:
            messages.error(self.request, f'Ошибка при загрузке файла: {str(e)}')
            print(f"DEBUG: Ошибка при загрузке файла: {e}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        print(f"DEBUG: Начало form_invalid")
        print(f"DEBUG: Ошибки формы: {form.errors}")
        messages.error(
            self.request,
            'Пожалуйста, исправьте ошибки в форме.'
        )
        return super().form_invalid(form)

    def get_success_url(self):
        participation_id = self.request.GET.get('participation')
        print(f"DEBUG: get_success_url, participation_id: {participation_id}")
        if participation_id:
            return reverse_lazy('participation:detail', kwargs={'pk': participation_id})
        return reverse_lazy('participation:list')



# apps/participation/views/file_views.py (обновляем UploadedFileUpdateView)
# apps/participation/views.py (исправляем UploadedFileUpdateView)
# apps/participation/views.py (исправляем UploadedFileUpdateView)
class UploadedFileUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование файла (замена файла на другой)"""
    model = UploadedFile
    template_name = 'participation/file_form.html'
    fields = ['participation', 'original_name']

    def dispatch(self, request, *args, **kwargs):
        """Проверка прав доступа перед выполнением действия"""
        user = request.user
        uploaded_file = self.get_object()

        has_access = False
        if hasattr(user, 'role'):
            if user.role in ['methodist', 'admin']:
                # Методисты и админы могут редактировать всё
                has_access = True
            elif user.role == 'teacher':
                # Педагоги могут редактировать только свои файлы
                try:
                    teacher = Teacher.objects.get(user=user)
                    if uploaded_file.participation.enrollment.teacher == teacher:
                        has_access = True
                except Teacher.DoesNotExist:
                    has_access = False
                except Exception:
                    has_access = False
            else:
                has_access = False
        else:
            has_access = False

        if not has_access:
            messages.error(request, 'У вас нет прав для редактирования этого файла.')
            return HttpResponseRedirect(reverse_lazy('participation:file_detail', kwargs={'pk': uploaded_file.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        instance = self.get_object()

        # Фильтруем доступные участия в зависимости от роли пользователя
        if hasattr(user, 'role'):
            if user.role == 'teacher':
                try:
                    teacher = Teacher.objects.get(user=user)
                    # Только доступные участия для педагога
                    accessible_enrollments = StudioEnrollment.objects.filter(
                        teacher=teacher
                    ).values_list('id', flat=True)
                    accessible_participations = Participation.objects.filter(
                        enrollment_id__in=accessible_enrollments
                    ).select_related('child', 'event').order_by('child__fio', 'event__name')
                    form.fields['participation'].queryset = accessible_participations

                    # Если текущее участие не в списке доступных, добавляем его
                    if instance.participation and instance.participation.id not in [p.id for p in
                                                                                    accessible_participations]:
                        form.fields[
                            'participation'].queryset = accessible_participations | Participation.objects.filter(
                            id=instance.participation.id
                        ).select_related('child', 'event').order_by('child__fio', 'event__name')

                except Teacher.DoesNotExist:
                    form.fields['participation'].queryset = Participation.objects.none()
                except Exception as e:
                    print(f"DEBUG: Ошибка при фильтрации participation: {e}")
                    form.fields['participation'].queryset = Participation.objects.none()
            elif user.role in ['methodist', 'admin']:
                # Для методистов и админов все участия
                form.fields['participation'].queryset = Participation.objects.select_related(
                    'child', 'event'
                ).order_by('child__fio', 'event__name')
            else:
                form.fields['participation'].queryset = Participation.objects.none()
        else:
            form.fields['participation'].queryset = Participation.objects.none()

        # Делаем поле оригинального имени доступным для редактирования
        form.fields['original_name'].widget.attrs.pop('readonly', None)

        return form

    def form_valid(self, form):
        instance = self.get_object()
        user = self.request.user

        # Обработка замены файла, если он был загружен
        file_upload = self.request.FILES.get('file_upload')
        if file_upload:
            try:
                # Удаляем старый файл из файловой системы
                old_file_path = instance.file_path
                if os.path.exists(old_file_path):
                    os.remove(old_file_path)
                    print(f"DEBUG: Старый файл удален: {old_file_path}")

                # Сохраняем новый файл
                import uuid
                file_extension = os.path.splitext(file_upload.name)[1].lower()
                stored_name = f"{uuid.uuid4()}{file_extension}"

                # Определяем путь для сохранения файла
                from django.conf import settings
                if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
                    upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'participation_files')
                else:
                    upload_dir = os.path.join('media', 'uploads', 'participation_files')

                os.makedirs(upload_dir, exist_ok=True)
                file_path = os.path.join(upload_dir, stored_name)

                # Сохраняем новый файл
                with open(file_path, 'wb+') as destination:
                    for chunk in file_upload.chunks():
                        destination.write(chunk)

                # Обновляем информацию о файле
                form.instance.original_name = file_upload.name
                form.instance.stored_name = stored_name
                form.instance.file_path = file_path
                form.instance.file_size = file_upload.size
                form.instance.mime_type = file_upload.content_type
                form.instance.uploaded_by = user

                messages.success(
                    self.request,
                    f'Файл успешно заменен на "{file_upload.name}".'
                )

            except Exception as e:
                messages.error(
                    self.request,
                    f'Ошибка при замене файла: {str(e)}'
                )
                return self.form_invalid(form)
        else:
            # Если файл не был загружен, сохраняем только метаданные
            messages.success(
                self.request,
                'Информация о файле успешно обновлена.'
            )

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_file_update'] = True  # Флаг для шаблона
        return context

    def get_success_url(self):
        return reverse_lazy('participation:file_detail', kwargs={'pk': self.object.pk})


# apps/participation/views.py (исправляем UploadedFileDeleteView)
# apps/participation/views.py (обновляем UploadedFileDeleteView)
# apps/participation/views/file_views.py (обновляем UploadedFileDeleteView)
class UploadedFileDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление файла"""
    model = UploadedFile
    template_name = 'participation/file_confirm_delete.html'
    context_object_name = 'file'  # Добавляем это, чтобы объект назывался 'file'

    def get_success_url(self):
        # Перенаправляем на детали участия, к которому принадлежал файл
        return reverse_lazy('participation:detail', kwargs={'pk': self.object.participation.pk})

    def delete(self, request, *args, **kwargs):
        messages.success(
            request,
            f'Файл "{self.object.original_name}" успешно удален.'
        )
        return super().delete(request, *args, **kwargs)

# Функции для работы с файлами

# apps/participation/views.py (исправляем download_file)
# apps/participation/views.py (исправляем download_file)
@login_required
def download_file(request, pk):
    """Скачивание файла"""
    try:
        uploaded_file = get_object_or_404(UploadedFile, pk=pk)
        print(f"DEBUG: Файл найден: {uploaded_file.original_name}")
    except Exception as e:
        print(f"DEBUG: Ошибка при поиске файла: {e}")
        raise Http404("Файл не найден")

    # Проверяем права доступа
    user = request.user
    has_access = False

    print(f"DEBUG: Пользователь: {user.username}, роль: {getattr(user, 'role', 'нет роли')}")

    if hasattr(user, 'role'):
        if user.role in ['methodist', 'admin']:
            has_access = True
            print(f"DEBUG: Пользователь {user.username} имеет полный доступ")
        elif user.role == 'teacher':
            try:
                teacher = Teacher.objects.get(user=user)
                if uploaded_file.participation.enrollment.teacher == teacher:
                    has_access = True
                    print(f"DEBUG: Пользователь {user.username} - владелец файла")
                else:
                    print(f"DEBUG: Пользователь {user.username} НЕ владелец файла")
            except Teacher.DoesNotExist:
                print(f"DEBUG: Пользователь {user.username} не найден как учитель")
            except Exception as e:
                print(f"DEBUG: Ошибка при проверке прав учителя: {e}")
        else:
            print(f"DEBUG: У пользователя {user.username} неизвестная роль: {user.role}")
    else:
        print(f"DEBUG: У пользователя {user.username} нет роли")

    if not has_access:
        raise Http404("У вас нет прав для скачивания этого файла")

    # Проверяем существование файла - пробуем разные пути
    file_path = uploaded_file.file_path
    print(f"DEBUG: Путь к файлу из БД: {file_path}")

    # Список возможных путей к файлу
    possible_paths = [
        file_path,  # Путь из БД
        os.path.join(settings.MEDIA_ROOT, file_path) if hasattr(settings, 'MEDIA_ROOT') else None,  # Путь с MEDIA_ROOT
        os.path.join('media', file_path),  # Относительный путь
        os.path.join(settings.BASE_DIR, file_path) if hasattr(settings, 'BASE_DIR') else None,  # Путь с BASE_DIR
        os.path.join(settings.BASE_DIR, 'media', file_path) if hasattr(settings, 'BASE_DIR') else None,  # Полный путь
    ]

    # Убираем None значения
    possible_paths = [path for path in possible_paths if path is not None]

    found_file_path = None
    for path in possible_paths:
        print(f"DEBUG: Пробуем путь: {path}")
        print(f"DEBUG: Существует ли файл: {os.path.exists(path)}")
        if os.path.exists(path):
            found_file_path = path
            print(f"DEBUG: Файл найден по пути: {path}")
            break

    if found_file_path is None:
        print(f"DEBUG: Файл НЕ найден ни по одному из путей")
        # Попробуем найти файл по stored_name
        stored_name = uploaded_file.stored_name
        if stored_name:
            alternative_paths = [
                os.path.join('uploads', 'participation_files', stored_name),
                os.path.join('media', 'uploads', 'participation_files', stored_name),
                os.path.join(settings.MEDIA_ROOT, 'uploads', 'participation_files', stored_name) if hasattr(settings,
                                                                                                            'MEDIA_ROOT') else None,
                os.path.join(settings.BASE_DIR, 'media', 'uploads', 'participation_files', stored_name) if hasattr(
                    settings, 'BASE_DIR') else None,
            ]
            alternative_paths = [path for path in alternative_paths if path is not None]

            for path in alternative_paths:
                print(f"DEBUG: Пробуем альтернативный путь: {path}")
                if os.path.exists(path):
                    found_file_path = path
                    print(f"DEBUG: Файл найден по альтернативному пути: {path}")
                    break

    if found_file_path:
        try:
            response = FileResponse(
                open(found_file_path, 'rb'),
                content_type=uploaded_file.mime_type
            )
            response['Content-Disposition'] = f'attachment; filename="{uploaded_file.original_name}"'
            print(f"DEBUG: Файл успешно отправлен для скачивания")
            return response
        except Exception as e:
            print(f"DEBUG: Ошибка при открытии файла: {e}")
            raise Http404(f"Ошибка при открытии файла: {e}")
    else:
        print(f"DEBUG: Файл НЕ найден ни по одному из путей")
        raise Http404("Файл не найден на сервере. Возможно, он был удален.")


# apps/participation/views/file_views.py (обновляем check_file_access)
@login_required
def view_file(request, pk):
    """Просмотр файла в браузере"""
    print(f"DEBUG: Попытка просмотра файла с ID={pk}")

    # Проверяем, существует ли файл в базе данных
    try:
        uploaded_file = UploadedFile.objects.get(pk=pk)
        print(f"DEBUG: Файл найден в БД: {uploaded_file.original_name}")
    except UploadedFile.DoesNotExist:
        print(f"DEBUG: Файл с ID={pk} не найден в БД")
        raise Http404("Файл не найден в базе данных")
    except Exception as e:
        print(f"DEBUG: Ошибка при поиске файла в БД: {e}")
        raise Http404("Ошибка при поиске файла")

    # Проверяем права доступа (расширенная проверка для просмотра)
    user = request.user
    print(f"DEBUG: Пользователь: {user.username}, роль: {getattr(user, 'role', 'нет роли')}")

    has_access = False
    if hasattr(user, 'role'):
        if user.role in ['methodist', 'admin']:
            has_access = True
            print(f"DEBUG: Пользователь {user.username} имеет полный доступ (methodist/admin)")
        elif user.role == 'teacher':
            try:
                # Для педагогов - разрешаем просмотр любых файлов (только просмотр!)
                teacher = Teacher.objects.get(user=user)
                # Проверяем, что файл существует (для просмотра достаточно того, что пользователь - учитель)
                has_access = True
                print(f"DEBUG: Пользователь {user.username} - учитель, разрешен просмотр")
            except Teacher.DoesNotExist:
                print(f"DEBUG: Пользователь {user.username} не найден как учитель")
            except Exception as e:
                print(f"DEBUG: Ошибка при проверке прав учителя: {e}")
        else:
            print(f"DEBUG: У пользователя {user.username} неизвестная роль: {user.role}")
    else:
        print(f"DEBUG: У пользователя {user.username} нет роли")

    if not has_access:
        print(f"DEBUG: Доступ запрещен для пользователя {user.username}")
        raise Http404("У вас нет прав для просмотра этого файла")

    # Проверяем существование файла в файловой системе
    file_path = uploaded_file.file_path
    print(f"DEBUG: Путь к файлу в БД: {file_path}")
    print(f"DEBUG: Абсолютный путь: {os.path.abspath(file_path)}")
    print(f"DEBUG: Существует ли файл: {os.path.exists(file_path)}")

    if os.path.exists(file_path):
        print(f"DEBUG: Файл существует, пробуем открыть")
        try:
            # Открываем файл и отправляем его
            file_handle = open(file_path, 'rb')
            response = FileResponse(
                file_handle,
                content_type=uploaded_file.mime_type
            )
            response['Content-Disposition'] = f'inline; filename="{uploaded_file.original_name}"'
            print(f"DEBUG: Файл успешно отправлен для просмотра")
            return response
        except Exception as e:
            print(f"DEBUG: Ошибка при открытии файла: {e}")
            raise Http404(f"Ошибка при открытии файла: {e}")
    else:
        print(f"DEBUG: Файл НЕ существует по указанному пути")
        # Попробуем найти файл в стандартной директории
        standard_path = os.path.join('media', 'uploads', 'participation_files', uploaded_file.stored_name)
        print(f"DEBUG: Пробуем стандартный путь: {standard_path}")
        if os.path.exists(standard_path):
            print(f"DEBUG: Файл найден по стандартному пути")
            try:
                file_handle = open(standard_path, 'rb')
                response = FileResponse(
                    file_handle,
                    content_type=uploaded_file.mime_type
                )
                response['Content-Disposition'] = f'inline; filename="{uploaded_file.original_name}"'
                return response
            except Exception as e:
                print(f"DEBUG: Ошибка при открытии файла по стандартному пути: {e}")
                raise Http404(f"Ошибка при открытии файла: {e}")
        else:
            print(f"DEBUG: Файл НЕ найден и по стандартному пути")
            raise Http404("Файл не найден на сервере. Возможно, он был удален.")