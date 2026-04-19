# apps/webhooks/admin.py
from django.contrib import admin
from .models import WebhookEndpoint, WebhookDelivery

@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ['url', 'owner_type', 'is_active', 'failure_count', 'created_at']
    list_filter = ['is_active', 'owner_type']
    readonly_fields = ['secret']

@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'event_type', 'status', 'attempt_count', 'created_at']
    list_filter = ['status', 'event_type']