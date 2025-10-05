import os
from pathlib import Path


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
        ignore_dirs = ['.git', '__pycache__', '.venv', 'venv', 'env', 'node_modules']

    if ignore_files is None:
        ignore_files = ['.DS_Store', 'thumbs.db']

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


def get_simple_structure(root_dir, output_file):
    """
    Упрощенная версия без древовидной структуры
    """
    root_path = Path(root_dir)

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Структура проекта: {root_path.name}\n")
        f.write("=" * 50 + "\n\n")

        for root, dirs, files in os.walk(root_dir):
            # Пропускаем скрытые папки
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            level = root.replace(root_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            f.write(f"{indent}{os.path.basename(root)}/\n")

            sub_indent = ' ' * 2 * (level + 1)
            for file in files:
                if not file.startswith('.'):  # Пропускаем скрытые файлы
                    f.write(f"{sub_indent}{file}\n")


# Пример использования
if __name__ == "__main__":
    # Получаем структуру текущей директории
    project_dir = "."  # Можно указать любой путь
    output_filename = "project_structure.txt"

    # Используем подробную версию с древовидной структурой
    get_project_structure(project_dir, output_filename)

    print(f"Структура проекта записана в файл: {output_filename}")

    # Альтернативно: используем упрощенную версию
    # get_simple_structure(project_dir, "simple_structure.txt")