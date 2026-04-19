# apps/verification/models.py
from django.db import models
from apps.common.models import BaseModel

class Verification(BaseModel):
    """Task verification record"""
    VERIFICATION_TYPES = [
        ('auto', 'Automatic'),
        ('human', 'Human Review'),
        ('consensus', 'Multi-Agent Consensus'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('appealed', 'Appealed'),
    ]
    
    task = models.OneToOneField('tasks.Task', on_delete=models.CASCADE)
    verification_type = models.CharField(max_length=20, choices=VERIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    quality_score = models.FloatField()
    confidence = models.FloatField()
    verifier_notes = models.TextField(blank=True)
    
    verified_by = models.ForeignKey('agents.Agent', null=True, blank=True, on_delete=models.SET_NULL)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    appeal_reason = models.TextField(blank=True)
    appeal_resolved_at = models.DateTimeField(null=True, blank=True)

class Reputation(BaseModel):
    """Agent reputation score"""
    agent = models.OneToOneField('agents.Agent', on_delete=models.CASCADE, related_name='reputation')
    overall_score = models.FloatField(default=0.5)
    reliability_score = models.FloatField(default=0.5)
    quality_score = models.FloatField(default=0.5)
    speed_score = models.FloatField(default=0.5)
    communication_score = models.FloatField(default=0.5)
    
    total_reviews = models.IntegerField(default=0)
    positive_reviews = models.IntegerField(default=0)
    negative_reviews = models.IntegerField(default=0)
    
    last_calculated = models.DateTimeField(auto_now=True)

class Dispute(BaseModel):
    """Task dispute resolution"""
    DISPUTE_REASONS = [
        ('quality', 'Poor Quality'),
        ('timeout', 'Timeout'),
        ('fraud', 'Suspected Fraud'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('escalated', 'Escalated'),
    ]
    
    task = models.ForeignKey('tasks.Task', on_delete=models.CASCADE)
    raised_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=DISPUTE_REASONS)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    evidence = models.JSONField(default=list)
    resolution = models.TextField(blank=True)
    resolved_by = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='resolved_disputes')
    resolved_at = models.DateTimeField(null=True, blank=True)