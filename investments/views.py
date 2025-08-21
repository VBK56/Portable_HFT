from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django_user_agents.utils import get_user_agent

def home_redirect(request):
    """Redirect to unified dashboard"""
    return redirect('dashboard')

@login_required
def unified_dashboard(request):
    """Единая точка входа с автоопределением устройства"""
    user_agent = get_user_agent(request)
    
    # Логируем для отладки
    device_type = "mobile" if user_agent.is_mobile else "tablet" if user_agent.is_tablet else "desktop"
    print(f"Device detected: {device_type}")
    
    # Пока используем один шаблон для всех устройств
    # В будущем можно будет добавить разные шаблоны
    template = 'pwa/v3/mobile_app_v3.html'
    
    context = {
        'device_type': device_type,
        'is_mobile': user_agent.is_mobile,
        'is_tablet': user_agent.is_tablet,
        'is_desktop': not (user_agent.is_mobile or user_agent.is_tablet)
    }
    
    return render(request, template, context)

def v3_desktop(request):
    """Legacy endpoint - redirect to unified dashboard"""
    return redirect('dashboard')

def manifest_view(request):
    """PWA manifest"""
    manifest = {
        "name": "Investment Tracker v3.0",
        "short_name": "InvestTracker",
        "start_url": "/dashboard/",  # Изменили на /dashboard/
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#007cba",
        "icons": [
            {
                "src": "/static/icon-192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/static/icon-512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    }
    return JsonResponse(manifest)

def service_worker_view(request):
    """Service Worker"""
    sw_content = """
    console.log('v3.0 Service Worker');
    
    self.addEventListener('install', event => {
        console.log('SW installed');
    });
    
    self.addEventListener('activate', event => {
        console.log('SW activated');
    });
    """
    return HttpResponse(sw_content, content_type='application/javascript')