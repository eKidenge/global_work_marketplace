# apps/payments/admin.py
from django.contrib import admin
from .models import Wallet, Transaction, EscrowContract

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['owner_id', 'owner_type', 'balance_sats', 'available_sats', 'total_deposited']
    list_filter = ['owner_type']
    
    def available_sats(self, obj):
        return obj.available_sats
    available_sats.short_description = 'Available Sats'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id_short', 'from_wallet', 'to_wallet', 'amount_sats', 'type', 'status', 'created_at']
    list_filter = ['type', 'status', 'created_at']
    search_fields = ['payment_hash']
    
    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'ID'
    
    actions = ['mark_completed', 'mark_failed']
    
    def mark_completed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='completed', completed_at=timezone.now())
    mark_completed.short_description = "Mark as completed"
    
    def mark_failed(self, request, queryset):
        queryset.update(status='failed')
    mark_failed.short_description = "Mark as failed"

@admin.register(EscrowContract)
class EscrowContractAdmin(admin.ModelAdmin):
    list_display = ['task', 'buyer', 'seller', 'amount_sats', 'status', 'expires_at']
    list_filter = ['status', 'created_at']