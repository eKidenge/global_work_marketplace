# apps/agents/models.py
from django.db import models
from apps.common.models import BaseModel
from django.contrib.postgres.fields import ArrayField

class Agent(BaseModel):
    """Agent model for both AI and Human agents"""
    AGENT_TYPES = [
        ('ai', 'AI Agent'),
        ('human', 'Human Agent'),
    ]
    
    # Basic info
    name = models.CharField(max_length=200)
    agent_type = models.CharField(max_length=10, choices=AGENT_TYPES)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, null=True, blank=True, related_name='agents')
    
    # Capabilities
    capabilities = models.JSONField(default=list)
    description = models.TextField(blank=True)
    
    # API integration (for AI agents)
    api_endpoint = models.URLField(null=True, blank=True)
    webhook_url = models.URLField(null=True, blank=True)
    api_key_encrypted = models.BinaryField(null=True, blank=True)
    
    # Performance metrics
    trust_score = models.FloatField(default=0.5)
    success_rate = models.FloatField(default=0.5)
    total_tasks = models.IntegerField(default=0)
    total_earned = models.BigIntegerField(default=0)
    avg_response_ms = models.IntegerField(default=1000)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    last_heartbeat = models.DateTimeField(auto_now=True)
    
    # Rate limiting
    rate_limit_per_minute = models.IntegerField(default=60)
    rate_limit_remaining = models.IntegerField(default=60)
    
    # Pricing
    hourly_rate_sats = models.BigIntegerField(default=10000)
    
    def __str__(self):
        return f"{self.name} ({self.agent_type})"
    
    @property
    def is_online(self):
        from django.utils import timezone
        from datetime import timedelta
        return self.is_active and self.last_heartbeat > (timezone.now() - timedelta(minutes=5))

class Capability(BaseModel):
    """Available capabilities/skills"""
    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_ai_capable = models.BooleanField(default=True)
    is_human_capable = models.BooleanField(default=True)
    agents = models.ManyToManyField(Agent, related_name='capability_set', blank=True)
    
    def __str__(self):
        return self.name

class AgentHeartbeat(BaseModel):
    """Track agent heartbeats for monitoring"""
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='heartbeats')
    status = models.CharField(max_length=50, default='online')
    latency_ms = models.IntegerField()
    metrics = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-created_at']