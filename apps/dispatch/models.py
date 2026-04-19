# apps/dispatch/models.py
from django.db import models
from apps.common.models import BaseModel

class DispatchQueue(BaseModel):
    """Real-time dispatch queue"""
    PRIORITY_LEVELS = [
        ('urgent', 'Urgent'),
        ('high', 'High'),
        ('normal', 'Normal'),
        ('low', 'Low'),
    ]
    
    task = models.OneToOneField('tasks.Task', on_delete=models.CASCADE, related_name='dispatch_queue')
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='normal')
    queue_position = models.IntegerField()
    enqueued_at = models.DateTimeField(auto_now_add=True)
    dequeued_at = models.DateTimeField(null=True, blank=True)
    estimated_wait_ms = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['priority', 'queue_position']
        indexes = [
            models.Index(fields=['priority', 'queue_position']),
            models.Index(fields=['enqueued_at']),
        ]

class DispatchRecord(BaseModel):
    """Record of dispatch decisions"""
    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE)
    selected_agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE)
    candidate_agents = models.JSONField(default=list)  # List of agent IDs considered
    decision_reason = models.TextField()
    score = models.FloatField()
    dispatch_latency_ms = models.IntegerField()
    
    class Meta:
        ordering = ['-created_at']

class Assignment(BaseModel):
    """Task assignment record"""
    task = models.OneToOneField('tasks.Task', on_delete=models.CASCADE)
    agent = models.ForeignKey('agents.Agent', on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)