# apps/events/views.py (простая версия)
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.views.generic.edit import FormView
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils import timezone
from .models import Event, ResultType
import pandas as pd
from django import forms

from .forms import EventForm  # Импортируем нашу форму

from ..children.models import Teacher
from ..participation.models import Participation


# apps/events/views.py (обновляем EventListView)
class EventListView(LoginRequiredMixin, ListView):
    """Список конкурсов"""
    model = Event
    template_name = 'events/event_list.html'
    context_object_name = 'events'
    paginate_by = 50

    def get_queryset(self):
        user = self.request.user
        status_filter = self.request.GET.get('status', 'published')

        # Базовая выборка
        queryset = Event.objects.all()

        if status_filter == 'published':
            # Все видят все опубликованные конкурсы
            queryset = queryset.filter(status='published')
        else:
            # Вкладка "На утверждении/Черновики"
            if user.role == 'teacher':
                # Педагог видит только свои конкурсы со статусом pending или draft
                queryset = queryset.filter(
                    created_by=user,
                    status__in=['pending', 'draft']
                )
            else:
                # Методист/админ видит все конкурсы со статусом pending или draft
                queryset = queryset.filter(status__in=['pending', 'draft'])

        # Остальные фильтры
        level = self.request.GET.get('level')
        search = self.request.GET.get('search')

        if level:
            queryset = queryset.filter(level=level)
        if search:
            queryset = queryset.filter(
                Q(name__iregex=search) |
                Q(description__iregex=search)
            )

        # Сортировка
        sort_by = self.request.GET.get('sort', 'name')
        sort_order = self.request.GET.get('order', 'asc')

        allowed_sort_fields = ['name', 'level', 'application_deadline', 'result_date', 'created_at', 'sort_order']
        if sort_by not in allowed_sort_fields:
            sort_by = 'name'

        if sort_order == 'desc':
            queryset = queryset.order_by(f'-{sort_by}')
        else:
            queryset = queryset.order_by(sort_by)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['levels'] = Event.LEVEL_CHOICES
        context['current_level'] = self.request.GET.get('level', '')
        context['current_search'] = self.request.GET.get('search', '')
        context['current_sort'] = self.request.GET.get('sort', 'name')
        context['current_order'] = self.request.GET.get('order', 'asc')
        context['current_status'] = self.request.GET.get('status', 'published')

        # Счётчики для вкладок
        # Опубликованные (все видят одинаково)
        context['published_count'] = Event.objects.filter(status='published').count()

        if user.role == 'teacher':
            # Для педагога: сколько его конкурсов на утверждении/черновиках
            context['pending_count'] = Event.objects.filter(
                created_by=user, status__in=['pending', 'draft']
            ).count()
        else:
            # Для методиста/админа: сколько всего конкурсов на утверждении/черновиках
            context['pending_count'] = Event.objects.filter(status__in=['pending', 'draft']).count()

        return context


# apps/events/views.py (исправляем EventDetailView)
class EventDetailView(LoginRequiredMixin, DetailView):
    """Детали конкурса"""
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object

        # Получаем статус для возврата на ту же вкладку
        context['return_status'] = self.request.GET.get('status', 'published')

        # Получаем участников конкурса
        from ..participation.models import Participation
        from ..children.models import Child, StudioEnrollment, Teacher, Studio

        participants = Participation.objects.filter(
            event=event
        ).select_related(
            'child', 'enrollment__studio', 'enrollment__teacher', 'result_type'
        ).order_by('child__fio')

        context['participants'] = participants
        context['participants_count'] = participants.count()

        # Для фильтров и статистики
        user = self.request.user

        # Проверяем права доступа
        has_access = False
        if hasattr(user, 'role'):
            if user.role in ['methodist', 'admin']:
                has_access = True
            elif user.role == 'teacher':
                try:
                    teacher = Teacher.objects.get(user=user)
                    # Проверяем, есть ли у педагога доступ к этому конкурсу через участников
                    teacher_participants = participants.filter(enrollment__teacher=teacher)
                    if teacher_participants.exists():
                        has_access = True
                except Teacher.DoesNotExist:
                    has_access = False
                except Exception:
                    has_access = False
            else:
                has_access = False
        else:
            has_access = False

        context['has_access'] = has_access

        # Статистика по результатам
        from collections import Counter
        result_stats = Counter()
        for participant in participants:
            if participant.result_type:
                result_stats[participant.result_type.name] += 1
            elif participant.custom_result:
                result_stats[participant.custom_result] += 1
            else:
                result_stats['Без результата'] += 1

        context['result_stats'] = dict(result_stats)

        # Статистика по студиям
        studio_stats = {}
        for participant in participants:
            studio_name = participant.enrollment.studio.name
            if studio_name in studio_stats:
                studio_stats[studio_name] += 1
            else:
                studio_stats[studio_name] = 1

        context['studio_stats'] = studio_stats

        print(f"DEBUG: Найдено участников: {participants.count()}")
        print(f"DEBUG: Участники: {[p.child.fio for p in participants]}")

        return context


