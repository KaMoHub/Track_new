# track/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.dashboard.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('children/', include('apps.children.urls')),  # Убедитесь, что путь правильный
    path('events/', include('apps.events.urls')),  # Добавляем events
    path('participation/', include('apps.participation.urls')),  # Добавляем participation
    path('admin-dashboard/', include('apps.admin_tools.urls')),
]

# Для разработки - обслуживание статических и медиа файлов
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)