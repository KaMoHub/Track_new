"""
WSGI config for track project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'track.settings')

application = get_wsgi_application()



# или так
# import os
# import sys
#
# # Добавляем путь к проекту
# path = '/путь/track_new'
# if path not in sys.path:
#     sys.path.append(path)
#
# # Указываем настройки Django
# os.environ['DJANGO_SETTINGS_MODULE'] = 'track.settings'
#
# # Загружаем приложение
# from django.core.wsgi import get_wsgi_application
# application = get_wsgi_application()