# apps/super_admin/models.py
from django.db import models
from django.utils import timezone
import uuid

from apps.common.models import BaseModel


class AdminUser(BaseModel):
    """Extended admin user with permissions"""
    
    class Roles(models.TextChoices):
        SUPER_ADMIN = 'super_admin', 'Super Admin'
        ADMIN = 'admin', 'Admin'
        MODERATOR = 'moderator', 'Moderator'
        VIEWER = 'viewer', 'Viewer'
    
    user = models.OneToOneField(
        'accounts.User', 
        on_delete=models.CASCADE,
        related_name='admin_profile'
    )
    role = models.CharField(
        max_length=20, 
        choices=Roles.choices, 
        default=Roles.VIEWER
    )
    permissions = models.JSONField(default=dict, help_text="Custom permissions JSON")
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    login_count = models.IntegerField(default=0)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    # Two-factor authentication
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=100, blank=True)
    
    # Session management
    session_key = models.CharField(max_length=100, blank=True)
    session_expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Admin User"
        verbose_name_plural = "Admin Users"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()}"
    
    def has_permission(self, permission):
        """Check if admin has specific permission"""
        if self.role == 'super_admin':
            return True
        return self.permissions.get(permission, False)
    
    def is_online(self):
        """Check if admin is currently online"""
        if self.session_expires_at:
            return self.session_expires_at > timezone.now()
        return False


class AdminAuditLog(BaseModel):
    """Track every action taken by admin users"""
    
    class ActionTypes(models.TextChoices):
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        VIEW = 'view', 'View'
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        EXPORT = 'export', 'Export'
        SETTING_CHANGE = 'setting_change', 'Setting Change'
        PERMISSION_CHANGE = 'permission_change', 'Permission Change'
    
    admin_user = models.ForeignKey(
        AdminUser, 
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs'
    )
    action_type = models.CharField(max_length=20, choices=ActionTypes.choices)
    resource_type = models.CharField(max_length=100, help_text="Type of resource (task, agent, user, etc.)")
    resource_id = models.CharField(max_length=100, help_text="ID of the resource")
    resource_name = models.CharField(max_length=500, blank=True, help_text="Name/Title of the resource")
    
    changes = models.JSONField(default=dict, help_text="What changed (before/after)")
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # Request details
    request_method = models.CharField(max_length=10, blank=True)
    request_path = models.CharField(max_length=500, blank=True)
    request_data = models.JSONField(default=dict, blank=True)
    
    # Response details
    response_status = models.IntegerField(default=200)
    response_time_ms = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Admin Audit Log"
        verbose_name_plural = "Admin Audit Logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['admin_user', '-created_at']),
            models.Index(fields=['action_type', 'resource_type']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        admin = self.admin_user.user.email if self.admin_user else "Unknown"
        return f"{admin} - {self.action_type} - {self.resource_type} - {self.created_at}"


class SystemSettings(BaseModel):
    """Global system settings editable from admin panel"""
    
    class SettingTypes(models.TextChoices):
        STRING = 'string', 'String'
        INTEGER = 'integer', 'Integer'
        FLOAT = 'float', 'Float'
        BOOLEAN = 'boolean', 'Boolean'
        JSON = 'json', 'JSON'
        LIST = 'list', 'List'
    
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    setting_type = models.CharField(max_length=20, choices=SettingTypes.choices, default=SettingTypes.STRING)
    description = models.TextField(blank=True)
    is_public = models.BooleanField(default=False, help_text="Can be accessed by public API")
    is_encrypted = models.BooleanField(default=False, help_text="Value is encrypted")
    
    # Category for organization
    category = models.CharField(max_length=100, default='general', db_index=True)
    
    # Validation rules
    min_value = models.FloatField(null=True, blank=True)
    max_value = models.FloatField(null=True, blank=True)
    allowed_values = models.JSONField(default=list, blank=True, help_text="List of allowed values")
    
    # Metadata
    updated_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_settings'
    )
    
    class Meta:
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"
        ordering = ['category', 'key']
    
    def __str__(self):
        return f"{self.key} = {self.get_display_value()}"
    
    def get_display_value(self):
        """Get display-friendly value"""
        if self.setting_type == 'boolean':
            return "Yes" if self.value else "No"
        return str(self.value)
    
    def get_typed_value(self):
        """Get value with proper type conversion"""
        if self.setting_type == 'integer':
            return int(self.value)
        elif self.setting_type == 'float':
            return float(self.value)
        elif self.setting_type == 'boolean':
            return bool(self.value)
        return self.value
    
    def validate_value(self, value):
        """Validate value against constraints"""
        if self.setting_type == 'integer' or self.setting_type == 'float':
            if self.min_value is not None and value < self.min_value:
                return False, f"Value must be at least {self.min_value}"
            if self.max_value is not None and value > self.max_value:
                return False, f"Value must be at most {self.max_value}"
        
        if self.allowed_values and value not in self.allowed_values:
            return False, f"Value must be one of: {', '.join(map(str, self.allowed_values))}"
        
        return True, "Valid"


