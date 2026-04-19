# apps/webhooks/api/urls.py
from django.urls import path
from . import views

app_name = 'webhooks_api'

urlpatterns = [
    path('endpoints/', views.APIWebhookEndpointsView.as_view(), name='api_endpoints'),
    path('deliveries/', views.APIWebhookDeliveriesView.as_view(), name='api_deliveries'),
]