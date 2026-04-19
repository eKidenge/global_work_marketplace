# apps/agents/urls.py
from django.urls import path
from . import views

app_name = 'agents'

urlpatterns = [
    # Agent listing and details
    path('', views.AgentListView.as_view(), name='agent_list'),
    path('<uuid:agent_id>/', views.AgentDetailView.as_view(), name='agent_detail'),
    path('<uuid:agent_id>/edit/', views.AgentEditView.as_view(), name='agent_edit'),
    path('<uuid:agent_id>/delete/', views.AgentDeleteView.as_view(), name='agent_delete'),
    
    # Agent registration
    path('register/', views.AgentRegisterView.as_view(), name='agent_register'),
    path('register/ai/', views.AIRegisterView.as_view(), name='ai_register'),
    path('register/human/', views.HumanRegisterView.as_view(), name='human_register'),
    
    # Agent dashboard
    path('dashboard/', views.AgentDashboardView.as_view(), name='dashboard'),
    path('performance/', views.AgentPerformanceView.as_view(), name='performance'),
    path('earnings/', views.AgentEarningsView.as_view(), name='earnings'),
    path('tasks/', views.AgentTasksView.as_view(), name='tasks'),
    path('tasks/<uuid:task_id>/', views.AgentTaskDetailView.as_view(), name='task_detail'),
    
    # Agent settings
    path('settings/', views.AgentSettingsView.as_view(), name='settings'),
    path('capabilities/', views.AgentCapabilitiesView.as_view(), name='capabilities'),
    path('heartbeat/', views.AgentHeartbeatView.as_view(), name='heartbeat'),
    
    # Agent verification
    path('verify/', views.AgentVerificationView.as_view(), name='verification'),
    path('verify/start/', views.StartVerificationView.as_view(), name='start_verification'),
]