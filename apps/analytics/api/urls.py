# apps/analytics/api/urls.py
from django.urls import path
from . import views

app_name = 'analytics_api'

urlpatterns = [
    path('metrics/', views.APIMetricsView.as_view(), name='api_metrics'),
    path('dashboard/', views.APIDashboardView.as_view(), name='api_dashboard'),
    path('reports/', views.APIReportsView.as_view(), name='api_reports'),
]