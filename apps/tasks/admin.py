# apps/tasks/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Task, TaskTemplate, MicroTask

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'title_preview', 'state_badge', 'budget_sats', 'matched_agent', 'created_at']
    list_filter = ['state', 'priority', 'required_human', 'created_at']
    search_fields = ['title', 'description']
    
    fieldsets = (
        ('Task Info', {'fields': ('title', 'description', 'parent_task', 'is_microtask')}),
        ('Requirements', {'fields': ('required_capabilities', 'required_human', 'priority')}),
        ('Economics', {'fields': ('budget_sats', 'assigned_price_sats')}),
        ('Status', {'fields': ('state', 'matched_agent', 'assigned_at', 'started_at', 'completed_at')}),
    )
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    def title_preview(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_preview.short_description = 'Title'
    
    def state_badge(self, obj):
        colors = {
            'open': 'blue', 'assigned': 'orange', 'executing': 'green',
            'completed': 'darkgreen', 'failed': 'red'
        }
        color = colors.get(obj.state, 'gray')
        return format_html('<span style="color: {};">●</span> {}', color, obj.state)
    state_badge.short_description = 'State'
    
    actions = ['force_complete', 'force_fail']
    
    def force_complete(self, request, queryset):
        from django.utils import timezone
        queryset.update(state='completed', completed_at=timezone.now())
    force_complete.short_description = "Force complete"
    
    def force_fail(self, request, queryset):
        queryset.update(state='failed')
    force_fail.short_description = "Force fail"

@admin.register(TaskTemplate)
class TaskTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'default_budget_sats', 'usage_count', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['name']

@admin.register(MicroTask)
class MicroTaskAdmin(admin.ModelAdmin):
    list_display = ['parent_task', 'title', 'order', 'completed', 'assigned_agent']
    list_filter = ['completed']