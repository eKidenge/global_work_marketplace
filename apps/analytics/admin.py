# apps/analytics/admin.py
from django.contrib import admin
from .models import Metric, DailyReport, Alert

@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'value', 'timestamp']
    list_filter = ['category', 'name', 'timestamp']
    readonly_fields = ['tags']

@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ['date', 'generated_at']
    readonly_fields = ['data']

@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'level', 'is_resolved', 'created_at']
    list_filter = ['level', 'is_resolved']