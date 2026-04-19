# apps/analytics/views.py
from django.shortcuts import render
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
from .models import Metric, Alert
from apps.tasks.models import Task
from apps.agents.models import Agent
from apps.payments.models import Transaction

class AnalyticsDashboardView(View):
    template_name = 'analytics/dashboard.html'
    
    def get(self, request):
        context = {
            'overview': self.get_overview_stats(),
            'daily_stats': self.get_daily_stats(),
            'top_metrics': self.get_top_metrics(),
            'recent_alerts': Alert.objects.filter(is_resolved=False)[:10],
        }
        return render(request, self.template_name, context)
    
    def get_overview_stats(self):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0)
        
        return {
            'total_tasks': Task.objects.count(),
            'tasks_today': Task.objects.filter(created_at__gte=today_start).count(),
            'total_agents': Agent.objects.count(),
            'active_agents': Agent.objects.filter(is_active=True).count(),
            'total_volume': Transaction.objects.filter(status='completed').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            'volume_today': Transaction.objects.filter(
                status='completed',
                created_at__gte=today_start
            ).aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            'success_rate': self.calculate_success_rate(),
        }
    
    def calculate_success_rate(self):
        completed = Task.objects.filter(state='completed').count()
        total = Task.objects.exclude(state__in=['open']).count()
        return (completed / total * 100) if total > 0 else 0
    
    def get_daily_stats(self):
        stats = []
        for i in range(7, -1, -1):
            date = timezone.now() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)
            
            stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'tasks': Task.objects.filter(created_at__range=[day_start, day_end]).count(),
                'volume': Transaction.objects.filter(
                    created_at__range=[day_start, day_end],
                    status='completed'
                ).aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            })
        return stats
    
    def get_top_metrics(self):
        return Metric.objects.order_by('-created_at')[:20]

class MetricsView(View):
    template_name = 'analytics/metrics.html'
    
    def get(self, request):
        metrics = Metric.objects.all().order_by('-created_at')
        
        # Filter by category
        category = request.GET.get('category')
        if category:
            metrics = metrics.filter(category=category)
        
        context = {
            'metrics': metrics[:100],
            'categories': Metric.METRIC_CATEGORIES,
            'selected_category': category,
        }
        return render(request, self.template_name, context)

class ReportsView(View):
    template_name = 'analytics/reports.html'
    
    def get(self, request):
        context = {
            'available_reports': [
                {'name': 'Daily Performance', 'url': '/analytics/reports/daily/', 'icon': '📊'},
                {'name': 'Agent Performance', 'url': '/analytics/reports/agents/', 'icon': '🤖'},
                {'name': 'Financial Summary', 'url': '/analytics/reports/financial/', 'icon': '💰'},
                {'name': 'Task Analytics', 'url': '/analytics/reports/tasks/', 'icon': '📋'},
                {'name': 'User Growth', 'url': '/analytics/reports/users/', 'icon': '👥'},
                {'name': 'Revenue Report', 'url': '/analytics/reports/revenue/', 'icon': '💵'},
            ]
        }
        return render(request, self.template_name, context)

class AlertsView(View):
    template_name = 'analytics/alerts.html'
    
    def get(self, request):
        alerts = Alert.objects.all().order_by('-created_at')
        
        # Filter by level
        level = request.GET.get('level')
        if level:
            alerts = alerts.filter(level=level)
        
        context = {
            'alerts': alerts[:50],
            'levels': ['info', 'warning', 'critical'],
            'selected_level': level,
            'unresolved_count': alerts.filter(is_resolved=False).count(),
        }
        return render(request, self.template_name, context)

class TasksChartDataView(View):
    """API endpoint for task chart data"""
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        
        labels = []
        created_counts = []
        completed_counts = []
        
        for i in range(days, -1, -1):
            date = timezone.now() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)
            
            labels.append(date.strftime('%Y-%m-%d'))
            created_counts.append(Task.objects.filter(created_at__range=[day_start, day_end]).count())
            completed_counts.append(Task.objects.filter(completed_at__range=[day_start, day_end]).count())
        
        return JsonResponse({
            'labels': labels,
            'created': created_counts,
            'completed': completed_counts,
        })

class RevenueChartDataView(View):
    """API endpoint for revenue chart data"""
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        
        labels = []
        revenue = []
        
        for i in range(days, -1, -1):
            date = timezone.now() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)
            
            labels.append(date.strftime('%Y-%m-%d'))
            revenue.append(Transaction.objects.filter(
                created_at__range=[day_start, day_end],
                status='completed',
                type='payment'
            ).aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0)
        
        return JsonResponse({
            'labels': labels,
            'revenue': revenue,
        })

class RealtimeStatsView(View):
    """API endpoint for real-time stats"""
    
    def get(self, request):
        return JsonResponse({
            'active_tasks': Task.objects.filter(state__in=['open', 'assigned', 'executing']).count(),
            'online_agents': Agent.objects.filter(
                last_heartbeat__gte=timezone.now() - timedelta(minutes=5),
                is_active=True
            ).count(),
            'pending_verifications': Task.objects.filter(state='verifying').count(),
            'pending_payments': Transaction.objects.filter(status='pending').count(),
        })