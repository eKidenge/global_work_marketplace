# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile, APIKey

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['email', 'username', 'wallet_balance', 'is_verified', 'is_staff', 'date_joined']
    list_filter = ['is_staff', 'is_active', 'is_verified', 'date_joined']
    search_fields = ['email', 'username']
    
    fieldsets = UserAdmin.fieldsets + (
        ('Marketplace Info', {
            'fields': ('wallet_balance', 'total_spent', 'total_earned', 'rating', 'is_verified', 'verified_at')
        }),
    )

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone_number', 'location', 'email_notifications']
    search_fields = ['user__email', 'phone_number']

@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'last_used', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['user__email', 'name']