class Announcement(BaseModel):
    """Global announcements shown to users and admins"""
    
    class AnnouncementTypes(models.TextChoices):
        INFO = 'info', 'Information'
        WARNING = 'warning', 'Warning'
        SUCCESS = 'success', 'Success'
        ERROR = 'error', 'Error'
        MAINTENANCE = 'maintenance', 'Maintenance'
        FEATURE = 'feature', 'New Feature'
    
    class TargetAudience(models.TextChoices):
        ALL = 'all', 'All Users'
        ADMINS = 'admins', 'Admins Only'
        AGENTS = 'agents', 'Agents Only'
        USERS = 'users', 'Users Only'
        GUESTS = 'guests', 'Guests Only'
    
    title = models.CharField(max_length=200)
    content = models.TextField()
    announcement_type = models.CharField(
        max_length=20, 
        choices=AnnouncementTypes.choices, 
        default=AnnouncementTypes.INFO
    )
    is_active = models.BooleanField(default=True)
    is_dismissible = models.BooleanField(default=True)
    
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    
    target_audience = models.CharField(
        max_length=20, 
        choices=TargetAudience.choices, 
        default=TargetAudience.ALL
    )
    
    # Optional: Specific users/groups
    specific_users = models.ManyToManyField('accounts.User', blank=True, related_name='targeted_announcements')
    specific_agents = models.ManyToManyField('agents.Agent', blank=True, related_name='targeted_announcements')
    
    # Actions
    action_url = models.URLField(blank=True, help_text="URL to navigate when clicked")
    action_text = models.CharField(max_length=100, blank=True, help_text="Button text")
    
    # Tracking
    view_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_announcements'
    )
    
    class Meta:
        verbose_name = "Announcement"
        verbose_name_plural = "Announcements"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', 'start_date', 'end_date']),
            models.Index(fields=['announcement_type']),
        ]
    
    def __str__(self):
        return self.title
    
    def is_visible_to_user(self, user):
        """Check if announcement is visible to a specific user"""
        if not self.is_active:
            return False
        
        now = timezone.now()
        if now < self.start_date:
            return False
        if self.end_date and now > self.end_date:
            return False
        
        if self.target_audience == 'all':
            return True
        elif self.target_audience == 'admins' and user.is_staff:
            return True
        elif self.target_audience == 'agents':
            from apps.agents.models import Agent
            return Agent.objects.filter(user=user).exists()
        elif self.target_audience == 'users':
            return not user.is_staff
        elif self.target_audience == 'guests':
            return not user.is_authenticated
        
        return False


class AdminDashboardWidget(BaseModel):
    """Custom dashboard widgets for admin users"""
    
    class WidgetTypes(models.TextChoices):
        STATS = 'stats', 'Statistics'
        CHART = 'chart', 'Chart'
        TABLE = 'table', 'Data Table'
        ALERT = 'alert', 'Alerts'
        FEED = 'feed', 'Activity Feed'
        CUSTOM = 'custom', 'Custom HTML'
    
    class Positions(models.TextChoices):
        TOP_LEFT = 'top_left', 'Top Left'
        TOP_RIGHT = 'top_right', 'Top Right'
        BOTTOM_LEFT = 'bottom_left', 'Bottom Left'
        BOTTOM_RIGHT = 'bottom_right', 'Bottom Right'
        FULL_WIDTH = 'full_width', 'Full Width'
    
    admin_user = models.ForeignKey(
        AdminUser,
        on_delete=models.CASCADE,
        related_name='dashboard_widgets'
    )
    title = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WidgetTypes.choices)
    position = models.CharField(max_length=20, choices=Positions.choices, default=Positions.TOP_LEFT)
    order = models.IntegerField(default=0)
    
    # Configuration
    config = models.JSONField(default=dict, help_text="Widget-specific configuration")
    custom_html = models.TextField(blank=True, help_text="For CUSTOM widget type")
    
    # Size
    width = models.IntegerField(default=1, help_text="Width in grid columns (1-4)")
    height = models.IntegerField(default=1, help_text="Height in grid rows (1-4)")
    
    is_visible = models.BooleanField(default=True)
    refresh_interval_seconds = models.IntegerField(default=30, help_text="Auto-refresh interval")
    
    class Meta:
        verbose_name = "Dashboard Widget"
        verbose_name_plural = "Dashboard Widgets"
        ordering = ['position', 'order']
        unique_together = [['admin_user', 'position', 'order']]
    
    def __str__(self):
        return f"{self.admin_user.user.email} - {self.title}"


