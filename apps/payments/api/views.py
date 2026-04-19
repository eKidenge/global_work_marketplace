# apps/payments/api/views.py
from django.views import View
from django.http import JsonResponse
from django.utils import timezone
import json
import uuid

class APIWalletView(View):
    def get(self, request):
        return JsonResponse({
            'wallet_id': str(uuid.uuid4()),
            'balance_sats': 10000,
            'available_sats': 9500,
            'reserved_sats': 500,
            'currency': 'sats'
        })

class APIWalletBalanceView(View):
    def get(self, request):
        return JsonResponse({'balance_sats': 10000, 'available_sats': 9500})

class APITransactionListView(View):
    def get(self, request):
        return JsonResponse({
            'transactions': [],
            'total': 0,
            'page': 1
        })

class APITransactionDetailView(View):
    def get(self, request, tx_id):
        return JsonResponse({
            'id': tx_id,
            'amount_sats': 100,
            'type': 'payment',
            'status': 'completed',
            'created_at': timezone.now().isoformat()
        })

class APIEscrowListView(View):
    def get(self, request):
        return JsonResponse({'escrows': [], 'total': 0})

class APIEscrowDetailView(View):
    def get(self, request, escrow_id):
        return JsonResponse({
            'id': escrow_id,
            'amount_sats': 500,
            'status': 'held',
            'buyer_id': str(uuid.uuid4()),
            'seller_id': str(uuid.uuid4())
        })

class APIPayView(View):
    def post(self, request):
        return JsonResponse({
            'status': 'success',
            'transaction_id': str(uuid.uuid4()),
            'amount_sats': 100
        })