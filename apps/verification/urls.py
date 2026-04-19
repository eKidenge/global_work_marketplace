# apps/verification/urls.py
from django.urls import path
from . import views

app_name = 'verification'

urlpatterns = [
    # Task verification
    path('', views.VerificationDashboardView.as_view(), name='dashboard'),
    path('queue/', views.VerificationQueueView.as_view(), name='queue'),
    path('verify/<uuid:task_id>/', views.VerifyTaskView.as_view(), name='verify_task'),
    path('review/<uuid:verification_id>/', views.VerificationReviewView.as_view(), name='review'),
    
    # Reputation
    path('reputation/<uuid:agent_id>/', views.ReputationView.as_view(), name='reputation'),
    path('reputation/leaderboard/', views.ReputationLeaderboardView.as_view(), name='leaderboard'),
    
    # Disputes
    path('disputes/', views.DisputeListView.as_view(), name='disputes'),
    path('disputes/create/<uuid:task_id>/', views.CreateDisputeView.as_view(), name='create_dispute'),
    path('disputes/<uuid:dispute_id>/', views.DisputeDetailView.as_view(), name='dispute_detail'),
    path('disputes/<uuid:dispute_id>/respond/', views.RespondToDisputeView.as_view(), name='respond_dispute'),
    path('disputes/<uuid:dispute_id>/escalate/', views.EscalateDisputeView.as_view(), name='escalate_dispute'),
    
    # Appeals
    path('appeal/<uuid:verification_id>/', views.AppealView.as_view(), name='appeal'),
    path('appeal/<uuid:appeal_id>/review/', views.AppealReviewView.as_view(), name='appeal_review'),
    
    # Quality metrics
    path('metrics/', views.QualityMetricsView.as_view(), name='metrics'),
    path('reports/', views.VerificationReportView.as_view(), name='reports'),
]