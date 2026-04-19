# apps/execution/admin.py
from django.contrib import admin
from .models import Execution, ExecutionLog, Checkpoint

@admin.register(Execution)
class ExecutionAdmin(admin.ModelAdmin):
    list_display = ['task', 'agent', 'execution_type', 'state', 'duration_ms', 'created_at']
    list_filter = ['state', 'execution_type', 'created_at']
    readonly_fields = ['input_data', 'output_data']
    
    fieldsets = (
        ('Execution Info', {'fields': ('task', 'agent', 'execution_type')}),
        ('Status', {'fields': ('state', 'started_at', 'completed_at', 'duration_ms')}),
        ('Cost', {'fields': ('cost_sats', 'payment_status')}),
        ('Error', {'fields': ('error_message', 'retry_count')}),
    )

@admin.register(ExecutionLog)
class ExecutionLogAdmin(admin.ModelAdmin):
    list_display = ['execution', 'log_level', 'message_preview', 'timestamp']
    list_filter = ['log_level', 'timestamp']
    
    def message_preview(self, obj):
        return obj.message[:100]
    message_preview.short_description = 'Message'

@admin.register(Checkpoint)
class CheckpointAdmin(admin.ModelAdmin):
    list_display = ['execution', 'created_at']
    readonly_fields = ['state_data']