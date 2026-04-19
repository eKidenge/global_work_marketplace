# apps/payments/urls.py
from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Wallet
    path('wallet/', views.WalletView.as_view(), name='wallet'),
    path('wallet/deposit/', views.DepositView.as_view(), name='deposit'),
    path('wallet/withdraw/', views.WithdrawView.as_view(), name='withdraw'),
    path('wallet/transactions/', views.TransactionHistoryView.as_view(), name='transactions'),
    
    # Transactions
    path('transactions/<uuid:transaction_id>/', views.TransactionDetailView.as_view(), name='transaction_detail'),
    path('transactions/<uuid:transaction_id>/receipt/', views.ReceiptView.as_view(), name='receipt'),
    
    # Escrow
    path('escrow/', views.EscrowListView.as_view(), name='escrow_list'),
    path('escrow/<uuid:escrow_id>/', views.EscrowDetailView.as_view(), name='escrow_detail'),
    path('escrow/<uuid:escrow_id>/release/', views.ReleaseEscrowView.as_view(), name='release_escrow'),
    path('escrow/<uuid:escrow_id>/dispute/', views.DisputeEscrowView.as_view(), name='dispute_escrow'),
    
    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoices'),
    path('invoices/<uuid:invoice_id>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    path('invoices/<uuid:invoice_id>/download/', views.DownloadInvoiceView.as_view(), name='download_invoice'),
    
    # Payment methods
    path('methods/', views.PaymentMethodListView.as_view(), name='payment_methods'),
    path('methods/add/', views.AddPaymentMethodView.as_view(), name='add_payment_method'),
    path('methods/<uuid:method_id>/delete/', views.DeletePaymentMethodView.as_view(), name='delete_payment_method'),
    
    # Lightning Network
    path('lightning/invoice/', views.CreateLightningInvoiceView.as_view(), name='lightning_invoice'),
    path('lightning/pay/', views.PayLightningInvoiceView.as_view(), name='lightning_pay'),
    path('lightning/callback/', views.LightningCallbackView.as_view(), name='lightning_callback'),
]