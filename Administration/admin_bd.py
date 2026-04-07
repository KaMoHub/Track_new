import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import sqlite3
import os
from pathlib import Path
import pandas as pd
from tkinter import messagebox as mb

# Глобальные переменные для вкладки с содержимым таблиц
table_combobox = None
tree = None
status_label = None
text_area = None
text_area_project = None
child_id_combobox = None
text_area_search = None
status_label_search = None
# Глобальные переменные для вкладки замены ссылок
source_child_combobox = None
target_child_combobox = None
text_area_source = None
text_area_target = None
status_label_replace = None
source_child_id = None
target_child_id = None

# Просмотр содержимого таблиц и выгрузка
def view_table_content():
    """Показывает содержимое выбранной таблицы"""
    try:
        selected_table = table_combobox.get()
        if not selected_table:
            mb.showwarning("Предупреждение", "Выберите таблицу!")
            return

        # Очищаем дерево
        for item in tree.get_children():
            tree.delete(item)

        # Подключаемся к БД
        db_path = os.path.join('..', 'db.sqlite3')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Получаем данные
        cursor.execute(f"SELECT * FROM {selected_table}")
        rows = cursor.fetchall()

        # Получаем названия колонок
        columns = [description[0] for description in cursor.description]

        # Настраиваем колонки в дереве
        tree["columns"] = columns
        tree["show"] = "headings"

        # Настраиваем заголовки и ширину колонок
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="center")

        # Вставляем данные
        for row in rows:
            tree.insert("", "end", values=row)

        # Обновляем статус
        status_label.config(text=f"Таблица: {selected_table} | Всего записей: {len(rows)}")

        conn.close()

    except Exception as e:
        mb.showerror("Ошибка", f"Не удалось загрузить данные: {str(e)}")

def load_tables_for_combobox():
    """Загружает список таблиц для выпадающего списка"""
    try:
        db_path = os.path.join('..', 'db.sqlite3')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Список таблиц для исключения
        exclude_tables = [
            'accounts_user_groups',
            'accounts_user_user_permissions',
            'accounts_useractionlog',
            'auth_group',
            'auth_group_permissions',
            'auth_permission',
            'children_childlist'
        ]

        # Получаем таблицы
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            AND name NOT LIKE 'django_%'
            ORDER BY name;
        """)

        tables = cursor.fetchall()

        # Фильтруем исключенные таблицы
        table_list = [t[0] for t in tables if t[0] not in exclude_tables]

        # Обновляем выпадающий список
        table_combobox['values'] = table_list

        if table_list:
            table_combobox.set(table_list[0])

        conn.close()

    except Exception as e:
        mb.showerror("Ошибка", f"Не удалось загрузить список таблиц: {str(e)}")

def export_to_excel():
    """Экспортирует содержимое таблицы в Excel"""
    try:
        selected_table = table_combobox.get()
        if not selected_table:
            mb.showwarning("Предупреждение", "Выберите таблицу для экспорта!")
            return

        # Запрашиваем место сохранения файла
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"{selected_table}.xlsx"
        )

        if not file_path:
            return

        # Подключаемся к БД и экспортируем
        db_path = os.path.join('..', 'db.sqlite3')
        conn = sqlite3.connect(db_path)

        # Читаем таблицу в DataFrame
        df = pd.read_sql_query(f"SELECT * FROM {selected_table}", conn)

        # Экспортируем в Excel
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name=selected_table, index=False)

            # Настраиваем ширину колонок
            worksheet = writer.sheets[selected_table]
            for column in df:
                column_width = max(df[column].astype(str).map(len).max(), len(column))
                column_width = min(column_width, 50)
                col_idx = df.columns.get_loc(column) + 1
                worksheet.column_dimensions[chr(64 + col_idx)].width = column_width

        conn.close()

        mb.showinfo("Успех", f"Таблица '{selected_table}' экспортирована в Excel!\nФайл: {file_path}")

    except Exception as e:
        mb.showerror("Ошибка", f"Не удалось экспортировать: {str(e)}")

def refresh_table():
    """Обновляет содержимое таблицы"""
    view_table_content()


# Структура базы данных
def get_database_structure(db_path='db.sqlite3', output_file='database_structure.txt'):
    """Выводит детальную информацию о всех таблицах и сохраняет в файл"""

    if not os.path.exists(db_path):
        return f"Файл БД не найден: {db_path}"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Список таблиц для исключения
    exclude_tables = [
        'accounts_user_groups',
        'accounts_user_user_permissions',
        'accounts_useractionlog',
        'auth_group',
        'auth_group_permissions',
        'auth_permission',
        'children_childlist'
    ]

    # Создаем условие для исключения таблиц
    exclude_condition = " AND name NOT IN (" + ",".join(["?"] * len(exclude_tables)) + ")"

    # Получаем все таблицы, исключая системные, django_ и указанные таблицы
    query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        AND name NOT LIKE 'django_%'
    """ + exclude_condition + """
        ORDER BY name;
    """

    cursor.execute(query, exclude_tables)
    tables = cursor.fetchall()

    # Собираем результат в строку
    result = []
    result.append("\n" + " ")
    result.append(f"  СТРУКТУРА БАЗЫ ДАННЫХ DJANGO")
    result.append(f"  Файл: {os.path.abspath(db_path)}")
    result.append(" " )

    for table in tables:
        table_name = table[0]

        result.append(f"\n{'=' * 110}")
        result.append(f"📋 ТАБЛИЦА: {table_name}")
        result.append(f"{'=' * 110}")

        # Получаем структуру таблицы
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        columns = cursor.fetchall()

        # Получаем внешние ключи
        cursor.execute(f"PRAGMA foreign_key_list('{table_name}')")
        foreign_keys = cursor.fetchall()

        # Создаем словарь связей
        fk_dict = {}
        for fk in foreign_keys:
            fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
            fk_dict[from_col] = ref_table

        result.append(
            f"\n{'Колонка':<30} {'Тип':<15} {'NULL':<8} {'PK':<5} {'По умолчанию':<15} {'Связанная таблица':<25}")
        result.append("-" * 110)

        for col in columns:
            col_id, name, col_type, notnull, default, pk = col
            null_str = "NO" if notnull else "YES"
            pk_str = "✓" if pk else ""
            default_str = str(default) if default else ""

            # Получаем название связанной таблицы если это ключ
            related_table = fk_dict.get(name, "")

            result.append(f"{name:<30} {col_type:<15} {null_str:<8} {pk_str:<5} {default_str:<15} {related_table:<25}")

        # Получаем количество записей
        cursor.execute(f"SELECT COUNT(*) FROM '{table_name}'")
        count = cursor.fetchone()[0]
        result.append(f"\n📊 Всего записей: {count}")

    conn.close()

    # Сохраняем в файл
    result_text = "\n".join(result)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(result_text)

    return result_text

