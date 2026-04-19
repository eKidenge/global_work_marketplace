# apps/dispatch/urls.py
from django.urls import path
from . import views

app_name = 'dispatch'

urlpatterns = [
    # Dispatch monitoring
    path('', views.DispatchDashboardView.as_view(), name='dashboard'),
    path('queue/', views.QueueMonitorView.as_view(), name='queue_monitor'),
    path('assignments/', views.AssignmentListView.as_view(), name='assignments'),
    path('assignments/<uuid:assignment_id>/', views.AssignmentDetailView.as_view(), name='assignment_detail'),
    
    # Real-time dispatch
    path('realtime/', views.RealtimeDispatchView.as_view(), name='realtime'),
    path('realtime/board/', views.DispatchBoardView.as_view(), name='dispatch_board'),
    path('realtime/stats/', views.DispatchStatsView.as_view(), name='dispatch_stats'),
    
    # Dispatch history
    path('history/', views.DispatchHistoryView.as_view(), name='history'),
    path('history/<uuid:record_id>/', views.DispatchRecordView.as_view(), name='dispatch_record'),
    
    # Dispatch actions
    path('match/', views.MatchTaskView.as_view(), name='match_task'),
    path('assign/', views.AssignTaskView.as_view(), name='assign_task'),
    path('reassign/<uuid:assignment_id>/', views.ReassignTaskView.as_view(), name='reassign_task'),
]