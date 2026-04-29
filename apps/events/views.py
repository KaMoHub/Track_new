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
from datetime import datetime

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


class EventUploadView(LoginRequiredMixin, FormView):
    """Загрузка данных конкурсов из Excel с предварительным логом"""
    template_name = 'events/event_upload.html'
    success_url = reverse_lazy('events:list')

    def dispatch(self, request, *args, **kwargs):
        if request.user.role not in ['methodist', 'admin']:
            messages.error(request, 'Доступ только для методистов и администраторов')
            return HttpResponseRedirect(reverse_lazy('dashboard:home'))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        request.session.pop('upload_preview_data', None)
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        if 'confirm' in request.POST:
            return self.apply_changes(request)
        return self.analyze_file(request)

    def analyze_file(self, request):
        """Анализ Excel файла, формирование лога"""
        if 'excel_file' not in request.FILES:
            messages.error(request, 'Пожалуйста, выберите Excel файл для загрузки.')
            return render(request, self.template_name)

        excel_file = request.FILES['excel_file']
        upload_mode = request.POST.get('upload_mode', 'add')

        if not excel_file.name.endswith(('.xlsx', '.xls')):
            messages.error(request, 'Пожалуйста, загрузите файл в формате Excel (.xlsx или .xls).')
            return render(request, self.template_name)

        try:
            df = pd.read_excel(excel_file, header=0)
            if df.empty:
                messages.error(request, 'Excel файл пустой.')
                return render(request, self.template_name)

            # Определяем колонки
            npp_col = request.POST.get('npp_column', 'N п/п')
            name_col = request.POST.get('name_column', 'Название мероприятия')
            level_col = request.POST.get('level_column', 'Уровень')
            deadline_col = request.POST.get('deadline_column', 'application_deadline')
            result_date_col = request.POST.get('result_date_column', 'result_date')
            direction_col = request.POST.get('direction_column', 'Направление мероприятия')
            format_col = request.POST.get('format_column', 'participation_format')
            priority_col = request.POST.get('priority_column', 'Приоритет')
            id_col = request.POST.get('id_column', 'id') if upload_mode == 'update' else None

            # Проверка обязательных колонок
            required = [name_col, level_col]
            missing = [c for c in required if c not in df.columns]
            if missing:
                messages.error(request, f'Отсутствуют обязательные колонки: {", ".join(missing)}')
                return render(request, self.template_name)

            if upload_mode == 'update' and id_col and id_col not in df.columns:
                messages.error(request, f'В режиме обновления требуется колонка "{id_col}" с ID конкурсов.')
                return render(request, self.template_name)

            # Маппинг уровней
            level_mapping = {
                'Центровский': 'center', 'Городской': 'city', 'Районный': 'district',
                'Республиканский': 'republic', 'Региональный': 'regional',
                'Межрегиональный': 'interregional', 'Всероссийский': 'allrussian',
                'Международный': 'international','Высший уровень': 'allrussian',
                'Center': 'center', 'City': 'city', 'District': 'district',
                'Republic': 'republic', 'Regional': 'regional', 'Interregional': 'interregional',
                'All-Russian': 'allrussian', 'International': 'international'
            }

            # Маппинг направлений
            from .models import CompetitionDirection
            direction_mapping = {}
            for d in CompetitionDirection.objects.all():
                direction_mapping[d.name.lower()] = d.id
                direction_mapping[d.code.lower()] = d.id

            # Маппинг форматов
            format_mapping = {
                'очная': 'offline', 'очно-дистанционная': 'mixed', 'заочная': 'online'
            }

            preview_data = []
            errors = []
            index = 0

            for idx, row in df.iterrows():
                index += 2

                # Формируем полное название из номера и названия
                npp = str(row[npp_col]).strip() if npp_col in df.columns and pd.notna(row[npp_col]) else ''
                name = str(row[name_col]).strip() if pd.notna(row[name_col]) else ''
                if not name:
                    continue
                full_name = f"{npp} {name}" if npp else name

                level_raw = str(row[level_col]).strip() if pd.notna(row[level_col]) else ''
                level = level_mapping.get(level_raw, 'center')

                # Обработка дат
                deadline = None
                if deadline_col in df.columns and pd.notna(row[deadline_col]):
                    try:
                        if isinstance(row[deadline_col], pd.Timestamp):
                            deadline = row[deadline_col].date()
                        else:
                            deadline = datetime.strptime(str(row[deadline_col]), '%d.%m.%Y').date()
                    except:
                        errors.append(f'Строка {index}: ошибка преобразования даты подачи')

                result_date = None
                if result_date_col in df.columns and pd.notna(row[result_date_col]):
                    try:
                        if isinstance(row[result_date_col], pd.Timestamp):
                            result_date = row[result_date_col].date()
                        else:
                            result_date = datetime.strptime(str(row[result_date_col]), '%d.%m.%Y').date()
                    except:
                        errors.append(f'Строка {index}: ошибка преобразования даты результатов')

                # Приоритет
                priority = None
                if priority_col in df.columns and pd.notna(row[priority_col]):
                    try:
                        priority = int(row[priority_col])
                    except:
                        errors.append(f'Строка {index}: неверный формат приоритета (должно быть число)')

                # Направление
                direction_id = None
                if direction_col in df.columns and pd.notna(row[direction_col]):
                    dir_raw = str(row[direction_col]).strip().lower()
                    direction_id = direction_mapping.get(dir_raw)

                # Формат участия
                participation_format = None
                if format_col in df.columns and pd.notna(row[format_col]):
                    fmt_raw = str(row[format_col]).strip().lower()
                    participation_format = format_mapping.get(fmt_raw)

                # Поиск существующего конкурса
                existing_event = None
                row_data = {
                    'row': index,
                    'name': full_name,
                    'level_new': level,
                    'deadline_new': deadline,
                    'result_date_new': result_date,
                    'direction_new': direction_id,
                    'format_new': participation_format,
                    'priority_new': priority,
                }

                if upload_mode == 'update' and id_col:
                    try:
                        event_id = int(row[id_col])
                        existing_event = Event.objects.filter(id=event_id).first()
                        row_data['id'] = event_id
                    except:
                        errors.append(f'Строка {index}: неверный формат ID')
                else:
                    existing_event = Event.objects.filter(name=full_name).first()
                    if existing_event:
                        row_data['id'] = existing_event.id

                if existing_event:
                    changes = []
                    if existing_event.level != level and level != 'center':
                        changes.append(f'уровень: {existing_event.level} → {level}')
                        row_data['level_old'] = existing_event.level

                    if deadline and existing_event.application_deadline != deadline:
                        changes.append(f'срок подачи: {existing_event.application_deadline} → {deadline}')
                        row_data['deadline_old'] = existing_event.application_deadline

                    if result_date and existing_event.result_date != result_date:
                        changes.append(f'дата результатов: {existing_event.result_date} → {result_date}')
                        row_data['result_date_old'] = existing_event.result_date

                    if direction_id and existing_event.direction_id != direction_id:
                        old_dir = existing_event.direction.name if existing_event.direction else '—'
                        new_dir = CompetitionDirection.objects.get(id=direction_id).name
                        changes.append(f'направление: {old_dir} → {new_dir}')
                        row_data['direction_old'] = existing_event.direction_id

                    if participation_format and existing_event.participation_format != participation_format:
                        old_fmt = existing_event.get_participation_format_display() or '—'
                        new_fmt = dict(format_mapping).get(participation_format, participation_format)
                        changes.append(f'формат: {old_fmt} → {new_fmt}')
                        row_data['format_old'] = existing_event.participation_format

                    if priority and existing_event.sort_order != priority:
                        changes.append(f'приоритет: {existing_event.sort_order} → {priority}')
                        row_data['priority_old'] = existing_event.sort_order

                    row_data['changes'] = changes
                    row_data['action'] = 'update' if changes else 'skip'
                    row_data['changes_count'] = len(changes)
                else:
                    row_data['action'] = 'create'
                    row_data['changes_count'] = 1
                    row_data['changes'] = ['новый конкурс']

                preview_data.append(row_data)

            session_data = {
                'preview': preview_data,
                'errors': errors,
                'upload_mode': upload_mode,
                'original_file': excel_file.name,
                'npp_col': npp_col,
                'name_col': name_col,
                'level_col': level_col,
                'deadline_col': deadline_col,
                'result_date_col': result_date_col,
                'direction_col': direction_col,
                'format_col': format_col,
                'priority_col': priority_col,
                'id_col': id_col,
            }
            request.session['upload_preview_data'] = session_data

            return render(request, 'events/event_upload_preview.html', {
                'preview': preview_data,
                'errors': errors,
                'mode': upload_mode,
                'filename': excel_file.name,
                'has_changes': any(p['changes_count'] > 0 for p in preview_data)
            })

        except Exception as e:
            messages.error(request, f'Ошибка при чтении файла: {str(e)}')
            return render(request, self.template_name)

    def apply_changes(self, request):
        """Применение подтверждённых изменений"""
        session_data = request.session.get('upload_preview_data')
        if not session_data:
            messages.error(request, 'Данные не найдены. Попробуйте загрузить файл заново.')
            return HttpResponseRedirect(reverse_lazy('events:upload'))

        preview = session_data.get('preview', [])
        upload_mode = session_data.get('upload_mode', 'add')

        from .models import CompetitionDirection

        created = 0
        updated = 0
        skipped = 0
        errors = []

        for item in preview:
            if item['action'] == 'skip':
                skipped += 1
                continue

            if item['action'] == 'create' and upload_mode == 'add':
                try:
                    event = Event.objects.create(
                        name=item['name'],
                        level=item['level_new'],
                        application_deadline=item['deadline_new'],
                        result_date=item['result_date_new'],
                        direction_id=item['direction_new'] if item['direction_new'] else None,
                        participation_format=item['format_new'],
                        sort_order=item['priority_new'] or 3,
                        is_active=True,
                        status='published',
                        created_by=request.user
                    )
                    created += 1
                except Exception as e:
                    errors.append(f'{item["name"]}: {str(e)}')

            elif item['action'] == 'update' and upload_mode == 'update':
                try:
                    event = Event.objects.get(id=item['id'])
                    changed = False

                    if 'level_old' in item and item['level_new'] != 'center':
                        event.level = item['level_new']
                        changed = True
                    if 'deadline_old' in item and item['deadline_new']:
                        event.application_deadline = item['deadline_new']
                        changed = True
                    if 'result_date_old' in item and item['result_date_new']:
                        event.result_date = item['result_date_new']
                        changed = True
                    if 'direction_old' in item and item['direction_new']:
                        event.direction_id = item['direction_new']
                        changed = True
                    if 'format_old' in item and item['format_new']:
                        event.participation_format = item['format_new']
                        changed = True
                    if 'priority_old' in item and item['priority_new']:
                        event.sort_order = item['priority_new']
                        changed = True

                    if changed:
                        event.save()
                        updated += 1
                    else:
                        skipped += 1
                except Exception as e:
                    errors.append(f'ID {item["id"]}: {str(e)}')

        request.session.pop('upload_preview_data', None)

        if created:
            messages.success(request, f'✅ Создано конкурсов: {created}')
        if updated:
            messages.success(request, f'✅ Обновлено конкурсов: {updated}')
        if skipped:
            messages.info(request, f'⏭️ Пропущено (без изменений): {skipped}')
        if errors:
            for error in errors:
                messages.error(request, error)

        self.save_log_to_file(session_data, created, updated, skipped, errors)

        return HttpResponseRedirect(reverse_lazy('events:list'))

    def save_log_to_file(self, session_data, created, updated, skipped, errors):
        """Сохраняет лог загрузки в файл"""
        from datetime import datetime
        import os
        from django.conf import settings

        logs_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(logs_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"upload_log_{timestamp}.txt"
        filepath = os.path.join(logs_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"ЛОГ ЗАГРУЗКИ КОНКУРСОВ\n")
            f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write(f"Файл: {session_data.get('original_file', 'unknown')}\n")
            f.write(f"Режим: {session_data.get('upload_mode', 'unknown')}\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Создано: {created}\n")
            f.write(f"Обновлено: {updated}\n")
            f.write(f"Пропущено: {skipped}\n")
            f.write(f"Ошибок: {len(errors)}\n\n")

            if errors:
                f.write("ОШИБКИ:\n")
                for error in errors:
                    f.write(f"  - {error}\n")
                f.write("\n")

            f.write("ДЕТАЛИ:\n")
            f.write("-" * 80 + "\n")
            for item in session_data.get('preview', []):
                if item['action'] != 'skip':
                    f.write(f"Строка {item['row']}: {item['action'].upper()} | {item['name']}\n")
                    for ch in item['changes']:
                        if ch != 'новый конкурс':
                            f.write(f"    {ch}\n")
            f.write("-" * 80 + "\n")

        print(f"Лог сохранён: {filepath}")


