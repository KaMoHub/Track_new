from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.contrib.auth import get_user_model
import os


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'Управление пользователями'

    def ready(self):
        # Подключаем сигналы
        try:
            import apps.accounts.signals
        except ImportError:
            pass

        # Подключаем создание суперпользователя
        post_migrate.connect(self.create_superuser, sender=self)

    def create_superuser(self, sender, **kwargs):
        User = get_user_model()
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'i@moyeka.ru')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin')

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(username, email, password)
            print(f'Superuser {username} created successfully')
        else:
            print(f'Superuser {username} already exists')