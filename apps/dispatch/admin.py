# apps/dispatch/admin.py
from django.contrib import admin
from .models import DispatchQueue, DispatchRecord, Assignment

@admin.register(DispatchQueue)
class DispatchQueueAdmin(admin.ModelAdmin):
    list_display = ['task', 'priority', 'queue_position', 'enqueued_at']
    list_filter = ['priority']
    
@admin.register(DispatchRecord)
class DispatchRecordAdmin(admin.ModelAdmin):
    list_display = ['task', 'selected_agent', 'score', 'dispatch_latency_ms', 'created_at']
    list_filter = ['created_at']
    readonly_fields = ['candidate_agents', 'decision_reason']

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['task', 'agent', 'assigned_at', 'accepted_at', 'is_active']
    list_filter = ['is_active', 'assigned_at']