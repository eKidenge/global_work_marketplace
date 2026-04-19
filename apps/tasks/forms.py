# apps/tasks/forms.py
from django import forms
from .models import Task, MicroTask, TaskTemplate


class TaskCreateForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'budget_sats', 'priority', 'required_human']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
        }


class TaskEditForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'budget_sats', 'priority']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
        }


class TaskBidForm(forms.Form):
    bid_amount = forms.IntegerField(min_value=1, label='Your bid (sats)')
    message = forms.CharField(widget=forms.Textarea, required=False, label='Message to task creator')


class MicroTaskForm(forms.ModelForm):
    class Meta:
        model = MicroTask
        fields = ['title', 'description', 'budget_sats']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class TaskTemplateForm(forms.ModelForm):
    class Meta:
        model = TaskTemplate
        fields = ['name', 'category', 'description', 'schema', 'estimated_duration_ms', 'default_budget_sats']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'schema': forms.Textarea(attrs={'rows': 5, 'class': 'font-mono'}),
        }