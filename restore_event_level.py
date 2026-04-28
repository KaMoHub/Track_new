import os
import sys
import sqlite3
from datetime import datetime

# Настройка Django
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'track.settings')
django.setup()

from apps.events.models import Event

# Пути к базам данных
CURRENT_DB = 'db.sqlite3'
ARCHIVE_DB = 'db_archive.sqlite3'
CUTOFF_DATE = datetime(2026, 4, 16).date()  # конкурсы после 16 апреля


def get_archive_event_level(event_id, archive_conn):
    """Получает уровень конкурса из архивной БД по ID"""
    cursor = archive_conn.cursor()
    cursor.execute("SELECT level FROM events_event WHERE id = ?", (event_id,))
    row = cursor.fetchone()
    return row[0] if row else None


def restore_event_levels():
    """Восстанавливает уровень конкурсов из архивной БД (только если текущий уровень 'center')"""

    if not os.path.exists(ARCHIVE_DB):
        print(f"❌ Ошибка: Архивная БД не найдена по пути: {ARCHIVE_DB}")
        return

    print(f"✅ Архивная БД найдена: {ARCHIVE_DB}")

    archive_conn = sqlite3.connect(ARCHIVE_DB)

    # Получаем все конкурсы из текущей БД, у которых уровень 'center'
    events = Event.objects.filter(level='center')
    total = events.count()
    restored = 0
    not_found = 0
    skipped = 0

    print(f"\n📊 Конкурсов с уровнем 'Центровский' в текущей БД: {total}")
    print("-" * 60)

    for event in events:
        archive_level = get_archive_event_level(event.id, archive_conn)

        if archive_level is None:
            not_found += 1
            print(f"⚠️ ID={event.id} | {event.name[:50]} | Не найден в архиве")
            continue

        if archive_level == 'center':
            skipped += 1
            print(f"⏭️ ID={event.id} | {event.name[:50]} | В архиве тоже Центровский, пропущен")
            continue

        # Восстанавливаем уровень
        old_level = event.level
        event.level = archive_level
        event.save()
        restored += 1
        print(f"🔄 ID={event.id} | {event.name[:50]} | {old_level} → {archive_level}")

    archive_conn.close()

    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ВОССТАНОВЛЕНИЯ:")
    print(f"   ✅ Восстановлено: {restored}")
    print(f"   ⏭️ Пропущено (в архиве тоже Центровский): {skipped}")
    print(f"   ⚠️ Не найдено в архиве: {not_found}")
    print(f"   📊 Всего обработано: {total}")
    print("=" * 60)


def list_new_events():
    """Выводит список конкурсов, добавленных после 16 апреля 2026 года"""
    events = Event.objects.filter(created_at__date__gt=CUTOFF_DATE).order_by('created_at')
    count = events.count()

    print("\n" + "=" * 60)
    print(f"📋 КОНКУРСЫ, ДОБАВЛЕННЫЕ ПОСЛЕ {CUTOFF_DATE.strftime('%d.%m.%Y')}:")
    print("=" * 60)

    if count == 0:
        print("   Нет конкурсов, добавленных после указанной даты.")
    else:
        print(f"   Всего: {count}")
        print("-" * 60)
        for event in events:
            created_date = event.created_at.date()
            print(f"   {created_date.strftime('%d.%m.%Y')} | ID={event.id} | {event.name}")

    print("=" * 60)


if __name__ == '__main__':
    print("=" * 60)
    print("🔄 ВОССТАНОВЛЕНИЕ УРОВНЕЙ КОНКУРСОВ ИЗ АРХИВНОЙ БД")
    print("   (только для конкурсов с уровнем 'Центровский')")
    print("=" * 60)

    restore_event_levels()

    list_new_events()

    print("\n✅ Готово!")