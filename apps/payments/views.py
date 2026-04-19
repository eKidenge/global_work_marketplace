# apps/payments/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
import json
from .models import Wallet, Transaction, EscrowContract
from .forms import DepositForm, WithdrawForm

class WalletView(LoginRequiredMixin, View):
    template_name = 'payments/wallet.html'
    
    def get(self, request):
        wallet, created = Wallet.objects.get_or_create(
            owner_id=request.user.id,
            owner_type='user',
            defaults={'balance_sats': 0}
        )
        
        recent_transactions = Transaction.objects.filter(
            Q(from_wallet=wallet) | Q(to_wallet=wallet)
        ).order_by('-created_at')[:20]
        
        context = {
            'wallet': wallet,
            'balance_sats': wallet.balance_sats,
            'available_sats': wallet.available_sats,
            'reserved_sats': wallet.reserved_sats,
            'recent_transactions': recent_transactions,
            'total_deposited': wallet.total_deposited,
            'total_withdrawn': wallet.total_withdrawn,
            'total_spent': wallet.total_spent,
        }
        return render(request, self.template_name, context)

class DepositView(LoginRequiredMixin, View):
    template_name = 'payments/deposit.html'
    
    def get(self, request):
        form = DepositForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = DepositForm(request.POST)
        if form.is_valid():
            amount_sats = form.cleaned_data['amount_sats']
            payment_method = form.cleaned_data['payment_method']
            
            wallet, _ = Wallet.objects.get_or_create(
                owner_id=request.user.id,
                owner_type='user'
            )
            
            # Create transaction
            transaction = Transaction.objects.create(
                from_wallet=None,
                to_wallet=wallet,
                amount_sats=amount_sats,
                type='deposit',
                status='pending',
                metadata={'payment_method': payment_method}
            )
            
            # For demo, auto-complete
            transaction.status = 'completed'
            transaction.completed_at = timezone.now()
            transaction.save()
            
            # Update wallet balance
            wallet.balance_sats += amount_sats
            wallet.total_deposited += amount_sats
            wallet.save()
            
            messages.success(request, f'Successfully deposited {amount_sats} sats!')
            return redirect('payments:wallet')
        
        return render(request, self.template_name, {'form': form})

class WithdrawView(LoginRequiredMixin, View):
    template_name = 'payments/withdraw.html'
    
    def get(self, request):
        wallet = Wallet.objects.filter(owner_id=request.user.id, owner_type='user').first()
        form = WithdrawForm(initial={'wallet_balance': wallet.balance_sats if wallet else 0})
        return render(request, self.template_name, {'form': form, 'wallet': wallet})
    
    def post(self, request):
        form = WithdrawForm(request.POST)
        if form.is_valid():
            amount_sats = form.cleaned_data['amount_sats']
            withdraw_address = form.cleaned_data['withdraw_address']
            
            wallet = Wallet.objects.get(owner_id=request.user.id, owner_type='user')
            
            if wallet.balance_sats < amount_sats:
                messages.error(request, 'Insufficient balance')
                return render(request, self.template_name, {'form': form, 'wallet': wallet})
            
            # Create transaction
            Transaction.objects.create(
                from_wallet=wallet,
                to_wallet=None,
                amount_sats=amount_sats,
                type='withdrawal',
                status='pending',
                metadata={'withdraw_address': withdraw_address}
            )
            
            # Reserve funds
            wallet.reserved_sats += amount_sats
            wallet.save()
            
            messages.info(request, f'Withdrawal request for {amount_sats} sats submitted for processing')
            return redirect('payments:wallet')
        
        return render(request, self.template_name, {'form': form})

