# apps/payments/api/urls.py
from django.urls import path
from . import views

app_name = 'payments_api'

urlpatterns = [
    path('wallet/', views.APIWalletView.as_view(), name='api_wallet'),
    path('wallet/balance/', views.APIWalletBalanceView.as_view(), name='api_wallet_balance'),
    path('transactions/', views.APITransactionListView.as_view(), name='api_transactions'),
    path('transactions/<uuid:tx_id>/', views.APITransactionDetailView.as_view(), name='api_transaction_detail'),
    path('escrow/', views.APIEscrowListView.as_view(), name='api_escrow_list'),
    path('escrow/<uuid:escrow_id>/', views.APIEscrowDetailView.as_view(), name='api_escrow_detail'),
    path('pay/', views.APIPayView.as_view(), name='api_pay'),
]