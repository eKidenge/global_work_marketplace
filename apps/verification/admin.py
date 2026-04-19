# apps/verification/admin.py
from django.contrib import admin
from .models import Verification, Reputation, Dispute

@admin.register(Verification)
class VerificationAdmin(admin.ModelAdmin):
    list_display = ['task', 'verification_type', 'status', 'quality_score', 'verified_at']
    list_filter = ['verification_type', 'status']

@admin.register(Reputation)
class ReputationAdmin(admin.ModelAdmin):
    list_display = ['agent', 'overall_score', 'reliability_score', 'total_reviews']
    readonly_fields = ['overall_score', 'reliability_score', 'quality_score', 'speed_score']

@admin.register(Dispute)
class DisputeAdmin(admin.ModelAdmin):
    list_display = ['task', 'raised_by', 'reason', 'status', 'created_at']
    list_filter = ['reason', 'status']