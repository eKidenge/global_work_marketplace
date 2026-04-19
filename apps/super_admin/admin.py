# apps/super_admin/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Q

from .models import (
    AdminUser, AdminAuditLog, SystemSettings, Announcement,
    AdminDashboardWidget, SystemBackup, MaintenanceMode, ScheduledTask,
    APIRateLimit, SystemNotification
)


@admin.register(AdminUser)
class AdminUserAdmin(admin.ModelAdmin):
    list_display = [
        'user_link', 'role_badge', 'login_count', 'last_login_ip', 
        'last_activity_display', 'status_badge', 'created_at'
    ]
    list_filter = ['role', 'two_factor_enabled', 'created_at']
    search_fields = ['user__email', 'user__username', 'last_login_ip']
    readonly_fields = ['login_count', 'last_login_ip', 'last_activity', 'session_key']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'role', 'permissions')
        }),
        ('Security', {
            'fields': ('two_factor_enabled', 'two_factor_secret', 'last_login_ip', 'login_count'),
            'classes': ('collapse',)
        }),
        ('Session', {
            'fields': ('session_key', 'session_expires_at', 'last_activity'),
            'classes': ('collapse',)
        }),
    )
    
    def user_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:accounts_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.email)
    user_link.short_description = 'User'
    
    def role_badge(self, obj):
        colors = {
            'super_admin': '#9c27b0',
            'admin': '#2196f3',
            'moderator': '#ff9800',
            'viewer': '#757575',
        }
        color = colors.get(obj.role, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_role_display()
        )
    role_badge.short_description = 'Role'
    
    def last_activity_display(self, obj):
        if obj.last_activity:
            delta = timezone.now() - obj.last_activity
            if delta.total_seconds() < 60:
                return f"{int(delta.total_seconds())} seconds ago"
            elif delta.total_seconds() < 3600:
                return f"{int(delta.total_seconds() / 60)} minutes ago"
            elif delta.total_seconds() < 86400:
                return f"{int(delta.total_seconds() / 3600)} hours ago"
            return obj.last_activity.strftime('%Y-%m-%d %H:%M')
        return '-'
    last_activity_display.short_description = 'Last Activity'
    
    def status_badge(self, obj):
        if obj.is_online():
            return format_html('<span style="color: green;">● Online</span>')
        return format_html('<span style="color: gray;">● Offline</span>')
    status_badge.short_description = 'Status'
    
    actions = ['make_super_admin', 'make_admin', 'make_moderator', 'make_viewer']
    
    def make_super_admin(self, request, queryset):
        queryset.update(role='super_admin')
    make_super_admin.short_description = 'Make Super Admin'
    
    def make_admin(self, request, queryset):
        queryset.update(role='admin')
    make_admin.short_description = 'Make Admin'
    
    def make_moderator(self, request, queryset):
        queryset.update(role='moderator')
    make_moderator.short_description = 'Make Moderator'
    
    def make_viewer(self, request, queryset):
        queryset.update(role='viewer')
    make_viewer.short_description = 'Make Viewer'


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'admin_email', 'action_type_badge', 'resource_type', 
        'resource_id_short', 'ip_address', 'response_status', 'created_at'
    ]
    list_filter = ['action_type', 'resource_type', 'response_status', 'created_at']
    search_fields = ['admin_user__user__email', 'resource_id', 'resource_name', 'ip_address']
    readonly_fields = ['changes', 'request_data']
    
    def admin_email(self, obj):
        if obj.admin_user:
            return obj.admin_user.user.email
        return 'System'
    admin_email.short_description = 'Admin'
    
    def action_type_badge(self, obj):
        colors = {
            'create': '#4caf50',
            'update': '#2196f3',
            'delete': '#f44336',
            'view': '#9e9e9e',
            'login': '#ff9800',
            'logout': '#ff5722',
            'export': '#9c27b0',
            'setting_change': '#00bcd4',
            'permission_change': '#e91e63',
        }
        color = colors.get(obj.action_type, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_action_type_display()
        )
    action_type_badge.short_description = 'Action'
    
    def resource_id_short(self, obj):
        return obj.resource_id[:12] + '...' if len(obj.resource_id) > 12 else obj.resource_id
    resource_id_short.short_description = 'Resource ID'
    
    fieldsets = (
        ('Action Info', {
            'fields': ('admin_user', 'action_type', 'resource_type', 'resource_id', 'resource_name')
        }),
        ('Changes', {
            'fields': ('changes',),
            'classes': ('wide',)
        }),
        ('Request Details', {
            'fields': ('request_method', 'request_path', 'request_data', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Response', {
            'fields': ('response_status', 'response_time_ms'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'key', 'value_preview', 'setting_type_badge', 'category', 
        'is_public', 'updated_by_email', 'updated_at'
    ]
    list_filter = ['setting_type', 'category', 'is_public', 'is_encrypted']
    search_fields = ['key', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Setting', {
            'fields': ('key', 'value', 'setting_type', 'description')
        }),
        ('Category', {
            'fields': ('category', 'is_public', 'is_encrypted')
        }),
        ('Validation', {
            'fields': ('min_value', 'max_value', 'allowed_values'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def value_preview(self, obj):
        value = str(obj.get_display_value())
        if len(value) > 50:
            value = value[:47] + '...'
        return value
    value_preview.short_description = 'Value'
    
    def setting_type_badge(self, obj):
        colors = {
            'string': '#4caf50',
            'integer': '#2196f3',
            'float': '#ff9800',
            'boolean': '#9c27b0',
            'json': '#f44336',
            'list': '#00bcd4',
        }
        color = colors.get(obj.setting_type, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_setting_type_display()
        )
    setting_type_badge.short_description = 'Type'
    
    def updated_by_email(self, obj):
        if obj.updated_by:
            return obj.updated_by.email
        return '-'
    updated_by_email.short_description = 'Updated By'
    
    def save_model(self, request, obj, form, change):
        if change:
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = [
        'title_preview', 'announcement_type_badge', 'target_audience_badge', 
        'is_active_indicator', 'start_date', 'end_date', 'view_count', 'click_count'
    ]
    list_filter = ['announcement_type', 'target_audience', 'is_active', 'created_at']
    search_fields = ['title', 'content']
    
    fieldsets = (
        ('Content', {
            'fields': ('title', 'content', 'announcement_type')
        }),
        ('Targeting', {
            'fields': ('target_audience', 'specific_users', 'specific_agents')
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'is_active')
        }),
        ('Actions', {
            'fields': ('action_url', 'action_text', 'is_dismissible'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('view_count', 'click_count', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def title_preview(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_preview.short_description = 'Title'
    
    def announcement_type_badge(self, obj):
        colors = {
            'info': '#2196f3',
            'warning': '#ff9800',
            'success': '#4caf50',
            'error': '#f44336',
            'maintenance': '#9c27b0',
            'feature': '#00bcd4',
        }
        color = colors.get(obj.announcement_type, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_announcement_type_display()
        )
    announcement_type_badge.short_description = 'Type'
    
    def target_audience_badge(self, obj):
        colors = {
            'all': '#4caf50',
            'admins': '#9c27b0',
            'agents': '#ff9800',
            'users': '#2196f3',
            'guests': '#757575',
        }
        color = colors.get(obj.target_audience, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_target_audience_display()
        )
    target_audience_badge.short_description = 'Audience'
    
    def is_active_indicator(self, obj):
        now = timezone.now()
        if not obj.is_active:
            return format_html('<span style="color: gray;">● Inactive</span>')
        if obj.end_date and now > obj.end_date:
            return format_html('<span style="color: orange;">● Expired</span>')
        if now < obj.start_date:
            return format_html('<span style="color: blue;">● Scheduled</span>')
        return format_html('<span style="color: green;">● Active</span>')
    is_active_indicator.short_description = 'Status'
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
    
    actions = ['activate_announcements', 'deactivate_announcements']
    
    def activate_announcements(self, request, queryset):
        queryset.update(is_active=True)
    activate_announcements.short_description = 'Activate selected announcements'
    
    def deactivate_announcements(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_announcements.short_description = 'Deactivate selected announcements'


@admin.register(AdminDashboardWidget)
class AdminDashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['title', 'admin_email', 'widget_type_badge', 'position', 'order', 'is_visible']
    list_filter = ['widget_type', 'position', 'is_visible']
    search_fields = ['title', 'admin_user__user__email']
    
    def admin_email(self, obj):
        return obj.admin_user.user.email
    admin_email.short_description = 'Admin'
    
    def widget_type_badge(self, obj):
        colors = {
            'stats': '#4caf50',
            'chart': '#2196f3',
            'table': '#ff9800',
            'alert': '#f44336',
            'feed': '#9c27b0',
            'custom': '#757575',
        }
        color = colors.get(obj.widget_type, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_widget_type_display()
        )
    widget_type_badge.short_description = 'Type'


@admin.register(SystemBackup)
class SystemBackupAdmin(admin.ModelAdmin):
    list_display = ['filename', 'backup_type_badge', 'status_badge', 'file_size_mb', 'created_at', 'completed_at']
    list_filter = ['backup_type', 'status', 'created_at']
    search_fields = ['filename']
    readonly_fields = ['filename', 'file_size_bytes', 'metadata', 'error_message']
    
    def backup_type_badge(self, obj):
        colors = {
            'database': '#4caf50',
            'files': '#2196f3',
            'full': '#9c27b0',
        }
        color = colors.get(obj.backup_type, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_backup_type_display()
        )
    backup_type_badge.short_description = 'Type'
    
    def status_badge(self, obj):
        colors = {
            'pending': '#ff9800',
            'running': '#2196f3',
            'success': '#4caf50',
            'failed': '#f44336',
        }
        color = colors.get(obj.status, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def file_size_mb(self, obj):
        if obj.file_size_bytes:
            return f"{obj.file_size_bytes / (1024 * 1024):.2f} MB"
        return '-'
    file_size_mb.short_description = 'Size'


@admin.register(MaintenanceMode)
class MaintenanceModeAdmin(admin.ModelAdmin):
    list_display = ['is_enabled_indicator', 'message_preview', 'allow_admins', 'scheduled_start', 'scheduled_end']
    fieldsets = (
        ('Maintenance Settings', {
            'fields': ('is_enabled', 'message', 'allow_admins', 'allow_ips')
        }),
        ('Schedule', {
            'fields': ('scheduled_start', 'scheduled_end'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('started_by',),
            'classes': ('collapse',)
        }),
    )
    
    def is_enabled_indicator(self, obj):
        if obj.is_enabled:
            return format_html('<span style="color: red;">● Enabled</span>')
        return format_html('<span style="color: green;">● Disabled</span>')
    is_enabled_indicator.short_description = 'Status'
    
    def message_preview(self, obj):
        return obj.message[:50] + '...' if len(obj.message) > 50 else obj.message
    message_preview.short_description = 'Message'
    
    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get('is_enabled') and not obj.pk:
            obj.started_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'task_type_badge', 'frequency_badge', 'is_active_indicator', 
        'scheduled_time', 'last_run', 'next_run', 'last_status_badge'
    ]
    list_filter = ['task_type', 'frequency', 'is_active', 'last_status']
    search_fields = ['name']
    
    fieldsets = (
        ('Task Info', {
            'fields': ('name', 'task_type', 'frequency', 'parameters')
        }),
        ('Schedule', {
            'fields': ('scheduled_time', 'last_run', 'next_run', 'is_active')
        }),
        ('Execution', {
            'fields': ('last_status', 'last_output'),
            'classes': ('collapse',)
        }),
    )
    
    def task_type_badge(self, obj):
        colors = {
            'backup': '#4caf50',
            'cleanup': '#ff9800',
            'report': '#2196f3',
            'email': '#9c27b0',
            'sync': '#00bcd4',
        }
        color = colors.get(obj.task_type, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_task_type_display()
        )
    task_type_badge.short_description = 'Type'
    
    def frequency_badge(self, obj):
        colors = {
            'once': '#757575',
            'hourly': '#2196f3',
            'daily': '#4caf50',
            'weekly': '#ff9800',
            'monthly': '#9c27b0',
        }
        color = colors.get(obj.frequency, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_frequency_display()
        )
    frequency_badge.short_description = 'Frequency'
    
    def is_active_indicator(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">● Active</span>')
        return format_html('<span style="color: gray;">● Inactive</span>')
    is_active_indicator.short_description = 'Status'
    
    def last_status_badge(self, obj):
        colors = {
            'pending': '#ff9800',
            'running': '#2196f3',
            'success': '#4caf50',
            'failed': '#f44336',
        }
        color = colors.get(obj.last_status, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.last_status.upper()
        )
    last_status_badge.short_description = 'Last Status'
    
    actions = ['run_now', 'activate_tasks', 'deactivate_tasks']
    
    def run_now(self, request, queryset):
        for task in queryset:
            task.last_run = timezone.now()
            task.save()
        self.message_user(request, f"{queryset.count()} tasks marked for immediate execution")
    run_now.short_description = 'Run selected tasks now'
    
    def activate_tasks(self, request, queryset):
        queryset.update(is_active=True)
    activate_tasks.short_description = 'Activate selected tasks'
    
    def deactivate_tasks(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_tasks.short_description = 'Deactivate selected tasks'


@admin.register(APIRateLimit)
class APIRateLimitAdmin(admin.ModelAdmin):
    list_display = ['endpoint', 'method', 'requests_per_minute', 'requests_per_hour', 'requests_per_day', 'burst_limit', 'is_enabled']
    list_filter = ['method', 'is_enabled']
    search_fields = ['endpoint']
    
    fieldsets = (
        ('Endpoint', {
            'fields': ('endpoint', 'method')
        }),
        ('Rate Limits', {
            'fields': ('requests_per_minute', 'requests_per_hour', 'requests_per_day', 'burst_limit')
        }),
        ('Status', {
            'fields': ('is_enabled',)
        }),
    )


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = ['title_preview', 'level_badge', 'recipient_email', 'is_read', 'is_dismissed', 'created_at']
    list_filter = ['level', 'is_read', 'is_dismissed', 'created_at']
    search_fields = ['title', 'message', 'recipient__user__email']
    readonly_fields = ['created_at']
    
    def title_preview(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_preview.short_description = 'Title'
    
    def level_badge(self, obj):
        colors = {
            'info': '#2196f3',
            'success': '#4caf50',
            'warning': '#ff9800',
            'error': '#f44336',
            'critical': '#9c27b0',
        }
        color = colors.get(obj.level, '#757575')
        return format_html(
            '<span style="background: {}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color, obj.get_level_display()
        )
    level_badge.short_description = 'Level'
    
    def recipient_email(self, obj):
        return obj.recipient.user.email
    recipient_email.short_description = 'Recipient'
    
    actions = ['mark_as_read', 'mark_as_unread', 'dismiss_notifications']
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = 'Mark as read'
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = 'Mark as unread'
    
    def dismiss_notifications(self, request, queryset):
        queryset.update(is_dismissed=True)
    dismiss_notifications.short_description = 'Dismiss selected notifications'


# Custom Admin Site Configuration
admin.site.site_header = "Global Work Marketplace - Super Admin"
admin.site.site_title = "Marketplace Admin Portal"
admin.site.index_title = "Welcome to Marketplace Administration"