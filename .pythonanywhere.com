# Файл .pythonanywhere.com
PYTHON_VERSION=3.10  # Укажите вашу версию Python
WSGI_FILE=/path/to/your/project/wsgi.py  # Этот путь мы настроим позже на самом PA
# Пока просто оставьте эти строки как есть, мы их скопируем позже.