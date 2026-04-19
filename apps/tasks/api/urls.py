# apps/tasks/api/urls.py
from django.urls import path
from . import views

app_name = 'tasks_api'

urlpatterns = [
    # Task endpoints
    path('tasks/', views.APITaskListView.as_view(), name='api_task_list'),
    path('tasks/<uuid:task_id>/', views.APITaskDetailView.as_view(), name='api_task_detail'),
    path('tasks/<uuid:task_id>/accept/', views.APIAcceptTaskView.as_view(), name='api_accept_task'),
    path('tasks/<uuid:task_id>/submit/', views.APISubmitTaskView.as_view(), name='api_submit_task'),
    path('tasks/<uuid:task_id>/status/', views.APITaskStatusView.as_view(), name='api_task_status'),
    
    # Available tasks for agents
    path('tasks/available/', views.APIAvailableTasksView.as_view(), name='api_available_tasks'),
    
    # Task categories
    path('categories/', views.APITaskCategoriesView.as_view(), name='api_task_categories'),
]