# apps/analytics/urls.py
from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # Analytics dashboard
    path('', views.AnalyticsDashboardView.as_view(), name='dashboard'),
    path('overview/', views.OverviewView.as_view(), name='overview'),
    
    # Metrics
    path('metrics/', views.MetricsView.as_view(), name='metrics'),
    path('metrics/<str:metric_name>/', views.MetricDetailView.as_view(), name='metric_detail'),
    path('metrics/export/', views.ExportMetricsView.as_view(), name='export_metrics'),
    
    # Charts data (API endpoints)
    path('charts/tasks/', views.TasksChartDataView.as_view(), name='tasks_chart'),
    path('charts/revenue/', views.RevenueChartDataView.as_view(), name='revenue_chart'),
    path('charts/agents/', views.AgentsChartDataView.as_view(), name='agents_chart'),
    path('charts/performance/', views.PerformanceChartDataView.as_view(), name='performance_chart'),
    
    # Reports
    path('reports/', views.ReportListView.as_view(), name='reports'),
    path('reports/create/', views.CreateReportView.as_view(), name='create_report'),
    path('reports/<uuid:report_id>/', views.ReportDetailView.as_view(), name='report_detail'),
    path('reports/<uuid:report_id>/download/', views.DownloadReportView.as_view(), name='download_report'),
    path('reports/<uuid:report_id>/schedule/', views.ScheduleReportView.as_view(), name='schedule_report'),
    
    # Alerts
    path('alerts/', views.AlertListView.as_view(), name='alerts'),
    path('alerts/<uuid:alert_id>/', views.AlertDetailView.as_view(), name='alert_detail'),
    path('alerts/<uuid:alert_id>/resolve/', views.ResolveAlertView.as_view(), name='resolve_alert'),
    path('alerts/settings/', views.AlertSettingsView.as_view(), name='alert_settings'),
    
    # Real-time stats
    path('stats/realtime/', views.RealtimeStatsView.as_view(), name='realtime_stats'),
    path('stats/agents/', views.AgentStatsView.as_view(), name='agent_stats'),
    path('stats/tasks/', views.TaskStatsView.as_view(), name='task_stats'),
    path('stats/payments/', views.PaymentStatsView.as_view(), name='payment_stats'),
]