def show_structure():
    """Показывает структуру базы данных"""
    try:
        # Очищаем текстовое поле на вкладке структуры
        text_area.delete(1.0, tk.END)

        # Путь к базе данных на один уровень выше
        db_path = os.path.join('..', 'db.sqlite3')

        # Получаем структуру базы данных
        structure = get_database_structure(db_path, 'database_structure.txt')

        # Вставляем содержимое
        text_area.insert(1.0, structure)

        messagebox.showinfo("Успех", "Структура базы данных загружена!")

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось получить структуру: {str(e)}")


# Структура проекта
def show_project_structure():
    """Показывает структуру проекта"""
    try:
        # Очищаем текстовое поле на вкладке проекта
        text_area_project.delete(1.0, tk.END)

        # Получаем структуру проекта
        project_dir = ".."  # На один уровень выше
        output_file = "project_structure.txt"

        get_project_structure(project_dir, output_file)

        # Читаем файл со структурой
        with open(output_file, 'r', encoding='utf-8') as f:
            structure = f.read()

        # Вставляем содержимое
        text_area_project.insert(1.0, structure)

        messagebox.showinfo("Успех", "Структура проекта загружена!")

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось получить структуру: {str(e)}")

def get_project_structure(root_dir, output_file, ignore_dirs=None, ignore_files=None):
    """
    Создает текстовый файл со структурой проекта

    Args:
        root_dir (str): Корневая директория проекта
        output_file (str): Имя выходного файла
        ignore_dirs (list): Список директорий для игнорирования
        ignore_files (list): Список файлов для игнорирования
    """
    if ignore_dirs is None:
        ignore_dirs = ['.git', '__pycache__', '.venv', 'venv', 'env', 'node_modules', '.idea']

    if ignore_files is None:
        ignore_files = ['.DS_Store', 'thumbs.db', '.gitignore', '.gitattributes', 'data_dump.json']

    root_path = Path(root_dir)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Структура проекта: {root_path.name}\n")
        f.write("=" * 50 + "\n\n")

        def write_tree(directory, prefix=""):
            """Рекурсивная функция для записи структуры"""
            try:
                items = sorted(os.listdir(directory))
            except PermissionError:
                f.write(f"{prefix}└── [Ошибка доступа]\n")
                return

            # Фильтруем элементы
            filtered_items = []
            for item in items:
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path) and item in ignore_dirs:
                    continue
                if os.path.isfile(item_path) and item in ignore_files:
                    continue
                if '~' in item:
                    continue
                filtered_items.append(item)

            for index, item in enumerate(filtered_items):
                item_path = os.path.join(directory, item)
                is_last = index == len(filtered_items) - 1

                if os.path.isdir(item_path):
                    # Папка
                    connector = "└── " if is_last else "├── "
                    f.write(f"{prefix}{connector}{item}/\n")

                    # Рекурсивный вызов для поддиректорий
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    write_tree(item_path, new_prefix)
                else:
                    # Файл
                    connector = "└── " if is_last else "├── "
                    # Добавляем размер файла
                    try:
                        size = os.path.getsize(item_path)
                        size_str = f" ({size} bytes)"
                    except OSError:
                        size_str = " (недоступен)"

                    f.write(f"{prefix}{connector}{item}{size_str}\n")

        write_tree(root_path)


