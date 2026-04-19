# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.common.models import BaseModel

class User(AbstractUser, BaseModel):
    """Custom user model"""
    email = models.EmailField(unique=True)
    wallet_balance = models.BigIntegerField(default=0)
    total_spent = models.BigIntegerField(default=0)
    total_earned = models.BigIntegerField(default=0)
    rating = models.FloatField(default=0.0)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email

class Profile(BaseModel):
    """User profile"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    website = models.URLField(blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    
    # Settings
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.user.email}'s profile"

class APIKey(BaseModel):
    """API keys for programmatic access"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=100)
    key = models.CharField(max_length=64, unique=True)
    last_used = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.name}"