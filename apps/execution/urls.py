# apps/execution/urls.py
from django.urls import path
from . import views

app_name = 'execution'

urlpatterns = [
    # Execution monitoring
    path('', views.ExecutionDashboardView.as_view(), name='dashboard'),
    path('monitor/', views.ExecutionMonitorView.as_view(), name='monitor'),
    path('live/', views.LiveExecutionView.as_view(), name='live'),
    
    # Execution details
    path('<uuid:execution_id>/', views.ExecutionDetailView.as_view(), name='detail'),
    path('<uuid:execution_id>/logs/', views.ExecutionLogView.as_view(), name='logs'),
    path('<uuid:execution_id>/checkpoints/', views.CheckpointView.as_view(), name='checkpoints'),
    path('<uuid:execution_id>/checkpoints/<uuid:checkpoint_id>/restore/', views.RestoreCheckpointView.as_view(), name='restore_checkpoint'),
    
    # Execution actions
    path('<uuid:execution_id>/pause/', views.PauseExecutionView.as_view(), name='pause'),
    path('<uuid:execution_id>/resume/', views.ResumeExecutionView.as_view(), name='resume'),
    path('<uuid:execution_id>/cancel/', views.CancelExecutionView.as_view(), name='cancel'),
    path('<uuid:execution_id>/retry/', views.RetryExecutionView.as_view(), name='retry'),
    
    # Execution history
    path('history/', views.ExecutionHistoryView.as_view(), name='history'),
    path('history/agent/<uuid:agent_id>/', views.AgentExecutionHistoryView.as_view(), name='agent_history'),
    path('history/task/<uuid:task_id>/', views.TaskExecutionHistoryView.as_view(), name='task_history'),
    
    # Streaming
    path('stream/<uuid:execution_id>/', views.ExecutionStreamView.as_view(), name='stream'),
    path('websocket/<uuid:execution_id>/', views.ExecutionWebSocketView.as_view(), name='websocket'),
]