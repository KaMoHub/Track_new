# apps/dashboard/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Главная страница приложения"""
    template_name = 'dashboard/home.html'


class MapView(TemplateView):
    """Страница карты маршрута"""
    template_name = 'dashboard/map.html'

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


def home(request):
    """Главная страница приложения"""
    return render(request, 'dashboard/home.html')


@login_required
def map_view(request):
    """Страница карты маршрута"""
    return render(request, 'dashboard/map.html')
