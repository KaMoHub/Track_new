# list_user.py
import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'track.settings')
django.setup()

# Импортируем кастомную модель User
from apps.accounts.models import User
from apps.children.models import Teacher, StudioEnrollment


def list_all_users():
    """Вывод списка всех пользователей"""
    print("=" * 80)
    print("СПИСОК ВСЕХ ПОЛЬЗОВАТЕЛЕЙ СИСТЕМЫ")
    print("=" * 80)

    users = User.objects.all().order_by('username')

    if not users.exists():
        print("Пользователи не найдены")
        return

    print(f"Всего пользователей: {users.count()}")
    print("-" * 80)

    for user in users:
        print(f"ID: {user.id};  {user.username}")





if __name__ == '__main__':
    list_all_users()