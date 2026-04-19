# apps/webhooks/urls.py
from django.urls import path
from . import views

app_name = 'webhooks'

urlpatterns = [
    # Webhook endpoints management
    path('', views.WebhookEndpointListView.as_view(), name='endpoints'),
    path('create/', views.WebhookEndpointCreateView.as_view(), name='create'),
    path('<uuid:endpoint_id>/', views.WebhookEndpointDetailView.as_view(), name='detail'),
    path('<uuid:endpoint_id>/edit/', views.WebhookEndpointEditView.as_view(), name='edit'),
    path('<uuid:endpoint_id>/delete/', views.WebhookEndpointDeleteView.as_view(), name='delete'),
    path('<uuid:endpoint_id>/test/', views.WebhookTestView.as_view(), name='test'),
    path('<uuid:endpoint_id>/regenerate-secret/', views.RegenerateSecretView.as_view(), name='regenerate_secret'),
    
    # Delivery logs
    path('deliveries/', views.DeliveryLogListView.as_view(), name='deliveries'),
    path('deliveries/<uuid:delivery_id>/', views.DeliveryLogDetailView.as_view(), name='delivery_detail'),
    path('deliveries/<uuid:delivery_id>/retry/', views.RetryDeliveryView.as_view(), name='retry_delivery'),
    
    # Webhook receiver (public endpoint)
    path('receive/<str:endpoint_secret>/', views.WebhookReceiverView.as_view(), name='receiver'),
    
    # Statistics
    path('stats/', views.WebhookStatsView.as_view(), name='stats'),
]