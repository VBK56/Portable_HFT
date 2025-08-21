from django.contrib import admin
from django.urls import path, include
from investments import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Новая единая точка входа
    path('', views.home_redirect, name='home'),
    path('dashboard/', views.unified_dashboard, name='dashboard'),
    
    # Legacy endpoints (для обратной совместимости)
    path('v3/', views.v3_desktop, name='v3_desktop'),
    
    # API
    path('api/', include('investments.api.urls')),
    
    # PWA
    path('manifest.json', views.manifest_view, name='manifest'),
    path('sw.js', views.service_worker_view, name='service_worker'),
]