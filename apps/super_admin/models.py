# apps/super_admin/models.py
from django.db import models
from apps.common.models import BaseModel

class AdminUser(BaseModel):
    """Extended admin user with permissions"""
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=[
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('viewer', 'Viewer')
    ], default='viewer')
    
    permissions = models.JSONField(default=dict)  # Granular permissions
    last_login_ip = models.GenericIPAddressField(null=True)
    login_count = models.IntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.email} - {self.role}"

class AdminAuditLog(BaseModel):
    """Track every admin action"""
    admin_user = models.ForeignKey(AdminUser, on_delete=models.CASCADE)
    action_type = models.CharField(max_length=100)  # create, update, delete, view
    resource_type = models.CharField(max_length=100)  # task, agent, payment, etc.
    resource_id = models.CharField(max_length=100)
    changes = models.JSONField(default=dict)  # What changed
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    
    class Meta:
        ordering = ['-created_at']

class SystemSettings(BaseModel):
    """Global system settings editable from admin panel"""
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False)  # Can be read by API
    
    class Meta:
        verbose_name_plural = "System Settings"

class Announcement(BaseModel):
    """Global announcements shown to all users"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    announcement_type = models.CharField(max_length=50, choices=[
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('success', 'Success'),
        ('error', 'Error')
    ], default='info')
    is_active = models.BooleanField(default=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    target_audience = models.CharField(max_length=50, choices=[
        ('all', 'All Users'),
        ('admins', 'Admins Only'),
        ('agents', 'Agents Only'),
        ('clients', 'Clients Only')
    ], default='all')