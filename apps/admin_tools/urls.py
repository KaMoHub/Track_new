from django.urls import path
from . import views

app_name = 'admin_tools'

urlpatterns = [
    path('', views.admin_dashboard, name='dashboard'),
    path('api/db-structure/', views.db_structure, name='db_structure'),
    path('api/project-structure/', views.project_structure, name='project_structure'),
    path('api/tables/', views.tables_list, name='tables_list'),
    path('api/table-data/<str:table_name>/', views.table_data, name='table_data'),
    path('export/<str:table_name>/', views.export_table_excel, name='export_excel'),
    path('api/children/', views.children_list, name='children_list'),
    path('api/search-links/', views.search_child_links, name='search_links'),
    path('api/delete-child/', views.delete_child, name='delete_child'),
    path('api/replace-links/', views.replace_links, name='replace_links'),

]