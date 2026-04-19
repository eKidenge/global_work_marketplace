# apps/dispatch/api/urls.py
from django.urls import path
from . import views

app_name = 'dispatch_api'

urlpatterns = [
    # Task dispatch endpoints
    path('dispatch/task/', views.APIDispatchTaskView.as_view(), name='api_dispatch_task'),
    path('dispatch/status/<uuid:dispatch_id>/', views.APIDispatchStatusView.as_view(), name='api_dispatch_status'),
    path('dispatch/queue/', views.APIDispatchQueueView.as_view(), name='api_dispatch_queue'),
    
    # Matching endpoints
    path('match/task/<uuid:task_id>/', views.APIMatchTaskView.as_view(), name='api_match_task'),
    path('match/agent/<uuid:agent_id>/', views.APIMatchAgentView.as_view(), name='api_match_agent'),
    
    # Priority endpoints
    path('priority/task/<uuid:task_id>/', views.APITaskPriorityView.as_view(), name='api_task_priority'),
    path('priority/queue/', views.APIQueuePriorityView.as_view(), name='api_queue_priority'),
]