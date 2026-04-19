# apps/payments/models.py
from django.db import models
from apps.common.models import BaseModel

class Wallet(BaseModel):
    """User/Agent wallet"""
    OWNER_TYPES = [
        ('user', 'User'),
        ('agent', 'Agent'),
        ('system', 'System'),
    ]
    
    owner_id = models.UUIDField()
    owner_type = models.CharField(max_length=10, choices=OWNER_TYPES)
    balance_sats = models.BigIntegerField(default=0)
    reserved_sats = models.BigIntegerField(default=0)
    total_deposited = models.BigIntegerField(default=0)
    total_withdrawn = models.BigIntegerField(default=0)
    total_spent = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=10, default='sats')
    
    class Meta:
        unique_together = ['owner_id', 'owner_type']
        indexes = [
            models.Index(fields=['owner_id', 'owner_type']),
        ]
    
    @property
    def available_sats(self):
        return self.balance_sats - self.reserved_sats

class Transaction(BaseModel):
    """Payment transaction record"""
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('fee', 'Platform Fee'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    from_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='outgoing_transactions')
    to_wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='incoming_transactions')
    amount_sats = models.BigIntegerField()
    fee_sats = models.BigIntegerField(default=0)
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    
    payment_hash = models.CharField(max_length=64, null=True, blank=True)
    lightning_payment_id = models.CharField(max_length=100, null=True, blank=True)
    
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['from_wallet', 'status']),
            models.Index(fields=['to_wallet', 'status']),
            models.Index(fields=['payment_hash']),
        ]

class EscrowContract(BaseModel):
    """Escrow contract for task payments"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('held', 'Held'),
        ('released', 'Released'),
        ('disputed', 'Disputed'),
        ('refunded', 'Refunded'),
    ]
    
    task = models.OneToOneField('tasks.Task', on_delete=models.CASCADE)
    buyer = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='buyer_escrows')
    seller = models.ForeignKey('agents.Agent', on_delete=models.CASCADE, related_name='seller_escrows')
    amount_sats = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    release_conditions = models.JSONField(default=dict)
    released_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    
    dispute_reason = models.TextField(blank=True)
    resolved_by = models.ForeignKey('accounts.User', null=True, blank=True, on_delete=models.SET_NULL)