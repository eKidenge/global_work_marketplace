# apps/webhooks/forms.py
from django import forms
from .models import WebhookEndpoint

class WebhookEndpointForm(forms.ModelForm):
    class Meta:
        model = WebhookEndpoint
        fields = ['url', 'events', 'is_active']
        widgets = {
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://your-domain.com/webhook-endpoint'
            }),
            'events': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': 10
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set available event choices
        AVAILABLE_EVENTS = [
            ('task.created', 'Task Created'),
            ('task.completed', 'Task Completed'),
            ('task.failed', 'Task Failed'),
            ('agent.online', 'Agent Online'),
            ('agent.offline', 'Agent Offline'),
            ('payment.received', 'Payment Received'),
            ('payment.sent', 'Payment Sent'),
            ('verification.approved', 'Verification Approved'),
            ('verification.rejected', 'Verification Rejected'),
        ]
        self.fields['events'].choices = AVAILABLE_EVENTS
        self.fields['events'].help_text = 'Hold Ctrl to select multiple events'

class WebhookTestForm(forms.Form):
    """Form for testing webhook endpoints"""
    event_type = forms.ChoiceField(
        choices=[
            ('task.created', 'Task Created'),
            ('task.completed', 'Task Completed'),
            ('payment.received', 'Payment Received'),
            ('test', 'Test Event'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    custom_payload = forms.JSONField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': '{"custom": "data"}'
        }),
        help_text='Optional custom JSON payload for testing'
    )