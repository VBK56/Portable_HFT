# investments/api/urls.py

from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    # Проекты
    path('projects/', views.ProjectListCreateView.as_view(), name='project-list'),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view(), name='project-detail'),
    # ЗАКОММЕНТИРУЕМ эту строку пока не добавим функцию в views.py
    path('projects/<int:project_id>/detail/', views.project_detail_api, name='project-detail-api'),
    path('projects/create/', views.create_project, name='project-create'),
    
    # Транзакции
    path('transactions/', views.TransactionListCreateView.as_view(), name='transaction-list'),
    path('transactions/create/', views.create_transaction, name='transaction-create'),
    
    # Портфель
    path('portfolio/summary/', views.portfolio_summary, name='portfolio-summary'),
    
    # Аналитика
    path('analytics/', views.analytics_view, name='analytics'),
]