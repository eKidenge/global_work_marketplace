# apps/payments/forms.py
from django import forms

class DepositForm(forms.Form):
    amount_sats = forms.IntegerField(
        min_value=1,
        max_value=100000000,
        label='Amount (sats)',
        help_text='Minimum 1 sat, maximum 100,000,000 sats',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount in sats'
        })
    )
    
    payment_method = forms.ChoiceField(
        choices=[
            ('lightning', 'Lightning Network'),
            ('onchain', 'Bitcoin On-chain'),
            ('bank_transfer', 'Bank Transfer'),
        ],
        label='Payment Method',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class WithdrawForm(forms.Form):
    amount_sats = forms.IntegerField(
        min_value=1,
        label='Amount (sats)',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter amount in sats'
        })
    )
    
    withdraw_address = forms.CharField(
        max_length=500,
        label='Withdrawal Address',
        help_text='Lightning invoice or Bitcoin address',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter withdrawal address or invoice'
        })
    )
    
    def __init__(self, *args, **kwargs):
        self.wallet_balance = kwargs.pop('wallet_balance', 0)
        super().__init__(*args, **kwargs)
    
    def clean_amount_sats(self):
        amount = self.cleaned_data['amount_sats']
        if amount > self.wallet_balance:
            raise forms.ValidationError(f'Insufficient balance. You have {self.wallet_balance} sats.')
        return amount