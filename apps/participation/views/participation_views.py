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

        # Используем транзакцию для обеспечения целостности данных
        try:
            with transaction.atomic():
                # Проверяем существование участия
                if Participation.objects.filter(child=child, event=event).exists():
                    messages.error(
                        self.request,
                        f'Ребенок {child.fio} уже участвует в конкурсе "{event.name}"'
                    )
                    return self.form_invalid(form)

                # Сохраняем участие
                response = super().form_valid(form)

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
    def dispatch(self, request, *args, **kwargs):
        """Проверка прав доступа перед выполнением действия"""
        # Проверяем доступ перед выполнением действия
        user = request.user
        participation = self.get_object()

        has_access = self.check_user_access(user, participation)
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
            child=child, event=event
        ).exclude(pk=current_object.pk).exists():
            messages.error(
                self.request,
                f'Ребенок {child.fio} уже участвует в конкурсе "{event.name}"'
            )
            return self.form_invalid(form)

        # Сохраняем участие
        response = super().form_valid(form)

        # Обрабатываем загрузку файла, если она есть
        file_upload = self.request.FILES.get('file_upload')
        if file_upload:
            try:
                from .file_handlers import handle_file_upload
                handle_file_upload(self.object, file_upload, self.request.user)
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
        return super().form_valid(form)

class ParticipationDeleteView(BaseParticipationView, DeleteView):
    """Удаление участия"""
    template_name = 'participation/participation_confirm_delete.html'
    success_url = reverse_lazy('participation:list')

    def dispatch(self, request, *args, **kwargs):
        # Проверяем доступ перед выполнением действия
        user = request.user
        participation = self.get_object()

        has_access = self.check_user_access(user, participation)
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


