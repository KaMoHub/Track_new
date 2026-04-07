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
    """Ищет все ссылки на выбранного ребенка во всех таблицах"""
    try:
        selected_display = child_id_combobox.get()
        if not selected_display:
            messagebox.showwarning("Предупреждение", "Выберите ребенка!")
            return

        # Получаем ID ребенка из выбранной строки
        if hasattr(child_id_combobox, 'child_data') and selected_display in child_id_combobox.child_data:
            selected_child_id = child_id_combobox.child_data[selected_display]
        else:
            # Если словаря нет, пытаемся извлечь ID из строки
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
        results.append("=" * 110)
        results.append(f"🔍 ПОИСК ССЫЛОК НА РЕБЕНКА")
        results.append(f"   ID: {selected_child_id}")
        results.append(f"   ФИО: {child_fio}")
        results.append("=" * 110)

        found_count = 0

        for table in tables:
            table_name = table[0]

            # Пропускаем исключенные таблицы
            if table_name in exclude_tables:
                continue

            # Получаем структуру таблицы
            cursor.execute(f"PRAGMA table_info('{table_name}')")
            columns = cursor.fetchall()

            # Ищем поля, которые могут ссылаться на ребенка
            child_links = []
            for col in columns:
                col_name = col[1]
                # Ищем поля с 'child' в названии или заканчивающиеся на '_id'
                if 'child' in col_name.lower() or col_name.endswith('_id'):
                    # Проверяем, есть ли в этой колонке значение selected_child_id
                    try:
                        query = f"SELECT * FROM '{table_name}' WHERE {col_name} = ?"
                        cursor.execute(query, (selected_child_id,))
                        rows = cursor.fetchall()

                        if rows:
                            child_links.append({
                                'column': col_name,
                                'rows': rows,
                                'row_count': len(rows)
                            })
                    except:
                        pass

            if child_links:
                found_count += 1
                results.append(f"\n{'=' * 110}")
                results.append(f"📋 ТАБЛИЦА: {table_name}")
                results.append(f"{'=' * 110}")

                for link in child_links:
                    results.append(f"\n  🔗 Поле: {link['column']}")
                    results.append(f"  📊 Найдено записей: {link['row_count']}")
                    results.append(f"  📝 Содержимое:")

                    # Получаем названия колонок для вывода
                    cursor.execute(f"PRAGMA table_info('{table_name}')")
                    all_columns = cursor.fetchall()
                    col_names = [c[1] for c in all_columns]

                    # Выводим каждую запись
                    for row in link['rows']:
                        row_str = "      "
                        for i, value in enumerate(row):
                            if i < len(col_names):
                                row_str += f"{col_names[i]}: {value} | "
                        results.append(row_str)

        if found_count == 0:
            results.append(f"\n❌ Ссылок на ребенка не найдено")
        else:
            results.append(f"\n✅ Всего найдено таблиц со ссылками: {found_count}")

        conn.close()

        # Выводим результаты
        result_text = "\n".join(results)
        text_area_search.insert(1.0, result_text)

        status_label_search.config(text=f"Поиск завершен. Найдено таблиц: {found_count}")

    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось выполнить поиск: {str(e)}")


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
child_id_combobox = ttk.Combobox(top_frame_search, width=20, font=("Arial", 10))
child_id_combobox.pack(side=tk.LEFT, padx=5)

# Загружаем список ID детей
load_child_ids()

btn_search = ttk.Button(top_frame_search, text="🔍 Найти ссылки", command=search_child_links, width=20)
btn_search.pack(side=tk.LEFT, padx=5)

btn_clear_search = ttk.Button(top_frame_search, text="Очистить",
                              command=lambda: text_area_search.delete(1.0, tk.END), width=15)
btn_clear_search.pack(side=tk.LEFT, padx=5)

# Статусная строка для поиска
status_label_search = ttk.Label(tab_search, text="Выберите ID ребенка для поиска", relief="sunken", anchor="w")
status_label_search.pack(fill='x', padx=10, pady=5)

# Текстовое поле для результатов поиска
text_area_search = scrolledtext.ScrolledText(tab_search, wrap=tk.WORD, width=140, height=45, font=("Courier", 10))
text_area_search.pack(pady=10, padx=10)

# Заголовок
label_search = ttk.Label(tab_search, text="Результаты поиска ссылок на ребенка", font=("Arial", 12, "bold"))
label_search.pack()

# Запускаем главный цикл
root.mainloop()