# Поиск ссылок
def load_child_ids():
    """Загружает список детей (ID + FIO) для выпадающего списка"""
    try:
        db_path = os.path.join('..', 'db.sqlite3')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Получаем ID и FIO из таблицы children_child
        cursor.execute("""
            SELECT id, fio 
            FROM children_child 
            ORDER BY id
        """)

        children = cursor.fetchall()

        # Формируем список отображаемых значений (ID + FIO)
        display_list = []
        child_data = {}  # Словарь для хранения соответствия display -> id

        for child in children:
            child_id = child[0]
            fio = child[1] if child[1] else "Без имени"

            # Формируем отображаемую строку
            display_text = f"{child_id} - {fio}"
            display_list.append(display_text)
            child_data[display_text] = child_id

        # Обновляем выпадающий список
        child_id_combobox['values'] = display_list

        # Сохраняем словарь соответствия для использования в поиске
        child_id_combobox.child_data = child_data

        if display_list:
            child_id_combobox.set(display_list[0])

        conn.close()

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось загрузить список детей: {str(e)}")

def search_child_links():
    """Ищет все ссылки на выбранного ребенка во всех таблицах с подробной информацией"""
    try:
        selected_display = child_id_combobox.get()
        if not selected_display:
            messagebox.showwarning("Предупреждение", "Выберите ребенка!")
            return

        # Получаем ID ребенка из выбранной строки
        if hasattr(child_id_combobox, 'child_data') and selected_display in child_id_combobox.child_data:
            selected_child_id = child_id_combobox.child_data[selected_display]
        else:
            selected_child_id = selected_display.split(' - ')[0]

        # Очищаем текстовое поле
        text_area_search.delete(1.0, tk.END)

        # Подключаемся к БД
        db_path = os.path.join('..', 'db.sqlite3')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Получаем FIO ребенка для отображения
        cursor.execute("""
            SELECT fio 
            FROM children_child 
            WHERE id = ?
        """, (selected_child_id,))

        child_info = cursor.fetchone()
        child_fio = child_info[0] if child_info else "Неизвестно"

        # Список таблиц для исключения
        exclude_tables = [
            'accounts_user_groups',
            'accounts_user_user_permissions',
            'accounts_useractionlog',
            'auth_group',
            'auth_group_permissions',
            'auth_permission',
            'children_childlist'
        ]

        # Получаем все таблицы
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            AND name NOT LIKE 'django_%'
            ORDER BY name;
        """)

        tables = cursor.fetchall()

        # Результаты поиска
        results = []
        results.append("=" * 120)
        results.append(f"🔍 ПОИСК ССЫЛОК НА РЕБЕНКА")
        results.append(f"   ID: {selected_child_id}")
        results.append(f"   ФИО: {child_fio}")
        results.append("=" * 120)

        found_count = 0
        links_count = 0  # Общее количество ссылок

        for table in tables:
            table_name = table[0]

            # Пропускаем исключенные таблицы
            if table_name in exclude_tables:
                continue

            # Получаем структуру таблицы
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()

            # Ищем поля, которые могут ссылаться на ребенка
            for col in columns:
                col_name = col[1]
                # Ищем поля с 'child' в названии или заканчивающиеся на '_id'
                if 'child' in col_name.lower() or col_name.endswith('_id'):
                    try:
                        query = f"SELECT * FROM '{table_name}' WHERE {col_name} = ?"
                        cursor.execute(query, (selected_child_id,))
                        rows = cursor.fetchall()

                        if rows:
                            found_count += 1
                            links_count += len(rows)
                            results.append(f"\n{'=' * 120}")
                            results.append(f"📋 ТАБЛИЦА: {table_name}")
                            results.append(f"🔗 Поле-ссылка: {col_name}")
                            results.append(f"📊 Найдено записей: {len(rows)}")
                            results.append(f"{'=' * 120}")

                            # Получаем названия всех колонок таблицы
                            cursor.execute(f"PRAGMA table_info('{table_name}')")
                            all_columns = cursor.fetchall()
                            col_names = [c[1] for c in all_columns]

                            # Выводим каждую запись со всеми полями
                            for idx, row in enumerate(rows, 1):
                                results.append(f"\n  📝 Запись #{idx}:")
                                results.append(f"  {'-' * 100}")

                                for i, value in enumerate(row):
                                    if i < len(col_names):
                                        field_name = col_names[i]
                                        field_value = value if value is not None else "NULL"
                                        # Ограничиваем длину значения для красивого вывода
                                        if len(str(field_value)) > 80:
                                            field_value = str(field_value)[:80] + "..."
                                        results.append(f"     {field_name:<30} = {field_value}")

                                results.append(f"  {'-' * 100}")
                    except Exception as e:
                        pass

        if found_count == 0:
            results.append(f"\n❌ Ссылок на ребенка не найдено")
            # Если ссылок нет - активируем кнопку удаления
            btn_delete.config(state='normal')
            status_label_search.config(
                text=f"✅ Ссылок нет. Ребенка можно удалить. ID: {selected_child_id} - {child_fio}")
        else:
            results.append(f"\n✅ Всего найдено таблиц со ссылками: {found_count}")
            results.append(f"📊 Всего найдено ссылок: {links_count}")
            # Если есть ссылки - деактивируем кнопку удаления
            btn_delete.config(state='disabled')
            status_label_search.config(
                text=f"⚠️ Есть ссылки! Удаление невозможно. Найдено ссылок: {links_count} | ID: {selected_child_id} - {child_fio}")

        conn.close()

        # Выводим результаты
        result_text = "\n".join(results)
        text_area_search.insert(1.0, result_text)

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось выполнить поиск: {str(e)}")
        btn_delete.config(state='disabled')

def delete_child():
    """Удаляет ребенка и все его ссылки из всех таблиц"""
    try:
        selected_display = child_id_combobox.get()
        if not selected_display:
            messagebox.showwarning("Предупреждение", "Выберите ребенка для удаления!")
            return

        # Получаем ID ребенка
        if hasattr(child_id_combobox, 'child_data') and selected_display in child_id_combobox.child_data:
            selected_child_id = child_id_combobox.child_data[selected_display]
        else:
            selected_child_id = selected_display.split(' - ')[0]

        # Получаем ФИО ребенка
        db_path = os.path.join('..', 'db.sqlite3')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT fio FROM children_child WHERE id = ?", (selected_child_id,))
        child_info = cursor.fetchone()
        child_fio = child_info[0] if child_info else "Неизвестно"

        # ПРОВЕРКА: ищем все ссылки перед удалением
        exclude_tables = [
            'accounts_user_groups',
            'accounts_user_user_permissions',
            'accounts_useractionlog',
            'auth_group',
            'auth_group_permissions',
            'auth_permission',
            'children_childlist'
        ]

        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            AND name NOT LIKE 'django_%'
            ORDER BY name;
        """)

        tables = cursor.fetchall()

        # Собираем информацию о ссылках
        links_info = []
        total_links = 0

        for table in tables:
            table_name = table[0]

            if table_name in exclude_tables:
                continue

            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()

            for col in columns:
                col_name = col[1]
                if 'child' in col_name.lower() or col_name.endswith('_id'):
                    try:
                        query = f"SELECT COUNT(*) FROM '{table_name}' WHERE {col_name} = ?"
                        cursor.execute(query, (selected_child_id,))
                        count = cursor.fetchone()[0]

                        if count > 0:
                            links_info.append(f"{table_name}.{col_name}: {count} записей")
                            total_links += count
                    except:
                        pass

        # Если есть ссылки - не даем удалить
        if total_links > 0:
            messagebox.showerror(
                "Невозможно удалить",
                f"Ребенок имеет {total_links} ссылок в других таблицах!\n\n"
                f"Удаление невозможно. Сначала удалите все ссылки.\n\n"
                f"{chr(10).join(links_info)}"
            )
            conn.close()
            return

        # Подтверждение удаления (только если нет ссылок)
        result = messagebox.askyesno(
            "⚠️ ПОДТВЕРЖДЕНИЕ УДАЛЕНИЯ",
            f"Вы уверены, что хотите УДАЛИТЬ ребенка?\n\n"
            f"ID: {selected_child_id}\n"
            f"ФИО: {child_fio}\n\n"
            f"⚠️ ЭТО ДЕЙСТВИЕ НЕЛЬЗЯ БУДЕТ ОТМЕНИТЬ!\n\n"
            f"Удалить?"
        )

        if not result:
            conn.close()
            return

        # Удаляем запись о ребенке
        cursor.execute("DELETE FROM children_child WHERE id = ?", (selected_child_id,))

        # Сохраняем изменения
        conn.commit()
        conn.close()

        # Обновляем список детей в выпадающем списке
        load_child_ids()

        # Очищаем текстовое поле
        text_area_search.delete(1.0, tk.END)

        # Выводим результат
        result_text = f"✅ УДАЛЕНИЕ ВЫПОЛНЕНО УСПЕШНО!\n\n"
        result_text += f"Удален ребенок:\n"
        result_text += f"   ID: {selected_child_id}\n"
        result_text += f"   ФИО: {child_fio}\n\n"
        result_text += f"📊 Ребенок успешно удален.\n"

        text_area_search.insert(1.0, result_text)

        status_label_search.config(text=f"✅ Ребенок {child_fio} (ID: {selected_child_id}) удален!")

        messagebox.showinfo("Удаление выполнено",
                            f"Ребенок успешно удален!\n\nID: {selected_child_id}\nФИО: {child_fio}")

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось выполнить удаление: {str(e)}")


