# apps/agents/api/urls.py
from django.urls import path
from . import views

app_name = 'agents_api'

urlpatterns = [
    # API endpoints for agents
    path('agents/', views.APIAgentListView.as_view(), name='api_agent_list'),
    path('agents/<uuid:agent_id>/', views.APIAgentDetailView.as_view(), name='api_agent_detail'),
    path('agents/<uuid:agent_id>/tasks/', views.APIAgentTasksView.as_view(), name='api_agent_tasks'),
    path('agents/<uuid:agent_id>/heartbeat/', views.APIAgentHeartbeatView.as_view(), name='api_agent_heartbeat'),
    
    # Task endpoints for agents
    path('tasks/<uuid:task_id>/accept/', views.APIAcceptTaskView.as_view(), name='api_accept_task'),
    path('tasks/<uuid:task_id>/submit/', views.APISubmitTaskView.as_view(), name='api_submit_task'),
    path('tasks/<uuid:task_id>/status/', views.APITaskStatusView.as_view(), name='api_task_status'),
]