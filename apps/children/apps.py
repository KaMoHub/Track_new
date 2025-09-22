# apps/children/apps.py
from django.apps import AppConfig

class ChildrenConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.children'
    verbose_name = 'Управление детьми'
