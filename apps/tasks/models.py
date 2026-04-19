# apps/tasks/models.py
from django.db import models
from apps.common.models import BaseModel
from django.contrib.postgres.fields import ArrayField

class Task(BaseModel):
    """Main task model"""
    
    class TaskState(models.TextChoices):
        OPEN = 'open', 'Open'
        ASSIGNED = 'assigned', 'Assigned'
        EXECUTING = 'executing', 'Executing'
        VERIFYING = 'verifying', 'Verifying'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        DISPUTED = 'disputed', 'Disputed'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    # Basic info
    title = models.CharField(max_length=500)
    description = models.TextField()
    parent_task = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)
    is_microtask = models.BooleanField(default=False)
    
    # Requirements
    required_capabilities = models.JSONField(default=list)
    required_human = models.BooleanField(default=False)
    required_trust_level = models.IntegerField(default=1)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    
    # Economics
    budget_sats = models.BigIntegerField()
    min_bid_sats = models.BigIntegerField(null=True, blank=True)
    max_bid_sats = models.BigIntegerField(null=True, blank=True)
    assigned_price_sats = models.BigIntegerField(null=True, blank=True)
    
    # State
    state = models.CharField(max_length=20, choices=TaskState.choices, default=TaskState.OPEN)
    matched_agent = models.ForeignKey('agents.Agent', null=True, blank=True, on_delete=models.SET_NULL)
    
    # Timing
    assigned_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    # Execution
    execution_log = models.JSONField(default=list)
    result_data = models.JSONField(null=True, blank=True)
    verification_hash = models.CharField(max_length=64, null=True, blank=True)
    
    def __str__(self):
        return f"{self.title[:50]} - {self.state}"
    
    @property
    def is_expired(self):
        from django.utils import timezone
        return self.expires_at < timezone.now()

class TaskTemplate(BaseModel):
    """Reusable task templates"""
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    description = models.TextField()
    schema = models.JSONField(default=dict)
    estimated_duration_ms = models.IntegerField()
    default_budget_sats = models.BigIntegerField()
    required_capabilities = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    usage_count = models.IntegerField(default=0)
    
    def __str__(self):
        return self.name

class MicroTask(BaseModel):
    """Sub-tasks for complex tasks"""
    parent_task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='microtasks')
    title = models.CharField(max_length=500)
    description = models.TextField()
    order = models.IntegerField()
    budget_sats = models.BigIntegerField()
    assigned_agent = models.ForeignKey('agents.Agent', null=True, blank=True, on_delete=models.SET_NULL)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['order']