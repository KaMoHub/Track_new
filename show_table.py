# show_table.py для вывода содержимого таблицы


import sqlite3
from collections import defaultdict


def get_table_info(db_path, table_name):
    """Возвращает структуру таблицы: колонки, типы и внешние ключи."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Получаем колонки
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()

    # Получаем внешние ключи
    cursor.execute(f"PRAGMA foreign_key_list({table_name})")
    foreign_keys = cursor.fetchall()

    conn.close()

    return columns, foreign_keys


def get_all_tables(db_path):
    """Получаем список всех таблиц в базе."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    conn.close()
    return tables


def print_table_structure(db_path, table_name):
    """Печатает структуру одной таблицы."""
    columns, fks = get_table_info(db_path, table_name)
    print(f"\n[Таблица: {table_name}]")
    print("-" * 50)
    for col in columns:
        cid, name, col_type, notnull, default_val, pk = col
        null_str = "NOT NULL" if notnull else "NULL"
        pk_str = " (PK)" if pk else ""
        print(f"{name:20} {col_type:15} {null_str:10}{pk_str}")
    if fks:
        print("\nВнешние ключи:")
        for fk in fks:
            if len(fk) == 9:
                id, seq, table_from, table_to, from_col, to_col, on_update, on_delete, match = fk
            elif len(fk) == 8:
                id, seq, table_from, table_to, from_col, to_col, on_update, on_delete = fk
                match = None
            print(f"  {from_col} -> {table_to}.{to_col}")
    else:
        print("\nВнешние ключи: отсутствуют")


def print_db_structure(db_path):
    """Печатает структуру всех таблиц и зависимости."""
    tables = get_all_tables(db_path)

    print("=== Структура базы данных ===")
    for table in tables:
        print_table_structure(db_path, table)


def print_dependencies_tree(db_path):
    """Печатает дерево зависимостей (кто зависит от кого)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Собираем зависимости
    deps = defaultdict(list)
    tables = get_all_tables(db_path)

    for table in tables:
        _, fks = get_table_info(db_path, table)
        for fk in fks:
            if len(fk) == 9:
                id, seq, table_from, table_to, from_col, to_col, on_update, on_delete, match = fk
            elif len(fk) == 8:
                id, seq, table_from, table_to, from_col, to_col, on_update, on_delete = fk
                match = None
            deps[table_to].append((table, from_col, to_col))  # parent -> child

    conn.close()

    print("\n=== Дерево зависимостей ===")
    for parent, children in deps.items():
        print(f"\n'{parent}' <-")
        for child, from_col, to_col in children:
            print(f"  {child} ({from_col} -> {to_col})")


def print_table_content(db_path, table_name):
    """Выводит содержимое таблицы."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Получаем имена колонок
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
        col_names = [description[0] for description in cursor.description]

        # Выбираем все данные
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()

        print(f"\n[Содержимое таблицы: {table_name}]")
        print("-" * 80)

        # Выводим заголовки
        header = " | ".join(col_names)
        print(header)
        print("-" * len(header))

        # Выводим строки
        for row in rows:
            row_str = " | ".join(str(val) for val in row)
            print(row_str)

    except sqlite3.OperationalError as e:
        print(f"Ошибка при работе с таблицей '{table_name}': {e}")

    conn.close()


def interactive_table_content(db_path):


    """Интерактивный ввод имени таблицы и вывод содержимого."""
    tables = get_all_tables(db_path)
    print("\n=== Вывод содержимого таблицы ===")
    print("Доступные таблицы:", ", ".join(tables))
    table_name = input("Введите имя таблицы: ").strip()

    if table_name in tables:
        print_table_content(db_path, table_name)
    else:
        print(f"Таблица '{table_name}' не найдена.")


if __name__ == "__main__":
    db_path = "db.sqlite3"

    # Показать структуру и зависимости
    print_db_structure(db_path)
    print_dependencies_tree(db_path)

    # Интерактивный вывод содержимого
    interactive_table_content(db_path)