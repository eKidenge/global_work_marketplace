# apps/tasks/urls.py
from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    # Task listing
    path('', views.TaskListView.as_view(), name='task_list'),
    path('open/', views.OpenTasksView.as_view(), name='open_tasks'),
    path('my-tasks/', views.MyTasksView.as_view(), name='my_tasks'),
    path('assigned/', views.AssignedTasksView.as_view(), name='assigned_tasks'),
    path('completed/', views.CompletedTasksView.as_view(), name='completed_tasks'),
    
    # Task CRUD
    path('create/', views.TaskCreateView.as_view(), name='task_create'),
    path('<uuid:task_id>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('<uuid:task_id>/edit/', views.TaskEditView.as_view(), name='task_edit'),
    path('<uuid:task_id>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    path('<uuid:task_id>/cancel/', views.TaskCancelView.as_view(), name='task_cancel'),
    
    # Task actions
    path('<uuid:task_id>/bid/', views.TaskBidView.as_view(), name='task_bid'),
    path('<uuid:task_id>/accept/', views.TaskAcceptView.as_view(), name='task_accept'),
    path('<uuid:task_id>/reject/', views.TaskRejectView.as_view(), name='task_reject'),
    path('<uuid:task_id>/start/', views.TaskStartView.as_view(), name='task_start'),
    path('<uuid:task_id>/complete/', views.TaskCompleteView.as_view(), name='task_complete'),
    path('<uuid:task_id>/report/', views.TaskReportView.as_view(), name='task_report'),
    
    # Microtasks
    path('<uuid:task_id>/microtasks/', views.MicroTaskListView.as_view(), name='microtask_list'),
    path('<uuid:task_id>/microtasks/create/', views.MicroTaskCreateView.as_view(), name='microtask_create'),
    path('microtasks/<uuid:microtask_id>/', views.MicroTaskDetailView.as_view(), name='microtask_detail'),
    path('microtasks/<uuid:microtask_id>/complete/', views.MicroTaskCompleteView.as_view(), name='microtask_complete'),
    
    # Task templates
    path('templates/', views.TaskTemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.TaskTemplateCreateView.as_view(), name='template_create'),
    path('templates/<uuid:template_id>/', views.TaskTemplateDetailView.as_view(), name='template_detail'),
    path('templates/<uuid:template_id>/use/', views.UseTemplateView.as_view(), name='use_template'),
]