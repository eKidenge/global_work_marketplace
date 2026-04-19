# apps/super_admin/urls.py
from django.urls import path
from . import views

app_name = 'super_admin'

urlpatterns = [
    # Dashboard
    path('', views.SuperAdminDashboard.as_view(), name='dashboard'),
    
    # Agent Management
    path('agents/', views.AgentManagement.as_view(), name='agents'),
    path('agents/<uuid:agent_id>/', views.AgentDetailView.as_view(), name='agent_detail'),
    
    # Task Management
    path('tasks/', views.TaskManagement.as_view(), name='tasks'),
    path('tasks/<uuid:task_id>/', views.TaskDetailView.as_view(), name='task_detail'),
    
    # Payment Management
    path('payments/', views.PaymentManagement.as_view(), name='payments'),
    path('payments/<uuid:transaction_id>/', views.PaymentDetailView.as_view(), name='payment_detail'),
    
    # System Settings
    path('settings/', views.SystemSettingsView.as_view(), name='settings'),
    
    # Analytics
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    
    # Admin Users
    path('admin-users/', views.AdminUserManagement.as_view(), name='admin_users'),
    
    # Audit Logs
    path('audit-logs/', views.AuditLogView.as_view(), name='audit_logs'),
    
    # Reports
    path('reports/daily/', views.DailyReportView.as_view(), name='daily_report'),
    path('reports/agents/', views.AgentReportView.as_view(), name='agent_report'),
    path('reports/financial/', views.FinancialReportView.as_view(), name='financial_report'),
]