class EventCreateView(LoginRequiredMixin, CreateView):
    """Создание конкурса"""
    model = Event
    template_name = 'events/event_form.html'
    fields = ['name', 'direction', 'level', 'application_deadline',
              'result_date', 'is_active', 'participation_format', 'sort_order']
    success_url = reverse_lazy('events:list')

    def dispatch(self, request, *args, **kwargs):
        # Педагоги тоже могут создавать конкурсы (на утверждение)
        if request.user.role not in ['teacher', 'methodist', 'admin']:
            messages.error(request, 'Доступ только для педагогов, методистов и администраторов')
            return HttpResponseRedirect(reverse_lazy('dashboard:home'))
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        # Педагоги = на утверждение, методисты/админы = опубликован
        if self.request.user.role == 'teacher':
            form.instance.status = 'pending'
        else:
            form.instance.status = 'published'
        messages.success(self.request, 'Конкурс успешно добавлен.')
        return super().form_valid(form)

    def get_initial(self):
        initial = super().get_initial()
        initial['sort_order'] = 3
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import CompetitionDirection
        context['directions'] = CompetitionDirection.objects.all().order_by('sort_order')
        return context


class EventUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование конкурса"""
    model = Event
    template_name = 'events/event_form.html'
    fields = ['name', 'direction', 'level', 'application_deadline',
              'result_date', 'is_active', 'participation_format', 'sort_order']
    success_url = reverse_lazy('events:list')

    def get_success_url(self):
        # Получаем статус из GET параметра
        status = self.request.GET.get('status', 'published')
        # Возвращаемся на ту же вкладку
        return f"{reverse_lazy('events:list')}?status={status}"


    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        user = self.request.user

        # Для методистов/админов добавляем поле status
        if user.role in ['methodist', 'admin']:
            form.fields['status'] = forms.ChoiceField(
                choices=Event.STATUS_CHOICES,
                initial=self.object.status,
                label='Статус',
                required=True
            )
        else:
            # Для педагогов статус не показываем
            if 'status' in form.fields:
                del form.fields['status']

        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import CompetitionDirection
        context['directions'] = CompetitionDirection.objects.all().order_by('sort_order')
        return context



    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        user = request.user

        if user.role == 'teacher':
            if obj.created_by != user or obj.status not in ['pending', 'draft']:
                messages.error(request, 'Вы можете редактировать только свои конкурсы на утверждении или черновики')
                return HttpResponseRedirect(reverse_lazy('dashboard:home'))
        elif user.role not in ['methodist', 'admin']:
            messages.error(request, 'Доступ только для педагогов, методистов и администраторов')
            return HttpResponseRedirect(reverse_lazy('dashboard:home'))

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Сохраняем статус, если он был в форме
        if 'status' in form.cleaned_data:
            self.object.status = form.cleaned_data['status']
            self.object.save()
        messages.success(self.request, 'Конкурс успешно обновлён.')
        return super().form_valid(form)


class EventDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление конкурса"""
    model = Event
    template_name = 'events/event_confirm_delete.html'
    success_url = reverse_lazy('events:list')

    def get_success_url(self):
        # Получаем статус из GET параметра
        status = self.request.GET.get('status', 'published')
        # Возвращаемся на ту же вкладку
        return f"{reverse_lazy('events:list')}?status={status}"


    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        user = request.user

        if user.role == 'teacher':
            # Педагог может удалять только свои конкурсы со статусом pending или draft
            if obj.created_by != user or obj.status not in ['pending', 'draft']:
                messages.error(request, 'Вы можете удалять только свои конкурсы на утверждении или черновики')
                return HttpResponseRedirect(reverse_lazy('dashboard:home'))
        elif user.role not in ['methodist', 'admin']:
            messages.error(request, 'Доступ только для педагогов, методистов и администраторов')
            return HttpResponseRedirect(reverse_lazy('dashboard:home'))

        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.can_be_deleted():
            messages.error(request, f'Невозможно удалить конкурс "{self.object.name}", так как есть участия детей.')
            return HttpResponseRedirect(reverse_lazy('events:detail', kwargs={'pk': self.object.pk}))
        messages.success(request, f'Конкурс "{self.object.name}" успешно удалён.')
        return super().delete(request, *args, **kwargs)



