# apps/execution/api/urls.py
from django.urls import path
from . import views

app_name = 'execution_api'

urlpatterns = [
    # Execution endpoints
    path('execute/', views.APIExecuteTaskView.as_view(), name='api_execute_task'),
    path('status/<uuid:execution_id>/', views.APIExecutionStatusView.as_view(), name='api_execution_status'),
    path('cancel/<uuid:execution_id>/', views.APICancelExecutionView.as_view(), name='api_cancel_execution'),
    
    # Sandbox endpoints
    path('sandbox/test/', views.APISandboxTestView.as_view(), name='api_sandbox_test'),
    
    # Streaming endpoints
    path('stream/<uuid:execution_id>/', views.APIExecutionStreamView.as_view(), name='api_execution_stream'),
]