# # apps/participation/views.py (добавляем в конец)
# import pandas as pd
# from django.http import HttpResponse
# from io import BytesIO
#
#
# class ParticipationReportView(LoginRequiredMixin, View):
#     """Отчет по участию детей в конкурсах"""
#
#     def get(self, request, *args, **kwargs):
#         """Показ формы для генерации отчета"""
#         user = request.user
#
#         # Получаем доступные направления в зависимости от роли пользователя
#         directions = self.get_accessible_directions(user)
#
#         context = {
#             'directions': directions,
#             'page_title': 'Отчет по участию детей в конкурсах'
#         }
#         return render(request, 'participation/report_form.html', context)
#
#     def post(self, request, *args, **kwargs):
#         """Генерация отчета"""
#         user = request.user
#
#         # Получаем параметры отчета
#         direction_ids = request.POST.getlist('directions')
#         start_date = request.POST.get('start_date')
#         end_date = request.POST.get('end_date')
#
#         # Проверяем параметры
#         if not direction_ids:
#             messages.error(request, 'Пожалуйста, выберите хотя бы одно направление.')
#             return self.get(request, *args, **kwargs)
#
#         try:
#             from datetime import datetime
#             start_date = datetime.strptime(start_date, '%Y-%m-%d').date() if start_date else None
#             end_date = datetime.strptime(end_date, '%Y-%m-%d').date() if end_date else None
#         except ValueError:
#             messages.error(request, 'Неверный формат дат.')
#             return self.get(request, *args, **kwargs)
#
#         # Генерируем отчет
#         try:
#             excel_buffer = self.generate_report(direction_ids, start_date, end_date, user)
#
#             # Создаем HTTP ответ с Excel файлом
#             response = HttpResponse(
#                 excel_buffer.getvalue(),
#                 content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
#             )
#             response['Content-Disposition'] = 'attachment; filename="participation_report.xlsx"'
#
#             messages.success(request, 'Отчет успешно сгенерирован.')
#             return response
#
#         except Exception as e:
#             messages.error(request, f'Ошибка при генерации отчета: {str(e)}')
#             return self.get(request, *args, **kwargs)
#
#     def get_accessible_directions(self, user):
#         """Получение доступных направлений в зависимости от роли пользователя"""
#         if hasattr(user, 'role'):
#             if user.role == 'teacher':
#                 try:
#                     teacher = Teacher.objects.get(user=user)
#                     # Только направления, к которым у педагога есть доступ через студии
#                     accessible_studio_ids = TeacherStudioAccess.objects.filter(
#                         teacher=teacher
#                     ).values_list('studio_id', flat=True)
#                     accessible_studios = Studio.objects.filter(id__in=accessible_studio_ids)
#                     direction_ids = accessible_studios.values_list('direction_id', flat=True)
#                     return Direction.objects.filter(id__in=direction_ids).order_by('name')
#                 except Teacher.DoesNotExist:
#                     return Direction.objects.none()
#             elif user.role in ['methodist', 'admin']:
#                 # Для методистов и админов все направления
#                 return Direction.objects.all().order_by('name')
#         return Direction.objects.none()
#
#     def generate_report(self, direction_ids, start_date, end_date, user):
#         """Генерация отчета в Excel"""
#         from datetime import date
#         import calendar
#
#         # Определяем период отчета
#         if not start_date:
#             start_date = date(2025, 9, 1)  # Сентябрь 2025
#         if not end_date:
#             end_date = date(2026, 5, 31)  # Май 2026
#
#         print(f"DEBUG: Генерация отчета с {start_date} по {end_date}")
#         print(f"DEBUG: Направления: {direction_ids}")
#
#         # Получаем данные для отчета
#         queryset = Participation.objects.select_related(
#             'child', 'event', 'enrollment__studio', 'enrollment__teacher', 'enrollment__direction'
#         )
#
#         # Фильтруем по направлениям
#         queryset = queryset.filter(enrollment__studio__direction_id__in=direction_ids)
#
#         # Фильтруем по дате отчета
#         queryset = queryset.filter(report_date__range=[start_date, end_date])
#
#         # Фильтруем по доступу пользователя
#         if hasattr(user, 'role'):
#             if user.role == 'teacher':
#                 try:
#                     teacher = Teacher.objects.get(user=user)
#                     queryset = queryset.filter(enrollment__teacher=teacher)
#                 except Teacher.DoesNotExist:
#                     queryset = queryset.none()
#             # Для methodist и admin фильтрация не нужна - показываем все
#
#         print(f"DEBUG: Найдено записей для отчета: {queryset.count()}")
#
#         # Группируем данные
#         report_data = {}
#
#         # Месяцы отчетного периода
#         months = []
#         current_date = start_date
#         while current_date <= end_date:
#             months.append((current_date.year, current_date.month))
#             # Переходим к следующему месяцу
#             if current_date.month == 12:
#                 current_date = date(current_date.year + 1, 1, 1)
#             else:
#                 current_date = date(current_date.year, current_date.month + 1, 1)
#
#         print(f"DEBUG: Месяцы для отчета: {months}")
#
#         # Уровни конкурсов
#         level_choices = Event.LEVEL_CHOICES
#         level_dict = dict(level_choices)
#         print(f"DEBUG: Уровни конкурсов: {level_dict}")
#
#         # Собираем данные
#         for participation in queryset:
#             direction = participation.enrollment.direction
#             teacher = participation.enrollment.teacher
#             report_date = participation.report_date
#             event_level = participation.event.level
#
#             # Ключ для группировки
#             key = (direction.name, teacher.fio)
#
#             if key not in report_data:
#                 report_data[key] = {}
#                 # Инициализируем счетчики для всех месяцев и уровней
#                 for year, month in months:
#                     month_key = f"{year}-{month:02d}"
#                     report_data[key][month_key] = {}
#                     for level_code, level_name in level_choices:
#                         report_data[key][month_key][level_code] = 0
#
#             # Увеличиваем счетчик
#             month_key = f"{report_date.year}-{report_date.month:02d}"
#             if month_key in report_data[key]:
#                 if event_level in report_data[key][month_key]:
#                     report_data[key][month_key][event_level] += 1
#                     print(f"DEBUG: Увеличен счетчик для {key} {month_key} {event_level}")
#
#         print(f"DEBUG: Сгруппированные данные: {report_data}")
#
#         # Создаем Excel файл
#         buffer = BytesIO()
#         with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
#             # Создаем DataFrame
#             rows = []
#
#             # Заголовки колонок
#             headers = ['Направление', 'ФИО педагога']
#             for year, month in months:
#                 month_name = calendar.month_name[month]
#                 headers.extend([
#                     f'{month_name} {year} - Центровский',
#                     f'{month_name} {year} - Городской',
#                     f'{month_name} {year} - Районный',
#                     f'{month_name} {year} - Республиканский',
#                     f'{month_name} {year} - Региональный',
#                     f'{month_name} {year} - Межрегиональный',
#                     f'{month_name} {year} - Всероссийский',
#                     f'{month_name} {year} - Международный'
#                 ])
#             headers.append('Итого')
#
#             # Данные
#             for (direction_name, teacher_fio), monthly_data in report_data.items():
#                 row = [direction_name, teacher_fio]
#                 total = 0
#
#                 for year, month in months:
#                     month_key = f"{year}-{month:02d}"
#                     if month_key in monthly_data:
#                         month_total = 0
#                         for level_code, level_name in level_choices:
#                             count = monthly_data[month_key].get(level_code, 0)
#                             row.append(count)
#                             month_total += count
#                         total += month_total
#                     else:
#                         # Если нет данных за месяц, заполняем нулями
#                         for _ in level_choices:
#                             row.append(0)
#
#                 row.append(total)
#                 rows.append(row)
#
#             # Создаем DataFrame и записываем в Excel
#             df = pd.DataFrame(rows, columns=headers)
#             df.to_excel(writer, sheet_name='Отчет по участию', index=False)
#
#             # Форматируем лист
#             worksheet = writer.sheets['Отчет по участию']
#
#             # Автоподбор ширины колонок
#             for column in worksheet.columns:
#                 max_length = 0
#                 column_letter = column[0].column_letter
#                 for cell in column:
#                     try:
#                         if len(str(cell.value)) > max_length:
#                             max_length = len(str(cell.value))
#                     except:
#                         pass
#                 adjusted_width = (max_length + 2)
#                 worksheet.column_dimensions[column_letter].width = min(adjusted_width, 50)
#
#         buffer.seek(0)
#         return buffer