# Views для типов результатов
class ResultTypeListView(LoginRequiredMixin, ListView):
    """Список типов результатов"""
    model = ResultType
    template_name = 'events/result_type_list.html'
    context_object_name = 'result_types'
    paginate_by = 50


class ResultTypeDetailView(LoginRequiredMixin, DetailView):
    """Детали типа результата"""
    model = ResultType
    template_name = 'events/result_type_detail.html'
    context_object_name = 'result_type'


class ResultTypeCreateView(LoginRequiredMixin, CreateView):
    """Создание типа результата"""
    model = ResultType
    template_name = 'events/result_type_form.html'
    fields = ['code', 'name', 'description']
    success_url = reverse_lazy('events:result_type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Тип результата успешно добавлен.')
        return super().form_valid(form)


class ResultTypeUpdateView(LoginRequiredMixin, UpdateView):
    """Редактирование типа результата"""
    model = ResultType
    template_name = 'events/result_type_form.html'
    fields = ['code', 'name', 'description']
    success_url = reverse_lazy('events:result_type_list')

    def form_valid(self, form):
        messages.success(self.request, 'Тип результата успешно обновлен.')
        return super().form_valid(form)


class ResultTypeDeleteView(LoginRequiredMixin, DeleteView):
    """Удаление типа результата"""
    model = ResultType
    template_name = 'events/result_type_confirm_delete.html'
    success_url = reverse_lazy('events:result_type_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, f'Тип результата {self.get_object().name} успешно удален.')
        return super().delete(request, *args, **kwargs)


class AddParticipantsView(LoginRequiredMixin, View):
    """Добавление участников в конкурс"""

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)

        # Получаем доступных детей в зависимости от роли пользователя
        from ..children.models import StudioEnrollment, Teacher
        from ..participation.models import Participation
        from datetime import date

        user = request.user
        if hasattr(user, 'role') and user.role == 'teacher':
            try:
                teacher = Teacher.objects.get(user=user)
                # Только дети этого педагога
                enrollments = StudioEnrollment.objects.filter(teacher=teacher).select_related('child', 'studio')
            except Teacher.DoesNotExist:
                enrollments = StudioEnrollment.objects.none()
        else:
            # Для методистов и админов - все дети
            enrollments = StudioEnrollment.objects.select_related('child', 'studio')

        # ИСКЛЮЧАЕМ ЗАПИСИ, которые уже участвуют в этом конкурсе (проверка по enrollment)
        existing_participations = Participation.objects.filter(event=event).values_list('enrollment_id', flat=True)
        available_enrollments = enrollments.exclude(id__in=existing_participations)

        # Получаем все типы результатов
        from .models import ResultType
        result_types = ResultType.objects.all().order_by('code')

        context = {
            'event': event,
            'enrollments': available_enrollments,
            'result_types': result_types,
            'today': date.today(),
            'page_title': f'Добавление участников в конкурс "{event.name}"'
        }
        return render(request, 'events/add_participants.html', context)

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)

        # Получаем выбранных участников
        enrollment_ids = request.POST.getlist('participants')
        report_date = request.POST.get('report_date')
        results_data = request.POST.get('results_data')

        if not enrollment_ids:
            messages.error(request, 'Не выбраны участники')
            return HttpResponseRedirect(reverse_lazy('events:add_participants', kwargs={'pk': pk}))

        if not report_date:
            messages.error(request, 'Не указана дата отчета')
            return HttpResponseRedirect(reverse_lazy('events:add_participants', kwargs={'pk': pk}))

        # Преобразуем дату
        from datetime import datetime
        try:
            report_date = datetime.strptime(report_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Неверный формат даты')
            return HttpResponseRedirect(reverse_lazy('events:add_participants', kwargs={'pk': pk}))

        # Парсим JSON с результатами
        import json
        results_dict = {}
        if results_data:
            try:
                results_dict = json.loads(results_data)
            except json.JSONDecodeError:
                messages.error(request, 'Ошибка при обработке данных результатов')
                return HttpResponseRedirect(reverse_lazy('events:add_participants', kwargs={'pk': pk}))

        # Получаем записи детей
        from ..children.models import StudioEnrollment
        enrollments = StudioEnrollment.objects.filter(id__in=enrollment_ids)

        # Получаем все типы результатов для контекста
        from .models import ResultType
        result_types = ResultType.objects.all().order_by('code')

        created_count = 0
        errors = []

        for enrollment in enrollments:
            try:
                from ..participation.models import Participation

                # Получаем результат из словаря (может быть пустым)
                result_type_id = results_dict.get(str(enrollment.id))
                result_type = None

                # Если результат указан, пытаемся найти его
                if result_type_id:
                    try:
                        result_type = ResultType.objects.get(id=result_type_id)
                    except ResultType.DoesNotExist:
                        # Если тип результата не найден, просто оставляем result_type = None
                        pass

                # ПРОВЕРКА ИЗМЕНЕНА: проверяем участие по записи в студии, а не по ребенку
                if Participation.objects.filter(enrollment=enrollment, event=event).exists():
                    errors.append(
                        f'Ребенок {enrollment.child.fio} уже участвует в этом конкурсе через студию "{enrollment.studio.name}"')
                    continue

                # Создаем участие (результат может быть None)
                Participation.objects.create(
                    child=enrollment.child,
                    enrollment=enrollment,
                    event=event,
                    report_date=report_date,
                    result_type=result_type,  # Может быть None
                    created_by=request.user
                )
                created_count += 1

            except Exception as e:
                error_msg = f'Ошибка при добавлении {enrollment.child.fio}: {str(e)}'
                errors.append(error_msg)
                print(f"DEBUG: {error_msg}")

        # Показываем результаты операции
        if created_count > 0:
            messages.success(
                request,
                f'Успешно добавлено {created_count} участников в конкурс "{event.name}"'
            )

        # Показываем ошибки, если они есть
        for error in errors:
            messages.error(request, error)

        # Если есть ошибки или не было создано ни одной записи, возвращаем на страницу с формой
        if errors or created_count == 0:
            context = {
                'event': event,
                'enrollments': self.get_available_enrollments(request.user, event),
                'result_types': result_types,
                'today': timezone.now().date(),
                'page_title': f'Добавление участников в конкурс "{event.name}"'
            }
            return render(request, 'events/add_participants.html', context)

        return HttpResponseRedirect(reverse_lazy('events:detail', kwargs={'pk': pk}))

    def get_available_enrollments(self, user, event):
        """Вспомогательный метод для получения доступных записей"""
        from ..children.models import StudioEnrollment, Teacher
        from ..participation.models import Participation

        if hasattr(user, 'role') and user.role == 'teacher':
            try:
                teacher = Teacher.objects.get(user=user)
                enrollments = StudioEnrollment.objects.filter(teacher=teacher).select_related('child', 'studio')
            except Teacher.DoesNotExist:
                enrollments = StudioEnrollment.objects.none()
        else:
            enrollments = StudioEnrollment.objects.select_related('child', 'studio')

        # ИСКЛЮЧАЕМ записи, которые уже участвуют в конкурсе (проверка по enrollment)
        existing_participations = Participation.objects.filter(event=event).values_list('enrollment_id', flat=True)
        return enrollments.exclude(id__in=existing_participations)

    def get_success_url(self):
        status = self.request.GET.get('status', 'published')
        return f"{reverse_lazy('events:detail', kwargs={'pk': self.kwargs['pk']})}?status={status}"


# apps/events/views.py (добавляем новый view)
class EventParticipantsView(LoginRequiredMixin, DetailView):
    """Просмотр конкурса с участниками"""
    model = Event
    template_name = 'events/event_participants.html'
    context_object_name = 'event'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Получаем участников конкурса
        from ..participation.models import Participation
        participants = Participation.objects.filter(
            event=self.object
        ).select_related(
            'child', 'enrollment__studio', 'enrollment__teacher', 'result_type'
        ).order_by('child__fio')

        context['participants'] = participants
        context['participants_count'] = participants.count()
        context['page_title'] = f'Участники конкурса "{self.object.name}"'

        return context


# apps/events/views.py (исправляем импорты в AddSingleParticipantView)
class AddSingleParticipantView(LoginRequiredMixin, View):
    """Добавление одного участника в конкурс"""

    def get(self, request):
        # Получаем параметры из запроса
        enrollment_id = request.GET.get('enrollment')
        event_id = request.GET.get('event')

        if not enrollment_id:
            messages.error(request, 'Не указана запись в студию')
            return HttpResponseRedirect(reverse('children:studio_children'))

        # Проверяем, существует ли запись
        from ..children.models import StudioEnrollment
        try:
            enrollment = StudioEnrollment.objects.get(id=enrollment_id)
        except StudioEnrollment.DoesNotExist:
            messages.error(request, 'Запись в студию не найдена')
            return HttpResponseRedirect(reverse('children:studio_children'))

        # Получаем список доступных конкурсов
        from ..events.models import Event, ResultType  # Исправленный импорт
        events = Event.objects.filter(is_active=True).order_by('name')
        result_types = ResultType.objects.all().order_by('name')  # Правильный импорт

        context = {
            'enrollment': enrollment,
            'events': events,
            'result_types': result_types,  # Добавляем типы результатов
            'selected_event': event_id,
            'page_title': 'Регистрация участия в конкурсе'
        }
        return render(request, 'events/add_single_participant.html', context)

    def post(self, request):
        # Получаем данные из формы
        enrollment_id = request.POST.get('enrollment')
        event_id = request.POST.get('event')
        report_date = request.POST.get('report_date')
        result_type_id = request.POST.get('result_type')
        custom_result = request.POST.get('custom_result')

        if not all([enrollment_id, event_id, report_date]):
            messages.error(request, 'Заполните все обязательные поля')
            return HttpResponseRedirect(f"{reverse('events:add_single_participant')}?enrollment={enrollment_id}")

        # Получаем объекты
        from ..children.models import StudioEnrollment
        from ..events.models import Event, ResultType  # Исправленные импорты
        from ..participation.models import Participation  # Правильный импорт
        from datetime import datetime

        try:
            enrollment = StudioEnrollment.objects.get(id=enrollment_id)
            event = Event.objects.get(id=event_id)

            # Проверяем, не участвует ли уже ребенок в этом конкурсе
            if Participation.objects.filter(child=enrollment.child, event=event).exists():
                messages.error(
                    request,
                    f'Ребенок {enrollment.child.fio} уже участвует в конкурсе "{event.name}"'
                )
                return HttpResponseRedirect(f"{reverse('events:add_single_participant')}?enrollment={enrollment_id}")

            # Создаем участие
            result_type = None
            if result_type_id:
                result_type = ResultType.objects.get(id=result_type_id)  # Правильный импорт

            report_date_parsed = datetime.strptime(report_date, '%Y-%m-%d').date()

            Participation.objects.create(
                child=enrollment.child,
                enrollment=enrollment,
                event=event,
                result_type=result_type,
                custom_result=custom_result,
                report_date=report_date_parsed,
                created_by=request.user
            )

            messages.success(
                request,
                f'Ребенок {enrollment.child.fio} успешно зарегистрирован в конкурсе "{event.name}"'
            )

            # Перенаправляем на карточку записи в студию
            return HttpResponseRedirect(reverse('children:enrollment_detail', kwargs={'pk': enrollment.pk}))

        except Exception as e:
            messages.error(request, f'Ошибка при регистрации участия: {str(e)}')
            return HttpResponseRedirect(f"{reverse('events:add_single_participant')}?enrollment={enrollment_id}")


# apps/events/views.py (обновляем EventUploadView с отладкой)
# apps/participation/views.py (обновляем EventUploadView)
# apps/events/views.py (обновляем EventUploadView с отладкой)
class EventUploadView(LoginRequiredMixin, FormView):
    """Загрузка данных конкурсов из Excel"""
    template_name = 'events/event_upload.html'
    success_url = reverse_lazy('events:list')

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ['methodist', 'admin']:
            messages.error(request, 'Доступ только для методистов и администраторов')
            return HttpResponseRedirect(reverse_lazy('dashboard:home'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        print("DEBUG: EventUploadView GET запрос")
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        print("DEBUG: EventUploadView POST запрос начат")
        print(f"DEBUG: FILES в запросе: {list(request.FILES.keys())}")

        # Проверяем, загружен ли файл
        if 'excel_file' not in request.FILES:
            print("DEBUG: Файл excel_file не найден в запросе")
            messages.error(request, 'Пожалуйста, выберите Excel файл для загрузки.')
            return render(request, self.template_name)

        excel_file = request.FILES['excel_file']
        print(f"DEBUG: Загружен файл: {excel_file.name}, размер: {excel_file.size} байт")

        # Проверяем расширение файла
        if not excel_file.name.endswith(('.xlsx', '.xls')):
            print(f"DEBUG: Неправильное расширение файла: {excel_file.name}")
            messages.error(request, 'Пожалуйста, загрузите файл в формате Excel (.xlsx или .xls).')
            return render(request, self.template_name)

        try:
            print("DEBUG: Начинаем чтение Excel файла")
            # Читаем Excel файл
            df = pd.read_excel(excel_file, header=0)
            print(f"DEBUG: Файл прочитан успешно. Форма DataFrame: {df.shape}")
            print(f"DEBUG: Колонки в файле: {list(df.columns)}")

            # Проверяем, есть ли данные
            if df.empty:
                print("DEBUG: Excel файл пустой")
                messages.error(request, 'Excel файл пустой.')
                return render(request, self.template_name)

            # Получаем настройки соответствия полей
            name_column = request.POST.get('name_column', 'name')
            description_column = request.POST.get('description_column', 'description')
            level_column = request.POST.get('level_column', 'level')
            deadline_column = request.POST.get('deadline_column', 'application_deadline')
            result_date_column = request.POST.get('result_date_column', 'result_date')

            print(f"DEBUG: Настройки колонок:")
            print(f"  name_column: {name_column}")
            print(f"  description_column: {description_column}")
            print(f"  level_column: {level_column}")
            print(f"  deadline_column: {deadline_column}")
            print(f"  result_date_column: {result_date_column}")

            # Проверяем, есть ли необходимые колонки
            required_columns = [name_column, level_column]
            missing_columns = [col for col in required_columns if col not in df.columns]
            print(f"DEBUG: Обязательные колонки: {required_columns}")
            print(f"DEBUG: Отсутствующие колонки: {missing_columns}")

            if missing_columns:
                messages.error(
                    request,
                    f'В Excel файле отсутствуют необходимые колонки: {", ".join(missing_columns)}'
                )
                print(f"DEBUG: Ошибка - отсутствуют колонки: {missing_columns}")
                return render(request, self.template_name)

            # Загружаем данные
            created_count = 0
            updated_count = 0
            errors = []

            print("DEBUG: Начинаем обработку строк")
            # Обрабатываем строки
            for index, row in df.iterrows():
                print(f"DEBUG: Обработка строки {index}")
                try:
                    # Получаем данные из строки
                    name = str(row[name_column]).strip() if pd.notna(row[name_column]) else ''
                    description = str(row[description_column]).strip() if pd.notna(row[description_column]) and row[
                        description_column] else name
                    level_code = str(row[level_column]).strip() if pd.notna(row[level_column]) else ''
                    application_deadline = row[deadline_column] if deadline_column in df.columns and pd.notna(
                        row[deadline_column]) else None
                    result_date = row[result_date_column] if result_date_column in df.columns and pd.notna(
                        row[result_date_column]) else None

                    print(f"DEBUG: Данные строки {index}:")
                    print(f"  name: '{name}'")
                    print(f"  description: '{description}'")
                    print(f"  level_code: '{level_code}'")
                    print(f"  application_deadline: {application_deadline}")
                    print(f"  result_date: {result_date}")

                    # Пропускаем пустые строки
                    if not name:
                        print(f"DEBUG: Пропущена пустая строка {index}")
                        continue

                    # Преобразуем даты, если они есть
                    if application_deadline is not None:
                        if isinstance(application_deadline, pd.Timestamp):
                            application_deadline = application_deadline.date()
                            print(f"DEBUG: Преобразована дата подачи: {application_deadline}")
                        elif isinstance(application_deadline, str):
                            # Пытаемся преобразовать строку в дату
                            try:
                                from datetime import datetime
                                application_deadline = datetime.strptime(application_deadline, '%d.%m.%Y').date()
                                print(f"DEBUG: Преобразована строка даты подачи: {application_deadline}")
                            except Exception as date_error:
                                print(f"DEBUG: Ошибка преобразования даты подачи: {date_error}")
                                application_deadline = None

                    if result_date is not None:
                        if isinstance(result_date, pd.Timestamp):
                            result_date = result_date.date()
                            print(f"DEBUG: Преобразована дата результатов: {result_date}")
                        elif isinstance(result_date, str):
                            # Пытаемся преобразовать строку в дату
                            try:
                                from datetime import datetime
                                result_date = datetime.strptime(result_date, '%d.%m.%Y').date()
                                print(f"DEBUG: Преобразована строка даты результатов: {result_date}")
                            except Exception as date_error:
                                print(f"DEBUG: Ошибка преобразования даты результатов: {date_error}")
                                result_date = None

                    # Преобразуем уровень в код
                    level_mapping = {
                        'Центровский': 'center',
                        'Городской': 'city',
                        'Районный': 'district',
                        'Республиканский': 'republic',
                        'Региональный': 'regional',
                        'Межрегиональный': 'interregional',
                        'Всероссийский': 'allrussian',
                        'Международный': 'international',
                        # Английские варианты
                        'Center': 'center',
                        'City': 'city',
                        'District': 'district',
                        'Republic': 'republic',
                        'Regional': 'regional',
                        'Interregional': 'interregional',
                        'All-Russian': 'allrussian',
                        'International': 'international',
                        # Сокращения
                        'Ц': 'center',
                        'Г': 'city',
                        'Р': 'district',
                        'РП': 'republic',
                        'РГ': 'regional',
                        'МР': 'interregional',
                        'ВР': 'allrussian',
                        'М': 'international',
                    }

                    level = level_mapping.get(level_code, 'center')  # По умолчанию центровский
                    print(f"DEBUG: Преобразованный уровень: {level} (из '{level_code}')")

                    # Создаем или обновляем конкурс
                    print(f"DEBUG: Создание/обновление конкурса: {name}")
                    event, created = Event.objects.get_or_create(
                        name=name,
                        defaults={
                            'description': description,
                            'level': level,
                            'application_deadline': application_deadline,
                            'result_date': result_date,
                            'is_active': True,
                            'sort_order': 0,
                            'created_by': request.user,
                        }
                    )

                    if created:
                        created_count += 1
                        print(f"DEBUG: Создан новый конкурс: {name}")
                    else:
                        # Обновляем существующий конкурс
                        event.description = description
                        event.level = level
                        event.application_deadline = application_deadline
                        event.result_date = result_date
                        event.updated_at = timezone.now()
                        event.save()
                        updated_count += 1
                        print(f"DEBUG: Обновлен конкурс: {name}")

                except Exception as e:
                    error_msg = f'Ошибка в строке {index + 1}: {str(e)}'
                    print(f"DEBUG: {error_msg}")
                    errors.append(error_msg)

            print(
                f"DEBUG: Завершена обработка. Создано: {created_count}, Обновлено: {updated_count}, Ошибок: {len(errors)}")

            # Показываем результаты
            if created_count > 0:
                messages.success(
                    request,
                    f'Успешно создано {created_count} конкурсов.'
                )
                print(f"DEBUG: Сообщение об успешном создании: {created_count} конкурсов")

            if updated_count > 0:
                messages.success(
                    request,
                    f'Успешно обновлено {updated_count} конкурсов.'
                )
                print(f"DEBUG: Сообщение об успешном обновлении: {updated_count} конкурсов")

            if errors:
                for error in errors:
                    messages.error(request, error)
                    print(f"DEBUG: Сообщение об ошибке: {error}")

            if created_count == 0 and updated_count == 0 and not errors:
                messages.info(request, 'Нет данных для загрузки.')
                print("DEBUG: Нет данных для загрузки")

        except Exception as e:
            error_msg = f'Ошибка при чтении Excel файла: {str(e)}'
            print(f"DEBUG: {error_msg}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            messages.error(request, error_msg)
            return render(request, self.template_name)

        print("DEBUG: Перенаправление на список конкурсов")
        return HttpResponseRedirect(self.success_url)