# 4 Замена ссылко
def load_children_for_combobox(combobox, data_dict_attr):
    """Загружает список детей для указанного combobox"""
    try:
        db_path = os.path.join('..', 'db.sqlite3')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, fio 
            FROM children_child 
            ORDER BY id
        """)

        children = cursor.fetchall()

        display_list = []
        child_data = {}

        for child in children:
            child_id = child[0]
            fio = child[1] if child[1] else "Без имени"
            display_text = f"{child_id} - {fio}"
            display_list.append(display_text)
            child_data[display_text] = child_id

        combobox['values'] = display_list
        setattr(combobox, data_dict_attr, child_data)

        if display_list:
            combobox.set(display_list[0])

        conn.close()

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось загрузить список детей: {str(e)}")

def show_child_links(part):
    """Показывает ссылки на выбранного ребенка (source или target) с подробной информацией"""
    try:
        if part == 'source':
            selected_display = source_child_combobox.get()
            text_widget = text_area_source
            status_prefix = "ИСТОЧНИК"
        else:
            selected_display = target_child_combobox.get()
            text_widget = text_area_target
            status_prefix = "ПОЛУЧАТЕЛЬ"

        if not selected_display:
            messagebox.showwarning("Предупреждение", f"Выберите ребенка-{status_prefix}!")
            return

        # Получаем ID ребенка
        if hasattr(source_child_combobox, 'child_data') and part == 'source':
            child_data = source_child_combobox.child_data
        elif hasattr(target_child_combobox, 'child_data') and part == 'target':
            child_data = target_child_combobox.child_data
        else:
            child_data = {}

        if selected_display in child_data:
            selected_child_id = child_data[selected_display]
        else:
            selected_child_id = selected_display.split(' - ')[0]

        # Сохраняем ID в глобальные переменные
        if part == 'source':
            global source_child_id
            source_child_id = selected_child_id
        else:
            global target_child_id
            target_child_id = selected_child_id

        # Очищаем текстовое поле
        text_widget.delete(1.0, tk.END)

        # Подключаемся к БД
        db_path = os.path.join('..', 'db.sqlite3')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Получаем FIO ребенка
        cursor.execute("SELECT fio FROM children_child WHERE id = ?", (selected_child_id,))
        child_info = cursor.fetchone()
        child_fio = child_info[0] if child_info else "Неизвестно"

        # Список таблиц для исключения
        exclude_tables = [
            'accounts_user_groups',
            'accounts_user_user_permissions',
            'accounts_useractionlog',
            'auth_group',
            'auth_group_permissions',
            'auth_permission',
            'children_childlist'
        ]

        # Получаем все таблицы
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            AND name NOT LIKE 'django_%'
            ORDER BY name;
        """)

        tables = cursor.fetchall()

        # Результаты поиска
        results = []
        results.append("=" * 120)
        results.append(f"🔍 ССЫЛКИ НА РЕБЕНКА-{status_prefix}")
        results.append(f"   ID: {selected_child_id}")
        results.append(f"   ФИО: {child_fio}")
        results.append("=" * 120)

        found_count = 0

        for table in tables:
            table_name = table[0]

            if table_name in exclude_tables:
                continue

            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()

            for col in columns:
                col_name = col[1]
                if 'child' in col_name.lower() or col_name.endswith('_id'):
                    try:
                        query = f"SELECT * FROM '{table_name}' WHERE {col_name} = ?"
                        cursor.execute(query, (selected_child_id,))
                        rows = cursor.fetchall()

                        if rows:
                            found_count += 1
                            results.append(f"\n{'=' * 120}")
                            results.append(f"📋 ТАБЛИЦА: {table_name}")
                            results.append(f"🔗 Поле-ссылка: {col_name}")
                            results.append(f"📊 Найдено записей: {len(rows)}")
                            results.append(f"{'=' * 120}")

                            # Получаем названия всех колонок таблицы
                            cursor.execute(f"PRAGMA table_info('{table_name}')")
                            all_columns = cursor.fetchall()
                            col_names = [c[1] for c in all_columns]

                            # Выводим каждую запись со всеми полями
                            for idx, row in enumerate(rows, 1):
                                results.append(f"\n  📝 Запись #{idx}:")
                                results.append(f"  {'-' * 100}")

                                for i, value in enumerate(row):
                                    if i < len(col_names):
                                        field_name = col_names[i]
                                        field_value = value if value is not None else "NULL"
                                        # Ограничиваем длину значения для красивого вывода
                                        if len(str(field_value)) > 80:
                                            field_value = str(field_value)[:80] + "..."
                                        results.append(f"     {field_name:<30} = {field_value}")

                                results.append(f"  {'-' * 100}")
                    except Exception as e:
                        pass

        if found_count == 0:
            results.append(f"\n❌ Ссылок на ребенка не найдено")
        else:
            results.append(f"\n✅ Всего найдено ссылок: {found_count}")

        conn.close()

        result_text = "\n".join(results)
        text_widget.insert(1.0, result_text)

        status_label_replace.config(text=f"{status_prefix}: {child_fio} | Найдено ссылок: {found_count}")

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось выполнить поиск: {str(e)}")

