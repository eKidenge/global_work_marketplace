# apps/agents/forms.py
from django import forms
from .models import Agent


class AgentRegisterForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['name', 'description', 'agent_type', 'hourly_rate_sats', 'api_endpoint']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


class AgentSettingsForm(forms.ModelForm):
    class Meta:
        model = Agent
        fields = ['name', 'description', 'hourly_rate_sats', 'is_available']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class AgentCapabilityForm(forms.Form):
    capabilities = forms.MultipleChoiceField(
        choices=[],  # Will be populated in __init__
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Capability
        self.fields['capabilities'].choices = [(c.name, c.name) for c in Capability.objects.all()]