class SystemBackup(BaseModel):
    """System backup records"""
    
    class BackupTypes(models.TextChoices):
        DATABASE = 'database', 'Database'
        FILES = 'files', 'Files'
        FULL = 'full', 'Full System'
    
    class BackupStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        RUNNING = 'running', 'Running'
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'
    
    backup_type = models.CharField(max_length=20, choices=BackupTypes.choices)
    status = models.CharField(max_length=20, choices=BackupStatus.choices, default=BackupStatus.PENDING)
    filename = models.CharField(max_length=500)
    file_size_bytes = models.BigIntegerField(default=0)
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    error_message = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)
    
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_backups'
    )
    
    class Meta:
        verbose_name = "System Backup"
        verbose_name_plural = "System Backups"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.filename} - {self.status}"


class MaintenanceMode(BaseModel):
    """System maintenance mode settings"""
    
    is_enabled = models.BooleanField(default=False)
    message = models.TextField(default="System is under maintenance. Please check back later.")
    allow_admins = models.BooleanField(default=True, help_text="Allow admin users to access")
    allow_ips = models.JSONField(default=list, blank=True, help_text="List of allowed IP addresses")
    
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    
    started_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='started_maintenance'
    )
    
    class Meta:
        verbose_name = "Maintenance Mode"
        verbose_name_plural = "Maintenance Mode"
    
    def __str__(self):
        return f"Maintenance: {'Enabled' if self.is_enabled else 'Disabled'}"
    
    def is_ip_allowed(self, ip):
        """Check if IP address is allowed during maintenance"""
        return ip in self.allow_ips


class ScheduledTask(BaseModel):
    """Scheduled administrative tasks"""
    
    class TaskTypes(models.TextChoices):
        BACKUP = 'backup', 'System Backup'
        CLEANUP = 'cleanup', 'Cleanup Old Data'
        REPORT = 'report', 'Generate Report'
        EMAIL = 'email', 'Send Email'
        SYNC = 'sync', 'Data Sync'
    
    class Frequency(models.TextChoices):
        ONCE = 'once', 'Once'
        HOURLY = 'hourly', 'Hourly'
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'
    
    name = models.CharField(max_length=200)
    task_type = models.CharField(max_length=20, choices=TaskTypes.choices)
    frequency = models.CharField(max_length=20, choices=Frequency.choices, default=Frequency.ONCE)
    
    # Schedule
    scheduled_time = models.DateTimeField()
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    
    # Execution
    is_active = models.BooleanField(default=True)
    parameters = models.JSONField(default=dict)
    
    # Results
    last_status = models.CharField(max_length=20, default='pending')
    last_output = models.TextField(blank=True)
    
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks'
    )
    
    class Meta:
        verbose_name = "Scheduled Task"
        verbose_name_plural = "Scheduled Tasks"
        ordering = ['next_run']
    
    def __str__(self):
        return f"{self.name} - {self.frequency}"


class APIRateLimit(BaseModel):
    """API rate limiting configuration"""
    
    endpoint = models.CharField(max_length=500, help_text="API endpoint pattern")
    method = models.CharField(max_length=10, default='ALL', help_text="HTTP method (GET, POST, etc.)")
    
    requests_per_minute = models.IntegerField(default=60)
    requests_per_hour = models.IntegerField(default=1000)
    requests_per_day = models.IntegerField(default=10000)
    
    burst_limit = models.IntegerField(default=10, help_text="Maximum burst requests")
    
    is_enabled = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "API Rate Limit"
        verbose_name_plural = "API Rate Limits"
        unique_together = [['endpoint', 'method']]
    
    def __str__(self):
        return f"{self.method} {self.endpoint}"


class SystemNotification(BaseModel):
    """System notifications for admins"""
    
    class NotificationLevels(models.TextChoices):
        INFO = 'info', 'Info'
        SUCCESS = 'success', 'Success'
        WARNING = 'warning', 'Warning'
        ERROR = 'error', 'Error'
        CRITICAL = 'critical', 'Critical'
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    level = models.CharField(max_length=20, choices=NotificationLevels.choices, default=NotificationLevels.INFO)
    
    is_read = models.BooleanField(default=False)
    is_dismissed = models.BooleanField(default=False)
    
    recipient = models.ForeignKey(
        AdminUser,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    
    action_url = models.URLField(blank=True)
    action_text = models.CharField(max_length=100, blank=True)
    
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "System Notification"
        verbose_name_plural = "System Notifications"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.recipient.user.email}"
    
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False