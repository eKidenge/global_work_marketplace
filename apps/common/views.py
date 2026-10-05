# apps/common/views.py
from django.shortcuts import render
from django.views import View
from django.db.models import Sum

from apps.tasks.models import Task
from apps.agents.models import Agent
from apps.payments.models import Transaction


class LandingPageView(View):
    """Public landing page for the marketplace"""
    template_name = 'common/landing.html'

    def get(self, request):
        context = {
            'title': 'Global Work Marketplace',
            'description': 'The economic operating system for AI + humans',
            'user': request.user,

            # Live platform statistics (real data from the database)
            'total_tasks': Task.objects.count(),
            'total_agents': Agent.objects.filter(is_active=True).count(),
            'completed_tasks': Task.objects.filter(state='completed').count(),
            'total_volume': (
                Transaction.objects
                .filter(status='completed')
                .aggregate(total=Sum('amount_sats'))['total']
                or 0
            ),
        }
        return render(request, self.template_name, context)
