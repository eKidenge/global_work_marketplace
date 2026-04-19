# apps/core_engine/admin.py
from django.contrib import admin
from .models import EngineDecision, EngineMetric, PolicyRule

@admin.register(EngineDecision)
class EngineDecisionAdmin(admin.ModelAdmin):
    list_display = ['task', 'decision_type', 'selected_agent_type', 'confidence_score', 'decision_time']
    list_filter = ['decision_type', 'decision_time']
    readonly_fields = ['reasoning', 'decision_log_json']

@admin.register(EngineMetric)
class EngineMetricAdmin(admin.ModelAdmin):
    list_display = ['metric_name', 'current_value', 'average_value', 'updated_at']
    readonly_fields = ['value_history_json']

@admin.register(PolicyRule)
class PolicyRuleAdmin(admin.ModelAdmin):
    list_display = ['name', 'rule_type', 'priority', 'is_active']
    list_filter = ['rule_type', 'is_active']
    search_fields = ['name']