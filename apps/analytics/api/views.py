# apps/analytics/api/views.py
from django.views import View
from django.http import JsonResponse
from django.utils import timezone

class APIMetricsView(View):
    def get(self, request):
        return JsonResponse({
            'total_tasks': 1250,
            'completed_tasks': 1180,
            'success_rate': 94.4,
            'total_payments_sats': 125000,
            'active_agents': 45,
            'avg_response_time_ms': 2500
        })

class APIDashboardView(View):
    def get(self, request):
        return JsonResponse({
            'daily_stats': [],
            'weekly_stats': [],
            'monthly_stats': [],
            'top_agents': []
        })

class APIReportsView(View):
    def get(self, request):
        return JsonResponse({
            'reports': [],
            'available_report_types': ['daily', 'weekly', 'monthly']
        })