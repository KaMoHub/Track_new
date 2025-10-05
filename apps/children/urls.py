# apps/children/urls.py
from django.urls import path
from . import views

app_name = 'children'

urlpatterns = [
    # URLs для детей
    path('', views.ChildListView.as_view(), name='list'),
    path('create/', views.ChildCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ChildDetailView.as_view(), name='detail'),
    path('<int:pk>/update/', views.ChildUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.ChildDeleteView.as_view(), name='delete'),

    # URLs для общего списка детей
    path('child-list/', views.ChildListListView.as_view(), name='child_list'),
    path('child-list/create/', views.ChildListCreateView.as_view(), name='child_list_create'),

    # URLs для направлений
    path('directions/', views.DirectionListView.as_view(), name='direction_list'),
    path('directions/create/', views.DirectionCreateView.as_view(), name='direction_create'),
    path('directions/<int:pk>/update/', views.DirectionCreateView.as_view(), name='direction_update'),
    path('directions/<int:pk>/delete/', views.DirectionDeleteView.as_view(), name='direction_delete'),
    # Для редактирования

    # URLs для студий
    path('studios/', views.StudioListView.as_view(), name='studio_list'),
    path('studios/create/', views.StudioCreateView.as_view(), name='studio_create'),
    path('studios/<int:pk>/update/', views.StudioCreateView.as_view(), name='studio_update'),  # Для редактирования
    path('studios/<int:pk>/delete/', views.StudioDeleteView.as_view(), name='studio_delete'),


    # URLs для педагогов
    path('teachers/', views.TeacherListView.as_view(), name='teacher_list'),
    path('teachers/create/', views.TeacherCreateView.as_view(), name='teacher_create'),
    path('teachers/<int:pk>/delete/', views.TeacherDeleteView.as_view(), name='teacher_delete'),

    # URLs для записей в студии
    path('enrollments/', views.EnrollmentListView.as_view(), name='enrollment_list'),
    path('enrollments/create/', views.EnrollmentCreateView.as_view(), name='enrollment_create'),

    # URLs для работы с записями в студиях
    path('studio-children/', views.StudioChildrenListView.as_view(), name='studio_children'),
    path('studio-children/add/', views.EnrollmentCreateView.as_view(), name='enrollment_create'),
    path('studio-children/<int:pk>/', views.EnrollmentDetailView.as_view(), name='enrollment_detail'),
    path('studio-children/<int:pk>/update/', views.EnrollmentUpdateView.as_view(), name='enrollment_update'),
    path('studio-children/<int:pk>/delete/', views.EnrollmentDeleteView.as_view(), name='enrollment_delete'),

    # URLs для загрузки данных
    path('upload/', views.ChildrenStudioUploadView.as_view(), name='upload'),  # Новый URL


    # apps/children/urls.py
    path('reports/', views.ReportsDashboardView.as_view(), name='reports_dashboard'),
    path('reports/competition/', views.DirectionCompetitionReportView.as_view(), name='competition_report'),
    path('reports/monthly-achievements/', views.MonthlyAchievementsReportView.as_view(), name='monthly_achievements_report'),
    path('reports/semester-achievements/', views.SemesterAchievementsReportView.as_view(), name='semester_achievements_report'),

    path('reports/monthly-stats/', views.MonthlyStatsAPIView.as_view(), name='monthly_stats_api'),
]