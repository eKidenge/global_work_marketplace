# apps/super_admin/urls.py
from django.urls import path
from . import views

app_name = 'super_admin'

urlpatterns = [
    # Dashboard
    path('', views.SuperAdminDashboard.as_view(), name='dashboard'),
    path('login/', views.SuperAdminLogin.as_view(), name='login'),
    path('logout/', views.SuperAdminLogout.as_view(), name='logout'),
    
    # Agent Management
    path('agents/', views.AgentManagement.as_view(), name='agents'),
    path('agents/<uuid:agent_id>/', views.AgentDetailView.as_view(), name='agent_detail'),
    path('agents/<uuid:agent_id>/edit/', views.AgentEditView.as_view(), name='agent_edit'),
    path('agents/<uuid:agent_id>/delete/', views.AgentDeleteView.as_view(), name='agent_delete'),
    path('agents/<uuid:agent_id>/activate/', views.AgentActivateView.as_view(), name='agent_activate'),
    path('agents/<uuid:agent_id>/deactivate/', views.AgentDeactivateView.as_view(), name='agent_deactivate'),
    path('agents/create/', views.AgentCreateView.as_view(), name='agent_create'),
    
    # Task Management
    path('tasks/', views.TaskManagement.as_view(), name='tasks'),
    path('tasks/<uuid:task_id>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('tasks/<uuid:task_id>/cancel/', views.TaskCancelView.as_view(), name='task_cancel'),
    path('tasks/<uuid:task_id>/reassign/', views.TaskReassignView.as_view(), name='task_reassign'),
    path('tasks/<uuid:task_id>/force-complete/', views.TaskForceCompleteView.as_view(), name='task_force_complete'),
    path('tasks/<uuid:task_id>/force-fail/', views.TaskForceFailView.as_view(), name='task_force_fail'),
    
    # Payment Management
    path('payments/', views.PaymentManagement.as_view(), name='payments'),
    path('payments/transactions/', views.TransactionListView.as_view(), name='transactions'),
    path('payments/transactions/<uuid:transaction_id>/', views.TransactionDetailView.as_view(), name='transaction_detail'),
    path('payments/transactions/<uuid:transaction_id>/refund/', views.TransactionRefundView.as_view(), name='transaction_refund'),
    path('payments/wallets/', views.WalletListView.as_view(), name='wallets'),
    path('payments/wallets/<uuid:wallet_id>/', views.WalletDetailView.as_view(), name='wallet_detail'),
    path('payments/escrow/', views.EscrowListView.as_view(), name='escrow_list'),
    path('payments/escrow/<uuid:escrow_id>/', views.EscrowDetailView.as_view(), name='escrow_detail'),
    path('payments/escrow/<uuid:escrow_id>/release/', views.EscrowReleaseView.as_view(), name='escrow_release'),
    path('payments/escrow/<uuid:escrow_id>/dispute/', views.EscrowDisputeView.as_view(), name='escrow_dispute'),
    
    # System Settings
    path('settings/', views.SystemSettingsView.as_view(), name='settings'),
    path('settings/general/', views.GeneralSettingsView.as_view(), name='general_settings'),
    path('settings/payments/', views.PaymentSettingsView.as_view(), name='payment_settings'),
    path('settings/agents/', views.AgentSettingsView.as_view(), name='agent_settings'),
    path('settings/tasks/', views.TaskSettingsView.as_view(), name='task_settings'),
    path('settings/security/', views.SecuritySettingsView.as_view(), name='security_settings'),
    path('settings/email/', views.EmailSettingsView.as_view(), name='email_settings'),
    path('settings/<str:key>/update/', views.SettingUpdateView.as_view(), name='setting_update'),
    
    # Analytics
    path('analytics/', views.AnalyticsView.as_view(), name='analytics'),
    path('analytics/metrics/', views.MetricsView.as_view(), name='metrics'),
    path('analytics/reports/', views.ReportsView.as_view(), name='reports'),
    path('analytics/alerts/', views.AlertsView.as_view(), name='alerts'),
    path('analytics/alerts/<uuid:alert_id>/resolve/', views.AlertResolveView.as_view(), name='alert_resolve'),
    path('analytics/export/<str:report_type>/', views.ExportReportView.as_view(), name='export_report'),
    
    # Admin Users
    path('admin-users/', views.AdminUserManagement.as_view(), name='admin_users'),
    path('admin-users/create/', views.AdminUserCreateView.as_view(), name='admin_user_create'),
    path('admin-users/<uuid:admin_id>/edit/', views.AdminUserEditView.as_view(), name='admin_user_edit'),
    path('admin-users/<uuid:admin_id>/delete/', views.AdminUserDeleteView.as_view(), name='admin_user_delete'),
    path('admin-users/<uuid:admin_id>/role/', views.AdminUserRoleUpdateView.as_view(), name='admin_user_role'),
    
    # Audit Logs
    path('audit-logs/', views.AuditLogView.as_view(), name='audit_logs'),
    path('audit-logs/<uuid:log_id>/', views.AuditLogDetailView.as_view(), name='audit_log_detail'),
    path('audit-logs/export/', views.AuditLogExportView.as_view(), name='audit_log_export'),
    
    # Reports
    path('reports/daily/', views.DailyReportView.as_view(), name='daily_report'),
    path('reports/weekly/', views.WeeklyReportView.as_view(), name='weekly_report'),
    path('reports/monthly/', views.MonthlyReportView.as_view(), name='monthly_report'),
    path('reports/agents/', views.AgentReportView.as_view(), name='agent_report'),
    path('reports/financial/', views.FinancialReportView.as_view(), name='financial_report'),
    path('reports/tasks/', views.TaskReportView.as_view(), name='task_report'),
    path('reports/download/<str:report_id>/', views.DownloadReportView.as_view(), name='download_report'),
    
    # Announcements
    path('announcements/', views.AnnouncementListView.as_view(), name='announcements'),
    path('announcements/create/', views.AnnouncementCreateView.as_view(), name='announcement_create'),
    path('announcements/<uuid:announcement_id>/edit/', views.AnnouncementEditView.as_view(), name='announcement_edit'),
    path('announcements/<uuid:announcement_id>/delete/', views.AnnouncementDeleteView.as_view(), name='announcement_delete'),
    path('announcements/<uuid:announcement_id>/toggle/', views.AnnouncementToggleView.as_view(), name='announcement_toggle'),
    
    # Disputes Management
    path('disputes/', views.DisputeListView.as_view(), name='disputes'),
    path('disputes/<uuid:dispute_id>/', views.DisputeDetailView.as_view(), name='dispute_detail'),
    path('disputes/<uuid:dispute_id>/resolve/', views.DisputeResolveView.as_view(), name='dispute_resolve'),
    path('disputes/<uuid:dispute_id>/escalate/', views.DisputeEscalateView.as_view(), name='dispute_escalate'),
    
    # System Health
    path('health/', views.SystemHealthView.as_view(), name='system_health'),
    path('health/check/', views.HealthCheckView.as_view(), name='health_check'),
    path('status/', views.SystemStatusView.as_view(), name='system_status'),
    
    # Backup & Restore
    path('backup/', views.BackupView.as_view(), name='backup'),
    path('backup/create/', views.CreateBackupView.as_view(), name='create_backup'),
    path('backup/download/<str:backup_file>/', views.DownloadBackupView.as_view(), name='download_backup'),
    path('backup/restore/<str:backup_file>/', views.RestoreBackupView.as_view(), name='restore_backup'),
    
    # API Keys Management
    path('api-keys/', views.APIKeyListView.as_view(), name='api_keys'),
    path('api-keys/create/', views.APIKeyCreateView.as_view(), name='api_key_create'),
    path('api-keys/<uuid:key_id>/revoke/', views.APIKeyRevokeView.as_view(), name='api_key_revoke'),
    
    # Webhooks Management
    path('webhooks/', views.WebhookListView.as_view(), name='webhooks'),
    path('webhooks/create/', views.WebhookCreateView.as_view(), name='webhook_create'),
    path('webhooks/<uuid:webhook_id>/edit/', views.WebhookEditView.as_view(), name='webhook_edit'),
    path('webhooks/<uuid:webhook_id>/delete/', views.WebhookDeleteView.as_view(), name='webhook_delete'),
    path('webhooks/<uuid:webhook_id>/test/', views.WebhookTestView.as_view(), name='webhook_test'),
    
    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notifications'),
    path('notifications/mark-read/', views.MarkNotificationsReadView.as_view(), name='mark_notifications_read'),
    
    # Profile
    path('profile/', views.AdminProfileView.as_view(), name='profile'),
    path('profile/edit/', views.AdminProfileEditView.as_view(), name='profile_edit'),
    path('profile/change-password/', views.AdminChangePasswordView.as_view(), name='change_password'),
]