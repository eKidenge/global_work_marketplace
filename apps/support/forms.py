# apps/support/forms.py
from django import forms
from .models import Ticket, TicketMessage

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['subject', 'priority', 'message', 'attachments']
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Brief summary of your issue'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-control'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Please provide detailed information about your issue...'
            }),
            'attachments': forms.ClearableFileInput(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set priority choices
        self.fields['priority'].choices = [
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('urgent', 'Urgent'),
        ]

class TicketReplyForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Type your reply here...'
        }),
        label='Your Reply'
    )
    attachments = forms.FileField(
        required=False,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control'
        }),
        label='Attachments (optional)'
    )