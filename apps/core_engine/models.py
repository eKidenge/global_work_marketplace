# apps/core_engine/models.py
from django.db import models
from apps.common.models import BaseModel

class EngineDecision(BaseModel):
    """Every decision made by the core engine"""
    DECISION_TYPES = [
        ('routing', 'Routing Decision'),
        ('pricing', 'Pricing Decision'),
        ('risk', 'Risk Assessment'),
        ('policy', 'Policy Enforcement'),
    ]
    
    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE, null=True, blank=True)
    decision_type = models.CharField(max_length=20, choices=DECISION_TYPES)
    selected_agent_type = models.CharField(max_length=10, null=True, blank=True)
    selected_agent = models.ForeignKey('agents.Agent', on_delete=models.SET_NULL, null=True, blank=True)
    
    price_sats = models.BigIntegerField(null=True, blank=True)
    confidence_score = models.FloatField()
    risk_score = models.FloatField()
    fraud_probability = models.FloatField()
    
    reasoning = models.TextField()
    decision_log_json = models.JSONField(default=dict)
    price_breakdown_json = models.JSONField(default=dict)
    
    decision_time = models.DateTimeField(auto_now_add=True)
    latency_ms = models.IntegerField()
    
    class Meta:
        ordering = ['-decision_time']
        indexes = [
            models.Index(fields=['decision_type', '-decision_time']),
            models.Index(fields=['task', 'decision_type']),
        ]

class EngineMetric(BaseModel):
    """Performance metrics for the engine"""
    METRIC_NAMES = [
        ('accuracy', 'Accuracy'),
        ('latency', 'Latency'),
        ('throughput', 'Throughput'),
        ('cost_efficiency', 'Cost Efficiency'),
    ]
    
    metric_name = models.CharField(max_length=50, choices=METRIC_NAMES)
    current_value = models.FloatField()
    average_value = models.FloatField()
    min_value = models.FloatField()
    max_value = models.FloatField()
    value_history_json = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['metric_name']

class PolicyRule(BaseModel):
    """Dynamic policy rules"""
    name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    rule_type = models.CharField(max_length=50)  # agent_selection, pricing, risk, etc.
    conditions = models.JSONField(default=dict)
    actions = models.JSONField(default=dict)
    priority = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name