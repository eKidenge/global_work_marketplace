# apps/agents/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Agent, Capability, AgentHeartbeat

@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'agent_type', 'status_badge', 'trust_score', 'success_rate', 'total_tasks', 'is_online']
    list_filter = ['agent_type', 'is_active', 'is_available']
    search_fields = ['name', 'user__email']
    
    fieldsets = (
        ('Basic Info', {'fields': ('name', 'agent_type', 'user', 'description')}),
        ('Capabilities', {'fields': ('capabilities',)}),
        ('Performance', {'fields': ('trust_score', 'success_rate', 'total_tasks', 'total_earned')}),
        ('Status', {'fields': ('is_active', 'is_available', 'last_heartbeat')}),
    )
    
    def status_badge(self, obj):
        if obj.is_online:
            return format_html('<span style="color: green;">● Online</span>')
        return format_html('<span style="color: red;">● Offline</span>')
    status_badge.short_description = 'Status'
    
    actions = ['activate_agents', 'deactivate_agents']
    
    def activate_agents(self, request, queryset):
        queryset.update(is_active=True)
    activate_agents.short_description = "Activate selected agents"
    
    def deactivate_agents(self, request, queryset):
        queryset.update(is_active=False)
    deactivate_agents.short_description = "Deactivate selected agents"

@admin.register(Capability)
class CapabilityAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'is_ai_capable', 'is_human_capable']
    list_filter = ['category', 'is_ai_capable', 'is_human_capable']
    search_fields = ['name']

@admin.register(AgentHeartbeat)
class AgentHeartbeatAdmin(admin.ModelAdmin):
    list_display = ['agent', 'status', 'latency_ms', 'created_at']
    list_filter = ['status', 'created_at']
    readonly_fields = ['metrics']