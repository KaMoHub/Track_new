import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'track.settings')
django.setup()

from apps.events.models import Event, CompetitionDirection
from apps.children.models import Child


def fill_competition_directions():
    """Заполняет справочник направлений конкурсов"""
    directions = [
        {'name': 'Наука', 'code': 'science', 'sort_order': 1},
        {'name': 'Спорт', 'code': 'sport', 'sort_order': 2},
        {'name': 'Образование', 'code': 'education', 'sort_order': 3},
        {'name': 'Творчество', 'code': 'creativity', 'sort_order': 4},
    ]

    created_count = 0
    for direction_data in directions:
        obj, created = CompetitionDirection.objects.get_or_create(
            code=direction_data['code'],
            defaults={
                'name': direction_data['name'],
                'sort_order': direction_data['sort_order']
            }
        )
        if created:
            created_count += 1
            print(f"✅ Создано направление: {obj.name}")
        else:
            print(f"⏭️ Уже существует: {obj.name}")

    print(f"\n📊 Итого создано направлений: {created_count}")
    return created_count


def set_all_events_published():
    """Устанавливает всем конкурсам статус 'published'"""
    count = Event.objects.all().update(status='published')
    print(f"✅ Установлен статус 'published' для {count} конкурсов")
    return count


def update_participation_format():
    """Обновляет поле participation_format на основе is_offline"""
    total = Event.objects.count()
    offline_count = 0
    online_count = 0

    for event in Event.objects.all():
        if event.is_offline:
            event.participation_format = 'offline'
            offline_count += 1
        else:
            event.participation_format = 'online'
            online_count += 1
        event.save()

    print(f"✅ Обновлено конкурсов: {total}")
    print(f"   - Очных (offline): {offline_count}")
    print(f"   - Заочных (online): {online_count}")
    return total


def split_fio(fio):
    """Разбивает ФИО на фамилию, имя, отчество"""
    parts = fio.strip().split()

    if len(parts) == 1:
        return parts[0], '', ''
    elif len(parts) == 2:
        return parts[0], parts[1], ''
    else:
        return parts[0], parts[1], ' '.join(parts[2:])


def fill_child_names():
    """Разбивает существующие ФИО детей на фамилию, имя, отчество"""
    children = Child.objects.all()
    total = children.count()
    updated = 0

    print(f"\n👶 Найдено детей: {total}")

    for child in children:
        old_fio = child.fio
        last_name, first_name, patronymic = split_fio(old_fio)

        # Пропускаем уже заполненные (не 'temp')
        if (child.last_name and child.last_name != 'temp' and
                child.first_name and child.first_name != 'temp'):
            print(f"✓ Пропущен (уже заполнен): {old_fio}")
            continue

        child.last_name = last_name
        child.first_name = first_name
        child.patronymic = patronymic
        child.save()
        updated += 1
        print(f"  Обработан: {old_fio} -> {last_name} {first_name} {patronymic}")

    print(f"\n✅ Обновлено детей: {updated} из {total}")
    return updated


def main():
    print("=" * 50)
    print("ЗАПУСК ОБНОВЛЕНИЯ ДАННЫХ")
    print("=" * 50)

    print("\n1. Заполнение направлений конкурсов...")
    fill_competition_directions()

    print("\n2. Установка статуса 'published' для всех конкурсов...")
    set_all_events_published()

    print("\n3. Обновление формата участия (на основе is_offline)...")
    update_participation_format()

    print("\n4. Разбивка ФИО детей...")
    fill_child_names()

    print("\n" + "=" * 50)
    print("✅ ВСЕ ОПЕРАЦИИ ЗАВЕРШЕНЫ")
    print("=" * 50)


if __name__ == '__main__':
    main()