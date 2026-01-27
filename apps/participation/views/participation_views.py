# apps/participation/views/participation_views.py
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponseRedirect, Http404
from django.db import transaction, IntegrityError
from django.utils import timezone
from .base_views import BaseParticipationView
from ..models import Participation, UploadedFile
from ...children.models import Teacher, StudioEnrollment, Child, Studio
from ...events.models import Event, ResultType
import os

class ParticipationListView(BaseParticipationView, ListView):
    """Список участий"""
    template_name = 'participation/participation_list.html'
    context_object_name = 'participations'
    paginate_by = 50

    def get_queryset(self):
        user = self.request.user
        queryset = Participation.objects.select_related(
            'child', 'event', 'result_type', 'enrollment__studio', 'enrollment__teacher'
        ).order_by('-report_date', 'child__fio')

        # Фильтрация по доступу в зависимости от роли пользователя
        if hasattr(user, 'role'):
            if user.role == 'teacher':
                # Для педагогов - только их ученики
                try:
                    teacher = Teacher.objects.get(user=user)
                    # Получаем записи детей, записанных к этому педагогу
                    accessible_enrollments = StudioEnrollment.objects.filter(
                        teacher=teacher
                    ).values_list('id', flat=True)
                    queryset = queryset.filter(enrollment_id__in=accessible_enrollments)
                except Teacher.DoesNotExist:
                    queryset = queryset.none()
                except Exception:
                    queryset = queryset.none()
            elif user.role in ['methodist', 'admin']:
                # Для методистов и админов - все участия
                pass
            else:
                # Для других ролей - пустой список
                queryset = queryset.none()
        else:
            # Для пользователей без роли - пустой список
            queryset = queryset.none()

        # Фильтры
        child_id = self.request.GET.get('child')
        event_id = self.request.GET.get('event')
        result_type_id = self.request.GET.get('result_type')
        search = self.request.GET.get('search')

        if child_id:
            queryset = queryset.filter(child_id=child_id)
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        if result_type_id:
            queryset = queryset.filter(result_type_id=result_type_id)
        if search:
            queryset = queryset.filter(
                Q(child__fio__icontains=search) |
                Q(event__name__icontains=search) |
                Q(custom_result__icontains=search) |
                Q(enrollment__studio__name__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Для фильтров - только доступные данные
        if hasattr(user, 'role'):
            if user.role == 'teacher':
                try:
                    teacher = Teacher.objects.get(user=user)
                    # Только дети этого педагога
                    context['children'] = Child.objects.filter(
                        studioenrollment__teacher=teacher
                    ).distinct().order_by('fio')
                    # Только студии этого педагога
                    context['studios'] = Studio.objects.filter(
                        studioenrollment__teacher=teacher
                    ).distinct().order_by('name')
                    # Только конкурсы этого педагога
                    context['events'] = Event.objects.filter(
                        participation__enrollment__teacher=teacher
                    ).distinct().filter(is_active=True).order_by('name')
                except (Teacher.DoesNotExist, Exception):
                    context['children'] = Child.objects.none()
                    context['studios'] = Studio.objects.none()
                    context['events'] = Event.objects.none()
            elif user.role in ['methodist', 'admin']:
                # Для методистов и админов - все данные
                context['children'] = Child.objects.all().order_by('fio')
                context['studios'] = Studio.objects.all().order_by('name')
                context['events'] = Event.objects.filter(is_active=True).order_by('name')
            else:
                context['children'] = Child.objects.none()
                context['studios'] = Studio.objects.none()
                context['events'] = Event.objects.none()
        else:
            context['children'] = Child.objects.none()
            context['studios'] = Studio.objects.none()
            context['events'] = Event.objects.none()

        context['result_types'] = ResultType.objects.all().order_by('name')

        # Текущие значения фильтров
        context['current_child'] = self.request.GET.get('child', '')
        context['current_event'] = self.request.GET.get('event', '')
        context['current_result_type'] = self.request.GET.get('result_type', '')
        context['current_search'] = self.request.GET.get('search', '')

        return context

class ParticipationDetailView(BaseParticipationView, DetailView):
    """Детали участия"""
    template_name = 'participation/participation_detail.html'
    context_object_name = 'participation'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Проверяем, имеет ли пользователь доступ к редактированию
        user = self.request.user
        participation = self.object

        can_edit = self.check_user_access(user, participation)
        context['can_edit_participation'] = can_edit

        # Получаем прикрепленные файлы
        files = UploadedFile.objects.filter(participation=participation).order_by('-upload_date')
        context['files'] = files

        return context

# apps/participation/views/participation_views.py (исправляем ParticipationCreateView)
class ParticipationCreateView(BaseParticipationView, CreateView):
    """Создание участия"""
    model = Participation
    template_name = 'participation/participation_form.html'
    fields = ['enrollment', 'event', 'result_type', 'custom_result', 'report_date']
    success_url = reverse_lazy('participation:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        enrollment_id = self.request.GET.get('enrollment')

        # Если передан enrollment_id, передаем информацию об этом в контекст
        if enrollment_id:
            try:
                enrollment = StudioEnrollment.objects.select_related(
                    'child', 'studio'
                ).get(id=enrollment_id)
                context['enrollment_info'] = {
                    'child_fio': enrollment.child.fio,
                    'studio_name': enrollment.studio.name,
                    'enrollment_id': enrollment.id
                }
                context['enrollment_id'] = enrollment_id
                print(f"DEBUG: Передаем enrollment_info в контекст: {context['enrollment_info']}")
            except Exception as e:
                print(f"DEBUG: Ошибка при получении enrollment_info: {e}")
                context['enrollment_info'] = None
                context['enrollment_id'] = None
        else:
            context['enrollment_info'] = None
            context['enrollment_id'] = None

        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        enrollment_id = self.request.GET.get('enrollment')

        # Фильтруем доступные записи в студии в зависимости от роли пользователя
        form.fields['enrollment'].queryset = self.get_accessible_enrollments(user)

        # Если передан enrollment_id, устанавливаем его как начальное значение
        if enrollment_id:
            try:
                enrollment = StudioEnrollment.objects.get(id=enrollment_id)
                # Проверяем, имеет ли пользователь доступ к этой записи
                if enrollment in form.fields['enrollment'].queryset:
                    form.fields['enrollment'].initial = enrollment
            except StudioEnrollment.DoesNotExist:
                print(f"DEBUG: Запись enrollment_id={enrollment_id} не найдена")

        # Только активные конкурсы
        form.fields['event'].queryset = Event.objects.filter(is_active=True).order_by('name')
        # Все типы результатов
        form.fields['result_type'].queryset = ResultType.objects.all().order_by('name')

        # Устанавливаем текущую дату по умолчанию
        if not form.initial.get('report_date'):
            from datetime import date
            form.initial['report_date'] = date.today()

        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        enrollment = form.cleaned_data['enrollment']
        form.instance.child = enrollment.child

        # Проверяем, не существует ли уже такое участие (до сохранения)
        child = form.instance.child
        event = form.cleaned_data['event']
        current_user = self.request.user
        print(f"DEBUG: Проверяем дубликат - enrollment={enrollment.id}, event={event.id}, created_by={current_user.id}")
        # Проверяем существование участия
        existing = Participation.objects.filter(
            enrollment=enrollment,
            event=event,
            created_by=current_user
        ).exists()

        print(f"DEBUG: Дубликат найден: {existing}")


        print(f"DEBUG: Начало валидации участия для ребенка {child.fio} в конкурсе {event.name}")

        # Используем транзакцию для обеспечения целостности данных
        try:
            with transaction.atomic():
                print(f"DEBUG: Начало транзакции")
                # Проверяем существование участия
                if Participation.objects.filter(enrollment=enrollment, event=event, created_by=self.request.user).exists():
                    print(f"DEBUG: Участие уже существует")
                    messages.error(
                        self.request,
                        f'Ребенок {child.fio} уже участвует в конкурсе "{event.name}"'
                    )
                    return self.form_invalid(form)

                file_upload = self.request.FILES.get('file_upload')
                if file_upload.size > 100 * 1024 * 1024:  # 100MB
                    messages.error(
                        self.request,
                        f'Файл слишком большой. Размер: {file_upload.size / 1024 / 1024:.2f} MB. Максимум: 100 MB'
                    )
                    return self.form_invalid(form)


                try:
                    print(f"DEBUG: Начало сохранения участия")
                    # Сохраняем участие
                    response = super().form_valid(form)
                except Exception as e:
                    print(f"DEBUG: Ошибка при сохранении участия: {e}")
                    messages.warning(
                        self.request,
                        f'Участие не было сохранено из-за ошибки: {str(e)}'
                    )
                    return self.form_invalid(form)



                # Обрабатываем загрузку файла, если она есть
                file_upload = self.request.FILES.get('file_upload')
                if file_upload:
                    try:
                        self.handle_file_upload(file_upload)
                        messages.success(
                            self.request,
                            f'Файл "{file_upload.name}" успешно загружен.'
                        )
                    except Exception as e:
                        messages.warning(
                            self.request,
                            f'Файл не был загружен из-за ошибки: {str(e)}'
                        )

                messages.success(self.request, 'Участие успешно зарегистрировано.')
                return response

        except IntegrityError:
            # Если произошла ошибка целостности (дубликат), показываем сообщение
            messages.error(
                self.request,
                f'Ребенок {child.fio} уже участвует в конкурсе "{event.name}"'
            )
            return self.form_invalid(form)

    def handle_file_upload(self, file_upload):
        """Обработка загрузки файла"""
        print(f"DEBUG: Начало загрузки файла: {file_upload.name}")

        # Создаем запись файла
        uploaded_file = UploadedFile(
            participation=self.object,
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
        print(f"DEBUG: Уникальное имя файла: {stored_name}")

        # Определяем путь для сохранения файла
        from django.conf import settings
        if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'participation_files')
        else:
            upload_dir = os.path.join('media', 'uploads', 'participation_files')

        # Создаем директорию, если она не существует
        os.makedirs(upload_dir, exist_ok=True)
        print(f"DEBUG: Директория для загрузки: {upload_dir}")

        # Абсолютный путь для физического сохранения
        absolute_file_path = os.path.join(upload_dir, stored_name)
        uploaded_file.file_path = absolute_file_path
        print(f"DEBUG: Абсолютный путь к файлу: {absolute_file_path}")

        try:
            # Сохраняем файл в файловой системе
            with open(absolute_file_path, 'wb+') as destination:
                for chunk in file_upload.chunks():
                    destination.write(chunk)
            print(f"DEBUG: Файл успешно сохранен")

            # Сохраняем запись о файле в БД
            uploaded_file.save()
            print(f"DEBUG: Запись о файле сохранена в БД, ID={uploaded_file.id}")

        except Exception as e:
            print(f"DEBUG: Ошибка при сохранении файла: {e}")
            # Удаляем файл, если не удалось сохранить запись в БД
            if os.path.exists(absolute_file_path):
                os.remove(absolute_file_path)
            raise e

    def form_invalid(self, form):
        print(f"DEBUG: Форма невалидна. Ошибки: {form.errors}")
        messages.error(
            self.request,
            'Пожалуйста, исправьте ошибки в форме.'
        )
        return super().form_invalid(form)

class ParticipationUpdateView(BaseParticipationView, UpdateView):
    """Редактирование участия"""
    template_name = 'participation/participation_form.html'
    fields = ['enrollment', 'event', 'result_type', 'custom_result', 'report_date']
    success_url = reverse_lazy('participation:list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        instance = self.get_object()

        # Добавляем информацию о текущем выборе для отображения в шаблоне
        if instance.enrollment:
            context['enrollment_info'] = {
                'child_fio': instance.enrollment.child.fio,
                'studio_name': instance.enrollment.studio.name
            }

        return context
    # def dispatch(self, request, *args, **kwargs):
    #     """Проверка прав доступа перед выполнением действия"""
    #     # Проверяем доступ перед выполнением действия
    #     user = request.user
    #     participation = self.get_object()
    #
    #     has_access = self.check_user_access(user, participation)
    #     if not has_access:
    #         messages.error(request, 'У вас нет прав для редактирования этого участия.')
    #         return HttpResponseRedirect(reverse_lazy('participation:detail', kwargs={'pk': participation.pk}))
    #
    #     return super().dispatch(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        """Проверка прав доступа перед выполнением действия"""
        # Проверяем доступ перед выполнением действия
        user = request.user
        participation = self.get_object()

        has_access = self.check_user_access(user, participation)

        # Дополнительно проверяем, что пользователь — создатель записи
        if participation.created_by != user:
            messages.error(request, 'У вас нет прав для редактирования этой записи.')
            return HttpResponseRedirect(reverse_lazy('participation:detail', kwargs={'pk': participation.pk}))

        if not has_access:
            messages.error(request, 'У вас нет прав для редактирования этого участия.')
            return HttpResponseRedirect(reverse_lazy('participation:detail', kwargs={'pk': participation.pk}))

        return super().dispatch(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user
        instance = self.get_object()

        # Фильтруем доступные записи в студии в зависимости от роли пользователя
        form.fields['enrollment'].queryset = self.get_accessible_enrollments(user)

        # Только активные конкурсы
        form.fields['event'].queryset = Event.objects.filter(is_active=True).order_by('name')
        # Все типы результатов
        form.fields['result_type'].queryset = ResultType.objects.all().order_by('name')

        return form

    def form_valid(self, form):
        enrollment = form.cleaned_data['enrollment']
        form.instance.child = enrollment.child

        # Проверяем, не создаст ли это дубликат
        child = form.instance.child
        event = form.cleaned_data['event']
        current_object = self.get_object()

        if Participation.objects.filter(
            enrollment=enrollment, event=event, created_by=self.request.user
        ).exclude(pk=current_object.pk).exists():
            messages.error(
                self.request,
                f'Ребенок {child.fio} уже участвует в конкурсе "{event.name}"'
            )
            return self.form_invalid(form)

        file_upload = self.request.FILES.get('file_upload')
        if file_upload.size > 100 * 1024 * 1024:  # 100MB
            messages.error(
                self.request,
                f'Файл слишком большой. Размер: {file_upload.size / 1024 / 1024:.2f} MB. Максимум: 100 MB'
            )
            return self.form_invalid(form)

        # Сохраняем участие
        response = super().form_valid(form)

        # Обрабатываем загрузку файла, если она есть
        file_upload = self.request.FILES.get('file_upload')
        if file_upload:
            try:
                # СОЗДАЕМ экземпляр UploadedFile перед вызовом функции
                uploaded_file = UploadedFile(
                    participation=self.object,
                    original_name=file_upload.name,
                    file_size=file_upload.size,
                    mime_type=file_upload.content_type,
                    uploaded_by=self.request.user
                )
                from .file_handlers import handle_file_upload
                handle_file_upload(uploaded_file, file_upload, self.request.user)
                messages.success(
                    self.request,
                    f'Файл "{file_upload.name}" успешно загружен.'
                )
            except Exception as e:
                messages.warning(
                    self.request,
                    f'Файл не был загружен из-за ошибки: {str(e)}'
                )

        messages.success(self.request, 'Участие успешно обновлено.')
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            'Пожалуйста, исправьте ошибки в форме.'
        )
        return super().form_invalid(form)



class ParticipationDeleteView(BaseParticipationView, DeleteView):
    """Удаление участия"""
    template_name = 'participation/participation_confirm_delete.html'
    success_url = reverse_lazy('participation:list')

    # def dispatch(self, request, *args, **kwargs):
    #     # Проверяем доступ перед выполнением действия
    #     user = request.user
    #     participation = self.get_object()
    #
    #     has_access = self.check_user_access(user, participation)
    #     if not has_access:
    #         messages.error(request, 'У вас нет прав для удаления этого участия.')
    #         return HttpResponseRedirect(reverse_lazy('participation:detail', kwargs={'pk': participation.pk}))
    #
    #     return super().dispatch(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Проверяем доступ перед выполнением действия
        user = request.user
        participation = self.get_object()

        has_access = self.check_user_access(user, participation)

        # Дополнительно проверяем, что пользователь — создатель записи
        if participation.created_by != user:
            messages.error(request, 'У вас нет прав для удаления этой записи.')
            return HttpResponseRedirect(reverse_lazy('participation:detail', kwargs={'pk': participation.pk}))

        if not has_access:
            messages.error(request, 'У вас нет прав для удаления этого участия.')
            return HttpResponseRedirect(reverse_lazy('participation:detail', kwargs={'pk': participation.pk}))

        return super().dispatch(request, *args, **kwargs)


    def delete(self, request, *args, **kwargs):
        messages.success(
            request,
            f'Участие ребенка {self.get_object().child.fio} в конкурсе "{self.get_object().event.name}" успешно удалено.'
        )
        return super().delete(request, *args, **kwargs)