class TransactionHistoryView(LoginRequiredMixin, View):
    template_name = 'payments/transactions.html'
    
    def get(self, request):
        wallet = Wallet.objects.filter(owner_id=request.user.id, owner_type='user').first()
        
        if not wallet:
            return render(request, self.template_name, {'transactions': []})
        
        transactions = Transaction.objects.filter(
            Q(from_wallet=wallet) | Q(to_wallet=wallet)
        ).order_by('-created_at')
        
        # Filtering
        tx_type = request.GET.get('type')
        if tx_type:
            transactions = transactions.filter(type=tx_type)
        
        status = request.GET.get('status')
        if status:
            transactions = transactions.filter(status=status)
        
        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(transactions, 30)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'transactions': page_obj,
            'wallet': wallet,
            'total_volume': transactions.filter(status='completed').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            'selected_type': tx_type,
            'selected_status': status,
        }
        return render(request, self.template_name, context)

class TransactionDetailView(LoginRequiredMixin, View):
    template_name = 'payments/transaction_detail.html'
    
    def get(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
        
        # Check permission
        user_wallet = Wallet.objects.filter(owner_id=request.user.id, owner_type='user').first()
        if transaction.from_wallet != user_wallet and transaction.to_wallet != user_wallet:
            messages.error(request, 'You do not have permission to view this transaction')
            return redirect('payments:transactions')
        
        context = {
            'transaction': transaction,
            'from_wallet': transaction.from_wallet,
            'to_wallet': transaction.to_wallet,
        }
        return render(request, self.template_name, context)

class EscrowListView(LoginRequiredMixin, View):
    template_name = 'payments/escrow_list.html'
    
    def get(self, request):
        escrows = EscrowContract.objects.filter(
            Q(buyer=request.user) | Q(seller__user=request.user)
        ).select_related('task', 'buyer', 'seller')
        
        context = {
            'escrows': escrows,
            'status_counts': {
                'pending': escrows.filter(status='pending').count(),
                'held': escrows.filter(status='held').count(),
                'released': escrows.filter(status='released').count(),
                'disputed': escrows.filter(status='disputed').count(),
            },
        }
        return render(request, self.template_name, context)

class EscrowDetailView(LoginRequiredMixin, View):
    template_name = 'payments/escrow_detail.html'
    
    def get(self, request, escrow_id):
        escrow = get_object_or_404(EscrowContract, id=escrow_id)
        
        # Check permission
        if escrow.buyer != request.user and escrow.seller.user != request.user:
            messages.error(request, 'You do not have permission to view this escrow')
            return redirect('payments:escrow_list')
        
        context = {
            'escrow': escrow,
            'task': escrow.task,
            'buyer': escrow.buyer,
            'seller': escrow.seller,
            'can_release': escrow.status == 'held' and request.user == escrow.buyer,
            'can_dispute': escrow.status == 'held' and (request.user == escrow.buyer or request.user == escrow.seller.user),
        }
        return render(request, self.template_name, context)

class ReleaseEscrowView(LoginRequiredMixin, View):
    def post(self, request, escrow_id):
        escrow = get_object_or_404(EscrowContract, id=escrow_id, buyer=request.user)
        
        if escrow.status == 'held':
            # Release funds
            escrow.status = 'released'
            escrow.released_at = timezone.now()
            escrow.save()
            
            # Create transaction
            buyer_wallet = Wallet.objects.get(owner_id=escrow.buyer.id, owner_type='user')
            seller_wallet = Wallet.objects.get(owner_id=escrow.seller.id, owner_type='agent')
            
            Transaction.objects.create(
                from_wallet=buyer_wallet,
                to_wallet=seller_wallet,
                amount_sats=escrow.amount_sats,
                type='payment',
                status='completed',
                completed_at=timezone.now()
            )
            
            messages.success(request, f'Released {escrow.amount_sats} sats to {escrow.seller.name}')
        
        return redirect('payments:escrow_detail', escrow_id=escrow.id)

class InvoiceListView(LoginRequiredMixin, View):
    template_name = 'payments/invoices.html'
    
    def get(self, request):
        transactions = Transaction.objects.filter(
            Q(from_wallet__owner_id=request.user.id) | Q(to_wallet__owner_id=request.user.id),
            type__in=['payment', 'deposit']
        ).order_by('-created_at')
        
        context = {
            'invoices': transactions[:50],
            'total_amount': transactions.filter(status='completed').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
        }
        return render(request, self.template_name, context)

class InvoiceDetailView(LoginRequiredMixin, View):
    template_name = 'payments/invoice_detail.html'
    
    def get(self, request, invoice_id):
        transaction = get_object_or_404(Transaction, id=invoice_id)
        
        # Check permission
        user_wallet = Wallet.objects.filter(owner_id=request.user.id, owner_type='user').first()
        if transaction.from_wallet != user_wallet and transaction.to_wallet != user_wallet:
            messages.error(request, 'You do not have permission to view this invoice')
            return redirect('payments:invoices')
        
        context = {
            'invoice': transaction,
            'from_wallet': transaction.from_wallet,
            'to_wallet': transaction.to_wallet,
        }
        return render(request, self.template_name, context)

class PaymentMethodListView(LoginRequiredMixin, View):
    template_name = 'payments/payment_methods.html'
    
    def get(self, request):
        # Get saved payment methods from user profile
        payment_methods = request.user.profile.payment_methods if hasattr(request.user, 'profile') else []
        
        context = {
            'payment_methods': payment_methods,
            'available_methods': ['lightning', 'onchain', 'bank_transfer'],
        }
        return render(request, self.template_name, context)

class ReceiptView(LoginRequiredMixin, View):
    """Generate receipt for a transaction"""
    template_name = 'payments/receipt.html'
    
    def get(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
        
        # Check permission
        user_wallet = Wallet.objects.filter(owner_id=request.user.id, owner_type='user').first()
        if transaction.from_wallet != user_wallet and transaction.to_wallet != user_wallet:
            messages.error(request, 'You do not have permission to view this receipt')
            return redirect('payments:transactions')
        
        context = {
            'transaction': transaction,
            'date': transaction.created_at,
            'amount': transaction.amount_sats,
            'status': transaction.status,
        }
        return render(request, self.template_name, context)

class DisputeEscrowView(LoginRequiredMixin, View):
    """Handle escrow disputes"""
    template_name = 'payments/dispute_escrow.html'
    
    def get(self, request, escrow_id):
        escrow = get_object_or_404(EscrowContract, id=escrow_id)
        
        # Check permission
        if escrow.buyer != request.user and escrow.seller.user != request.user:
            messages.error(request, 'You do not have permission to dispute this escrow')
            return redirect('payments:escrow_list')
        
        context = {
            'escrow': escrow,
            'task': escrow.task,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, escrow_id):
        escrow = get_object_or_404(EscrowContract, id=escrow_id)
        
        if escrow.status == 'held':
            escrow.status = 'disputed'
            escrow.dispute_reason = request.POST.get('reason', 'No reason provided')
            escrow.disputed_at = timezone.now()
            escrow.save()
            
            messages.warning(request, f'Dispute filed for escrow #{escrow_id}')
            return redirect('payments:escrow_detail', escrow_id=escrow.id)
        
        messages.error(request, 'Cannot dispute this escrow')
        return redirect('payments:escrow_list')

class DownloadInvoiceView(LoginRequiredMixin, View):
    """Download invoice as PDF"""
    
    def get(self, request, invoice_id):
        transaction = get_object_or_404(Transaction, id=invoice_id)
        
        # Check permission
        user_wallet = Wallet.objects.filter(owner_id=request.user.id, owner_type='user').first()
        if transaction.from_wallet != user_wallet and transaction.to_wallet != user_wallet:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # For now, return JSON. Later implement PDF generation
        response_data = {
            'invoice_id': str(transaction.id),
            'amount': transaction.amount_sats,
            'date': transaction.created_at.isoformat(),
            'status': transaction.status,
            'from': str(transaction.from_wallet.id) if transaction.from_wallet else 'External',
            'to': str(transaction.to_wallet.id) if transaction.to_wallet else 'External',
        }
        
        return JsonResponse(response_data)

class AddPaymentMethodView(LoginRequiredMixin, View):
    """Add a payment method to user profile"""
    
    def post(self, request):
        method_type = request.POST.get('method_type')
        method_details = request.POST.get('details')
        
        # Ensure user has profile
        if not hasattr(request.user, 'profile'):
            from apps.accounts.models import Profile
            Profile.objects.create(user=request.user)
        
        # Add to user profile
        if not hasattr(request.user.profile, 'payment_methods'):
            request.user.profile.payment_methods = []
        
        new_method = {
            'id': str(int(timezone.now().timestamp())),
            'type': method_type,
            'details': method_details,
            'added_at': timezone.now().isoformat(),
        }
        
        request.user.profile.payment_methods.append(new_method)
        request.user.profile.save()
        
        messages.success(request, f'Added {method_type} payment method')
        return redirect('payments:payment_methods')

class DeletePaymentMethodView(LoginRequiredMixin, View):
    """Delete a payment method"""
    
    def post(self, request, method_id):
        if hasattr(request.user, 'profile') and hasattr(request.user.profile, 'payment_methods'):
            request.user.profile.payment_methods = [
                method for method in request.user.profile.payment_methods 
                if method.get('id') != str(method_id)
            ]
            request.user.profile.save()
            messages.success(request, 'Payment method deleted')
        
        return redirect('payments:payment_methods')

class CreateLightningInvoiceView(LoginRequiredMixin, View):
    """Create a Lightning Network invoice"""
    
    def post(self, request):
        amount_sats = request.POST.get('amount_sats')
        memo = request.POST.get('memo', 'Payment to Global Work Marketplace')
        
        # This would integrate with LND or other Lightning node
        # For now, return a mock invoice
        invoice_data = {
            'payment_request': 'lnbc...',
            'payment_hash': 'mock_hash_' + str(int(timezone.now().timestamp())),
            'expires_at': (timezone.now() + timedelta(hours=1)).isoformat(),
            'amount_sats': amount_sats,
        }
        
        return JsonResponse(invoice_data)

class PayLightningInvoiceView(LoginRequiredMixin, View):
    """Pay a Lightning Network invoice"""
    
    def post(self, request):
        invoice = request.POST.get('invoice')
        amount_sats = request.POST.get('amount_sats')
        
        wallet = Wallet.objects.filter(owner_id=request.user.id, owner_type='user').first()
        
        if not wallet or wallet.balance_sats < int(amount_sats):
            return JsonResponse({'error': 'Insufficient balance'}, status=400)
        
        # Create transaction
        transaction = Transaction.objects.create(
            from_wallet=wallet,
            to_wallet=None,
            amount_sats=amount_sats,
            type='payment',
            status='pending',
            metadata={'lightning_invoice': invoice}
        )
        
        # This would actually pay the invoice via LND
        # For demo, mark as completed
        transaction.status = 'completed'
        transaction.completed_at = timezone.now()
        transaction.save()
        
        # Update wallet
        wallet.balance_sats -= int(amount_sats)
        wallet.total_spent += int(amount_sats)
        wallet.save()
        
        return JsonResponse({'success': True, 'transaction_id': str(transaction.id)})

class LightningCallbackView(View):
    """Webhook callback for Lightning payments"""
    
    def post(self, request):
        # Handle Lightning node callbacks
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        payment_hash = data.get('payment_hash')
        status = data.get('status')
        
        # Find and update transaction
        transaction = Transaction.objects.filter(
            metadata__lightning_payment_hash=payment_hash
        ).first()
        
        if transaction:
            if status == 'settled':
                transaction.status = 'completed'
                transaction.completed_at = timezone.now()
                transaction.save()
            elif status == 'failed':
                transaction.status = 'failed'
                transaction.save()
        
        return JsonResponse({'received': True})