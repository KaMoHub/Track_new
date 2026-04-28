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


def get_archive_event_data(event_id, archive_conn):
    """Получает данные конкурса из архивной БД по ID"""
    cursor = archive_conn.cursor()
    cursor.execute("""
        SELECT application_deadline, result_date 
        FROM events_event 
        WHERE id = ?
    """, (event_id,))
    row = cursor.fetchone()
    if row:
        return {
            'application_deadline': row[0],
            'result_date': row[1]
        }
    return None


def restore_dates():
    """Восстанавливает срок подачи и дату результата из архивной БД для всех найденных конкурсов"""

    if not os.path.exists(ARCHIVE_DB):
        print(f"❌ Ошибка: Архивная БД не найдена по пути: {ARCHIVE_DB}")
        return

    print(f"✅ Архивная БД найдена: {ARCHIVE_DB}")

    archive_conn = sqlite3.connect(ARCHIVE_DB)

    # Получаем все конкурсы из текущей БД
    events = Event.objects.all()
    total = events.count()
    restored_deadline = 0
    restored_result_date = 0
    not_found = 0
    no_changes = 0

    print(f"\n📊 Всего конкурсов в текущей БД: {total}")
    print("-" * 70)

    for event in events:
        archive_data = get_archive_event_data(event.id, archive_conn)

        if archive_data is None:
            not_found += 1
            print(f"⚠️ ID={event.id} | {event.name[:50]} | Не найден в архиве")
            continue

        changes = []

        # Восстанавливаем срок подачи
        if archive_data['application_deadline'] is not None:
            old_deadline = event.application_deadline
            if old_deadline != archive_data['application_deadline']:
                event.application_deadline = archive_data['application_deadline']
                restored_deadline += 1
                changes.append(f"срок подачи: {old_deadline} → {archive_data['application_deadline']}")

        # Восстанавливаем дату результата
        if archive_data['result_date'] is not None:
            old_result = event.result_date
            if old_result != archive_data['result_date']:
                event.result_date = archive_data['result_date']
                restored_result_date += 1
                changes.append(f"дата результатов: {old_result} → {archive_data['result_date']}")

        if changes:
            event.save()
            print(f"🔄 ID={event.id} | {event.name[:40]} | {', '.join(changes)}")
        else:
            no_changes += 1
            print(f"⏭️ ID={event.id} | {event.name[:50]} | Даты совпадают с архивом")

    archive_conn.close()

    print("\n" + "=" * 70)
    print("📊 РЕЗУЛЬТАТЫ ВОССТАНОВЛЕНИЯ ДАТ:")
    print(f"   ✅ Восстановлено сроков подачи: {restored_deadline}")
    print(f"   ✅ Восстановлено дат результатов: {restored_result_date}")
    print(f"   ⏭️ Совпадают с архивом: {no_changes}")
    print(f"   ⚠️ Не найдено в архиве: {not_found}")
    print(f"   📊 Всего обработано: {total}")
    print("=" * 70)


if __name__ == '__main__':
    print("=" * 70)
    print("🔄 ВОССТАНОВЛЕНИЕ ДАТ КОНКУРСОВ ИЗ АРХИВНОЙ БД")
    print("   (срок подачи и дата результатов)")
    print("=" * 70)

    restore_dates()

    print("\n✅ Готово!")