def replace_links():
    """Переносит все ссылки из источника в получатель"""
    try:
        global source_child_id, target_child_id

        if not source_child_id:
            messagebox.showwarning("Предупреждение", "Сначала выберите ребенка-ИСТОЧНИК и нажмите 'Показать ссылки'!")
            return

        if not target_child_id:
            messagebox.showwarning("Предупреждение", "Сначала выберите ребенка-ПОЛУЧАТЕЛЬ и нажмите 'Показать ссылки'!")
            return

        if source_child_id == target_child_id:
            messagebox.showwarning("Предупреждение", "Ребенок-ИСТОЧНИК и ребенок-ПОЛУЧАТЕЛЬ не могут совпадать!")
            return

        # Подтверждение действия
        result = messagebox.askyesno(
            "Подтверждение",
            f"Вы уверены, что хотите перенести ВСЕ ссылки?\n\n"
            f"ИСТОЧНИК (ID: {source_child_id})\n"
            f"ПОЛУЧАТЕЛЬ (ID: {target_child_id})\n\n"
            f"Все ссылки из ИСТОЧНИКА будут заменены на ПОЛУЧАТЕЛЯ.\n"
            f"Существующие ссылки в ПОЛУЧАТЕЛЕ останутся без изменений.\n\n"
            f"Продолжить?"
        )

        if not result:
            return

        # Подключаемся к БД
        db_path = os.path.join('..', 'db.sqlite3')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Список таблиц для исключения
        exclude_tables = [
            'accounts_user_groups',
            'accounts_user_user_permissions',
            'accounts_useractionlog',
            'auth_group',
            'auth_group_permissions',
            'auth_permission',
            'children_childlist',
            'children_child'  # Исключаем саму таблицу детей
        ]

        # Получаем все таблицы
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            AND name NOT LIKE 'sqlite_%'
            AND name NOT LIKE 'django_%'
            ORDER BY name;
        """)

        tables = cursor.fetchall()

        updated_count = 0
        updated_tables = []

        for table in tables:
            table_name = table[0]

            if table_name in exclude_tables:
                continue

            # Получаем структуру таблицы
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()

            for col in columns:
                col_name = col[1]
                if 'child' in col_name.lower() or col_name.endswith('_id'):
                    try:
                        # Обновляем записи: заменяем source_child_id на target_child_id
                        query = f"UPDATE '{table_name}' SET {col_name} = ? WHERE {col_name} = ?"
                        cursor.execute(query, (target_child_id, source_child_id))
                        count = cursor.rowcount

                        if count > 0:
                            updated_count += count
                            updated_tables.append(f"{table_name}.{col_name}: {count} записей")
                    except Exception as e:
                        print(f"Ошибка в таблице {table_name}: {e}")

        # Сохраняем изменения
        conn.commit()
        conn.close()

        # Выводим результат
        result_text = f"✅ ПЕРЕНОС ВЫПОЛНЕН УСПЕШНО!\n\n"
        result_text += f"ИСТОЧНИК (ID: {source_child_id}) → ПОЛУЧАТЕЛЬ (ID: {target_child_id})\n"
        result_text += f"{'=' * 60}\n"
        result_text += f"Всего обновлено записей: {updated_count}\n\n"

        if updated_tables:
            result_text += f"Обновленные таблицы:\n"
            for table in updated_tables:
                result_text += f"  • {table}\n"
        else:
            result_text += f"Ссылок для переноса не найдено.\n"

        messagebox.showinfo("Результат переноса", result_text)

        # Обновляем отображение ссылок
        show_child_links('source')
        show_child_links('target')

        status_label_replace.config(text=f"✅ Перенос выполнен! Обновлено записей: {updated_count}")

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось выполнить перенос: {str(e)}")



def clear_text():
    """Очищает текстовое поле"""
    text_area.delete(1.0, tk.END)


def button2_func():
    """Функция для второй кнопки (пока заглушка)"""
    show_project_structure()


def button3_func():
    """Функция для третьей кнопки (пока заглушка)"""
    messagebox.showinfo("Инфо", "Функция в разработке")


# Создаем главное окно
root = tk.Tk()
root.title("Управление базой данных")
root.geometry("1200x840")

# Создаем Notebook (вкладки)
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True, padx=10, pady=10)


# ========== Вкладка 1: Структура БД ==========
tab_structure = ttk.Frame(notebook)
notebook.add(tab_structure, text="📊 Структура базы данных")

# Создаем фрейм для кнопок на первой вкладке
button_frame1 = ttk.Frame(tab_structure)
button_frame1.pack(pady=10)

# Кнопка 1: Просмотр структуры базы данных
btn_structure = ttk.Button(button_frame1, text="Просмотр структуры базы данных",
                           command=show_structure, width=30)
btn_structure.pack(side=tk.LEFT, padx=5)

# Кнопка очистки на первой вкладке
btn_clear = ttk.Button(button_frame1, text="Очистить", command=clear_text, width=15)
btn_clear.pack(side=tk.LEFT, padx=5)

# Текстовое поле для структуры базы данных
text_area = scrolledtext.ScrolledText(tab_structure, wrap=tk.WORD, width=140, height=45, font=("Courier", 10))
text_area.pack(pady=10, padx=10)

# Заголовок первой вкладки
label1 = ttk.Label(tab_structure, text="Структура базы данных", font=("Arial", 12, "bold"))
label1.pack()


# ========== Вкладка 2: Структура проекта ==========
tab_project = ttk.Frame(notebook)
notebook.add(tab_project, text="📁 Структура проекта")

# Создаем фрейм для кнопок на второй вкладке
button_frame2 = ttk.Frame(tab_project)
button_frame2.pack(pady=10)

# Кнопка 2: Просмотр структуры проекта
btn_button2 = ttk.Button(button_frame2, text="Просмотр структуры проекта",
                         command=show_project_structure, width=30)
btn_button2.pack(side=tk.LEFT, padx=5)

# Кнопка очистки на второй вкладке
btn_clear_project = ttk.Button(button_frame2, text="Очистить",
                               command=lambda: text_area_project.delete(1.0, tk.END), width=15)
btn_clear_project.pack(side=tk.LEFT, padx=5)

# Текстовое поле для структуры проекта
text_area_project = scrolledtext.ScrolledText(tab_project, wrap=tk.WORD, width=140, height=45, font=("Courier", 10))
text_area_project.pack(pady=10, padx=10)

# Заголовок второй вкладки
label2 = ttk.Label(tab_project, text="Структура проекта", font=("Arial", 12, "bold"))
label2.pack()


# ========== Вкладка 3: Содержимое таблиц ==========
tab_content = ttk.Frame(notebook)
notebook.add(tab_content, text="📋 Содержимое таблиц")

# Верхняя панель для выбора таблицы
top_frame = ttk.Frame(tab_content)
top_frame.pack(pady=10, fill='x', padx=10)

ttk.Label(top_frame, text="Выберите таблицу:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

table_combobox = ttk.Combobox(top_frame, width=40, font=("Arial", 10))
table_combobox.pack(side=tk.LEFT, padx=5)

btn_load = ttk.Button(top_frame, text="Загрузить", command=view_table_content, width=15)
btn_load.pack(side=tk.LEFT, padx=5)

btn_refresh = ttk.Button(top_frame, text="Обновить", command=refresh_table, width=15)
btn_refresh.pack(side=tk.LEFT, padx=5)

btn_export = ttk.Button(top_frame, text="📎 Выгрузить в Excel", command=export_to_excel, width=20)
btn_export.pack(side=tk.LEFT, padx=5)

# Статусная строка
status_label = ttk.Label(tab_content, text="Выберите таблицу для просмотра", relief="sunken", anchor="w")
status_label.pack(fill='x', padx=10, pady=5)

# Создаем фрейм с прокруткой для таблицы
tree_frame = ttk.Frame(tab_content)
tree_frame.pack(fill='both', expand=True, padx=10, pady=5)

# Добавляем скроллбары
vsb = ttk.Scrollbar(tree_frame, orient="vertical")
hsb = ttk.Scrollbar(tree_frame, orient="horizontal")
tree = ttk.Treeview(tree_frame, yscrollcommand=vsb.set, xscrollcommand=hsb.set)
vsb.config(command=tree.yview)
hsb.config(command=tree.xview)

# Размещаем элементы
tree.grid(row=0, column=0, sticky="nsew")
vsb.grid(row=0, column=1, sticky="ns")
hsb.grid(row=1, column=0, sticky="ew")

tree_frame.grid_rowconfigure(0, weight=1)
tree_frame.grid_columnconfigure(0, weight=1)

# Загружаем список таблиц при запуске
load_tables_for_combobox()


# ========== Вкладка 4: Поиск ссылок по ребенку ==========
tab_search = ttk.Frame(notebook)
notebook.add(tab_search, text="🔍 Поиск ссылок по ребенку")

# Верхняя панель для выбора ребенка
top_frame_search = ttk.Frame(tab_search)
top_frame_search.pack(pady=10, fill='x', padx=10)

ttk.Label(top_frame_search, text="Выберите ID ребенка:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

# Выпадающий список для ID ребенка
child_id_combobox = ttk.Combobox(top_frame_search, width=30, font=("Arial", 10))
child_id_combobox.pack(side=tk.LEFT, padx=5)

# Кнопки
btn_search = ttk.Button(top_frame_search, text="🔍 Найти ссылки", command=search_child_links, width=20)
btn_search.pack(side=tk.LEFT, padx=5)

btn_delete = ttk.Button(top_frame_search, text="🗑️ УДАЛИТЬ ребенка", command=delete_child, width=20, state='disabled')
btn_delete.pack(side=tk.LEFT, padx=5)

btn_clear_search = ttk.Button(top_frame_search, text="Очистить",
                              command=lambda: text_area_search.delete(1.0, tk.END), width=15)
btn_clear_search.pack(side=tk.LEFT, padx=5)

# Статусная строка для поиска
status_label_search = ttk.Label(tab_search, text="Выберите ID ребенка для поиска", relief="sunken", anchor="w")
status_label_search.pack(fill='x', padx=10, pady=5)

# Текстовое поле для результатов поиска
text_area_search = scrolledtext.ScrolledText(tab_search, wrap=tk.WORD, width=140, height=40, font=("Courier", 10))
text_area_search.pack(pady=10, padx=10)

# Заголовок
label_search = ttk.Label(tab_search, text="Результаты поиска ссылок на ребенка", font=("Arial", 12, "bold"))
label_search.pack()

# Загружаем список детей
load_child_ids()


# ========== Вкладка 5: Замена ссылок ==========
tab_replace = ttk.Frame(notebook)
notebook.add(tab_replace, text="🔄 Замена ссылок")

# Создаем фрейм для левой и правой частей
left_right_frame = ttk.Frame(tab_replace)
left_right_frame.pack(fill='both', expand=True, padx=10, pady=10)

# Левая часть (Источник)
left_frame = ttk.LabelFrame(left_right_frame, text="📤 ИСТОЧНИК - Откуда переносим", padding=10)
left_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=5)

# Правая часть (Получатель)
right_frame = ttk.LabelFrame(left_right_frame, text="📥 ПОЛУЧАТЕЛЬ - Куда переносим", padding=10)
right_frame.pack(side=tk.RIGHT, fill='both', expand=True, padx=5)

# ===== Левая часть (Источник) =====
# Выбор ребенка-источника
ttk.Label(left_frame, text="Выберите ребенка-ИСТОЧНИК:", font=("Arial", 10, "bold")).pack(anchor="w", pady=5)

source_child_frame = ttk.Frame(left_frame)
source_child_frame.pack(fill='x', pady=5)

source_child_combobox = ttk.Combobox(source_child_frame, width=50, font=("Arial", 10))
source_child_combobox.pack(side=tk.LEFT, padx=5)

btn_load_source = ttk.Button(source_child_frame, text="📊 Показать ссылки",
                             command=lambda: show_child_links('source'), width=20)
btn_load_source.pack(side=tk.LEFT, padx=5)

# Текстовое поле для результатов источника
ttk.Label(left_frame, text="Ссылки на ребенка-ИСТОЧНИКА:", font=("Arial", 9, "bold")).pack(anchor="w", pady=5)
text_area_source = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, width=60, height=35, font=("Courier", 9))
text_area_source.pack(fill='both', expand=True, pady=5)

# ===== Правая часть (Получатель) =====
# Выбор ребенка-получателя
ttk.Label(right_frame, text="Выберите ребенка-ПОЛУЧАТЕЛЬ:", font=("Arial", 10, "bold")).pack(anchor="w", pady=5)

target_child_frame = ttk.Frame(right_frame)
target_child_frame.pack(fill='x', pady=5)

target_child_combobox = ttk.Combobox(target_child_frame, width=50, font=("Arial", 10))
target_child_combobox.pack(side=tk.LEFT, padx=5)

btn_load_target = ttk.Button(target_child_frame, text="📊 Показать ссылки",
                             command=lambda: show_child_links('target'), width=20)
btn_load_target.pack(side=tk.LEFT, padx=5)

# Текстовое поле для результатов получателя
ttk.Label(right_frame, text="Ссылки на ребенка-ПОЛУЧАТЕЛЯ:", font=("Arial", 9, "bold")).pack(anchor="w", pady=5)
text_area_target = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, width=60, height=35, font=("Courier", 9))
text_area_target.pack(fill='both', expand=True, pady=5)

# Нижняя панель с кнопкой переноса
bottom_frame = ttk.Frame(tab_replace)
bottom_frame.pack(fill='x', padx=10, pady=10)

btn_merge = ttk.Button(bottom_frame, text="🔄 ПЕРЕНЕСТИ ССЫЛКИ (Заменить получателя на источник)",
                       command=replace_links, width=60)
btn_merge.pack(pady=10)

# Статусная строка
status_label_replace = ttk.Label(tab_replace, text="Выберите ребенка-ИСТОЧНИК и ребенка-ПОЛУЧАТЕЛЬ",
                                  relief="sunken", anchor="w")
status_label_replace.pack(fill='x', padx=10, pady=5)

# Загружаем списки детей для левой и правой части
load_children_for_combobox(source_child_combobox, 'child_data')
load_children_for_combobox(target_child_combobox, 'child_data')



# Запускаем главный цикл
root.mainloop()