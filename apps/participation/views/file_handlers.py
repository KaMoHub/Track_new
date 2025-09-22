# apps/participation/views/file_handlers.py
"""Обработчики файлов для участия в конкурсах"""
import os
import uuid
from django.conf import settings
from ..models import UploadedFile

# apps/participation/views/file_handlers.py (обновляем handle_file_upload)
"""Обработчики файлов для участия в конкурсах"""
def handle_file_upload(uploaded_file_instance, file_upload, user):
    """
    Обработка загрузки файла

    Args:
        uploaded_file_instance: Экземпляр UploadedFile (уже созданный)
        file_upload: Загружаемый файл
        user: Пользователь, загружающий файл

    Returns:
        UploadedFile: Созданная запись файла
    """
    print(f"DEBUG: Начало загрузки файла: {file_upload.name}")

    # Генерируем уникальное имя файла
    file_extension = os.path.splitext(file_upload.name)[1].lower()
    stored_name = f"{uuid.uuid4()}{file_extension}"
    uploaded_file_instance.stored_name = stored_name
    print(f"DEBUG: Уникальное имя файла: {stored_name}")

    # Определяем правильный путь для сохранения файла
    if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
        upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads', 'participation_files')
    else:
        upload_dir = os.path.join('media', 'uploads', 'participation_files')

    # Создаем директорию, если она не существует
    os.makedirs(upload_dir, exist_ok=True)
    print(f"DEBUG: Директория для загрузки: {upload_dir}")

    # Абсолютный путь для физического сохранения
    absolute_file_path = os.path.join(upload_dir, stored_name)
    uploaded_file_instance.file_path = absolute_file_path
    print(f"DEBUG: Абсолютный путь для сохранения: {absolute_file_path}")

    try:
        # Сохраняем файл в файловой системе
        with open(absolute_file_path, 'wb+') as destination:
            for chunk in file_upload.chunks():
                destination.write(chunk)
        print(f"DEBUG: Файл успешно сохранен по пути: {absolute_file_path}")

        # Сохраняем запись о файле в БД
        uploaded_file_instance.save()
        print(f"DEBUG: Запись о файле сохранена в БД, ID={uploaded_file_instance.id}")

        return uploaded_file_instance

    except Exception as e:
        print(f"DEBUG: Ошибка при сохранении файла: {e}")
        # Удаляем файл, если не удалось сохранить запись в БД
        if os.path.exists(absolute_file_path):
            os.remove(absolute_file_path)
        raise e

def get_file_paths(uploaded_file):
    """
    Получение возможных путей к файлу

    Args:
        uploaded_file: Запись загруженного файла

    Returns:
        list: Список возможных путей к файлу
    """
    from django.conf import settings

    paths = []

    # Путь из БД
    if uploaded_file.file_path:
        paths.append(uploaded_file.file_path)

    # Путь в MEDIA_ROOT
    if hasattr(settings, 'MEDIA_ROOT') and settings.MEDIA_ROOT:
        media_path = os.path.join(settings.MEDIA_ROOT, 'uploads', 'participation_files', uploaded_file.stored_name)
        paths.append(media_path)

    # Относительный путь
    relative_path = os.path.join('media', 'uploads', 'participation_files', uploaded_file.stored_name)
    paths.append(relative_path)

    return paths


def find_file(uploaded_file):
    """
    Поиск файла в файловой системе

    Args:
        uploaded_file: Запись загруженного файла

    Returns:
        str or None: Путь к найденному файлу или None
    """
    paths = get_file_paths(uploaded_file)

    for path in paths:
        if os.path.exists(path):
            return path

    return None