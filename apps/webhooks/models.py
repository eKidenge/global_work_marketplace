# apps/webhooks/models.py
from django.db import models
from apps.common.models import BaseModel

class WebhookEndpoint(BaseModel):
    """Webhook endpoint configuration"""
    owner_id = models.UUIDField()
    owner_type = models.CharField(max_length=50)  # user, agent, system
    url = models.URLField()
    secret = models.CharField(max_length=64)
    events = models.JSONField(default=list)  # List of event types to receive
    is_active = models.BooleanField(default=True)
    
    retry_count = models.IntegerField(default=3)
    timeout_ms = models.IntegerField(default=5000)
    
    last_triggered_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    failure_count = models.IntegerField(default=0)

class WebhookDelivery(BaseModel):
    """Webhook delivery record"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=100)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    
    attempt_count = models.IntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)