# apps/verification/api/urls.py
from django.urls import path
from . import views

app_name = 'verification_api'

urlpatterns = [
    path('verify/<uuid:task_id>/', views.APIVerifyTaskView.as_view(), name='api_verify_task'),
    path('status/<uuid:verification_id>/', views.APIVerificationStatusView.as_view(), name='api_verification_status'),
    path('reputation/<uuid:agent_id>/', views.APIReputationView.as_view(), name='api_reputation'),
    path('disputes/', views.APIDisputeListView.as_view(), name='api_disputes'),
    path('disputes/<uuid:dispute_id>/', views.APIDisputeDetailView.as_view(), name='api_dispute_detail'),
]