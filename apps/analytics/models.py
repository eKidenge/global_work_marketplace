# apps/analytics/models.py
from django.db import models
from apps.common.models import BaseModel

class Metric(BaseModel):
    """Analytics metric"""
    METRIC_CATEGORIES = [
        ('task', 'Task Metrics'),
        ('agent', 'Agent Metrics'),
        ('payment', 'Payment Metrics'),
        ('performance', 'Performance Metrics'),
    ]
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=METRIC_CATEGORIES)
    value = models.FloatField()
    unit = models.CharField(max_length=20, default='count')
    timestamp = models.DateTimeField(auto_now_add=True)
    tags = models.JSONField(default=dict)
    
    class Meta:
        indexes = [
            models.Index(fields=['name', 'timestamp']),
            models.Index(fields=['category', 'timestamp']),
        ]

class DailyReport(BaseModel):
    """Daily aggregated report"""
    date = models.DateField(unique=True)
    data = models.JSONField()
    generated_at = models.DateTimeField(auto_now_add=True)

class Alert(BaseModel):
    """System alerts"""
    ALERT_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    level = models.CharField(max_length=10, choices=ALERT_LEVELS, default='info')
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict)