# apps/execution/models.py
from django.db import models
from apps.common.models import BaseModel

class Execution(BaseModel):
    """Runtime execution record"""
    
    class ExecutionState(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        WAITING_HUMAN = 'waiting_human', 'Waiting Human'
        WAITING_AI = 'waiting_ai', 'Waiting AI'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        TIMEOUT = 'timeout', 'Timeout'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class ExecutionType(models.TextChoices):
        AI = 'ai', 'AI Execution'
        HUMAN = 'human', 'Human Execution'
        HYBRID = 'hybrid', 'Hybrid Execution'
    
    task = models.OneToOneField('tasks.Task', on_delete=models.CASCADE, related_name='execution')
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE)
    execution_type = models.CharField(max_length=10, choices=ExecutionType.choices)
    state = models.CharField(max_length=20, choices=ExecutionState.choices, default=ExecutionState.PENDING)
    
    input_data = models.JSONField(default=dict)
    output_data = models.JSONField(null=True, blank=True)
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    
    cost_sats = models.BigIntegerField(default=0)
    payment_status = models.CharField(max_length=50, default='pending')
    
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['state', 'created_at']),
            models.Index(fields=['agent', 'state']),
        ]

class ExecutionLog(BaseModel):
    """Streaming execution logs"""
    execution = models.ForeignKey(Execution, on_delete=models.CASCADE, related_name='logs')
    log_level = models.CharField(max_length=20, default='info')  # info, warning, error, debug
    message = models.TextField()
    data = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']

class Checkpoint(BaseModel):
    """State checkpoint for recovery"""
    execution = models.ForeignKey(Execution, on_delete=models.CASCADE, related_name='checkpoints')
    state_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)