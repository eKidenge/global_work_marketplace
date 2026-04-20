# apps/analytics/views.py
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import json
import csv
from .models import Metric, Alert, Report
from apps.tasks.models import Task
from apps.agents.models import Agent
from apps.payments.models import Transaction


class AnalyticsDashboardView(LoginRequiredMixin, View):
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


class OverviewView(LoginRequiredMixin, View):
    template_name = 'analytics/overview.html'
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        context = {
            'days': days,
            'total_tasks': Task.objects.filter(created_at__gte=start_date).count(),
            'completed_tasks': Task.objects.filter(created_at__gte=start_date, state='completed').count(),
            'failed_tasks': Task.objects.filter(created_at__gte=start_date, state='failed').count(),
            'total_agents': Agent.objects.filter(created_at__gte=start_date).count(),
            'active_agents': Agent.objects.filter(is_active=True, last_heartbeat__gte=timezone.now() - timedelta(minutes=5)).count(),
            'total_volume': Transaction.objects.filter(created_at__gte=start_date, status='completed').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            'success_rate': self.calculate_success_rate(start_date),
            'daily_stats': self.get_daily_stats(start_date, days),
        }
        return render(request, self.template_name, context)
    
    def calculate_success_rate(self, start_date):
        completed = Task.objects.filter(created_at__gte=start_date, state='completed').count()
        failed = Task.objects.filter(created_at__gte=start_date, state='failed').count()
        total = completed + failed
        return (completed / total * 100) if total > 0 else 0
    
    def get_daily_stats(self, start_date, days):
        stats = []
        for i in range(days, -1, -1):
            date = timezone.now() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)
            stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'tasks': Task.objects.filter(created_at__range=[day_start, day_end]).count(),
                'volume': Transaction.objects.filter(created_at__range=[day_start, day_end], status='completed').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            })
        return stats


class MetricsView(LoginRequiredMixin, View):
    template_name = 'analytics/metrics.html'
    
    def get(self, request):
        metrics = Metric.objects.all().order_by('-created_at')
        
        category = request.GET.get('category')
        if category:
            metrics = metrics.filter(category=category)
        
        context = {
            'metrics': metrics[:100],
            'categories': dict(Metric.METRIC_CATEGORIES) if hasattr(Metric, 'METRIC_CATEGORIES') else [],
            'selected_category': category,
            'total_count': metrics.count(),
        }
        return render(request, self.template_name, context)


class MetricDetailView(LoginRequiredMixin, View):
    template_name = 'analytics/metric_detail.html'
    
    def get(self, request, metric_name):
        metrics = Metric.objects.filter(name=metric_name).order_by('-created_at')[:50]
        
        context = {
            'metric_name': metric_name,
            'metrics': metrics,
            'average_value': metrics.aggregate(Avg('value'))['value__avg'] if metrics else 0,
            'max_value': metrics.aggregate(Sum('value'))['value__sum'] if metrics else 0,
        }
        return render(request, self.template_name, context)


class ExportMetricsView(LoginRequiredMixin, View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="metrics_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Metric Name', 'Value', 'Unit', 'Category', 'Timestamp'])
        
        metrics = Metric.objects.all().order_by('-created_at')[:1000]
        for metric in metrics:
            writer.writerow([
                metric.name,
                metric.value,
                metric.unit,
                metric.category,
                metric.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response


class TasksChartDataView(LoginRequiredMixin, View):
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


class RevenueChartDataView(LoginRequiredMixin, View):
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


class AgentsChartDataView(LoginRequiredMixin, View):
    """API endpoint for agents chart data"""
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        
        labels = []
        total_agents = []
        active_agents = []
        
        for i in range(days, -1, -1):
            date = timezone.now() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)
            
            labels.append(date.strftime('%Y-%m-%d'))
            total_agents.append(Agent.objects.filter(created_at__lte=day_end).count())
            active_agents.append(Agent.objects.filter(
                is_active=True,
                last_heartbeat__gte=day_end
            ).count())
        
        return JsonResponse({
            'labels': labels,
            'total': total_agents,
            'active': active_agents,
        })


class PerformanceChartDataView(LoginRequiredMixin, View):
    """API endpoint for performance chart data"""
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        
        labels = []
        success_rates = []
        avg_completion_times = []
        
        for i in range(days, -1, -1):
            date = timezone.now() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)
            
            labels.append(date.strftime('%Y-%m-%d'))
            
            completed = Task.objects.filter(completed_at__range=[day_start, day_end], state='completed').count()
            failed = Task.objects.filter(completed_at__range=[day_start, day_end], state='failed').count()
            total = completed + failed
            success_rate = (completed / total * 100) if total > 0 else 0
            success_rates.append(success_rate)
            
            avg_time = Task.objects.filter(completed_at__range=[day_start, day_end]).aggregate(
                avg_time=Avg('completed_at__date__day')
            )['avg_time'] or 0
            avg_completion_times.append(avg_time)
        
        return JsonResponse({
            'labels': labels,
            'success_rates': success_rates,
            'avg_completion_times': avg_completion_times,
        })


class ReportListView(LoginRequiredMixin, View):
    template_name = 'analytics/reports.html'
    
    def get(self, request):
        reports = Report.objects.all().order_by('-created_at')
        
        context = {
            'reports': reports[:50],
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


class CreateReportView(LoginRequiredMixin, View):
    template_name = 'analytics/create_report.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        report_type = request.POST.get('report_type')
        date_range = request.POST.get('date_range')
        
        report = Report.objects.create(
            name=f"{report_type.title()} Report - {timezone.now().strftime('%Y-%m-%d')}",
            report_type=report_type,
            date_range=date_range,
            created_by=request.user,
            status='pending'
        )
        
        messages.success(request, f'Report "{report.name}" is being generated.')
        return redirect('analytics:report_detail', report_id=report.id)


class ReportDetailView(LoginRequiredMixin, View):
    template_name = 'analytics/report_detail.html'
    
    def get(self, request, report_id):
        report = get_object_or_404(Report, id=report_id)
        
        context = {
            'report': report,
            'data': report.data if report.data else {},
        }
        return render(request, self.template_name, context)


class DownloadReportView(LoginRequiredMixin, View):
    def get(self, request, report_id):
        report = get_object_or_404(Report, id=report_id)
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{report.name}.pdf"'
        
        # For now, return CSV instead of PDF
        writer = csv.writer(response)
        writer.writerow(['Report Name', report.name])
        writer.writerow(['Report Type', report.report_type])
        writer.writerow(['Generated At', report.created_at.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])
        
        if report.data:
            for key, value in report.data.items():
                writer.writerow([key, value])
        
        return response


class ScheduleReportView(LoginRequiredMixin, View):
    template_name = 'analytics/schedule_report.html'
    
    def get(self, request, report_id):
        report = get_object_or_404(Report, id=report_id)
        
        context = {
            'report': report,
            'frequencies': ['daily', 'weekly', 'monthly'],
        }
        return render(request, self.template_name, context)
    
    def post(self, request, report_id):
        report = get_object_or_404(Report, id=report_id)
        report.schedule_frequency = request.POST.get('frequency')
        report.schedule_email = request.POST.get('email')
        report.is_scheduled = True
        report.save()
        
        messages.success(request, f'Report scheduled {report.schedule_frequency}.')
        return redirect('analytics:report_detail', report_id=report.id)


class AlertListView(LoginRequiredMixin, View):
    template_name = 'analytics/alerts.html'
    
    def get(self, request):
        alerts = Alert.objects.all().order_by('-created_at')
        
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


class AlertDetailView(LoginRequiredMixin, View):
    template_name = 'analytics/alert_detail.html'
    
    def get(self, request, alert_id):
        alert = get_object_or_404(Alert, id=alert_id)
        
        context = {
            'alert': alert,
            'related_metrics': Metric.objects.filter(created_at__range=[
                alert.created_at - timedelta(hours=1),
                alert.created_at + timedelta(hours=1)
            ])[:20],
        }
        return render(request, self.template_name, context)


class ResolveAlertView(LoginRequiredMixin, View):
    def post(self, request, alert_id):
        alert = get_object_or_404(Alert, id=alert_id)
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.resolution_note = request.POST.get('note', '')
        alert.save()
        
        messages.success(request, f'Alert "{alert.title}" resolved.')
        return redirect('analytics:alerts')


class AlertSettingsView(LoginRequiredMixin, View):
    template_name = 'analytics/alert_settings.html'
    
    def get(self, request):
        context = {
            'alert_thresholds': {
                'task_failure_rate': 10,
                'agent_downtime': 5,
                'payment_failure_rate': 5,
            }
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        messages.success(request, 'Alert settings updated.')
        return redirect('analytics:alert_settings')


class RealtimeStatsView(LoginRequiredMixin, View):
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
            'timestamp': timezone.now().isoformat(),
        })


class AgentStatsView(LoginRequiredMixin, View):
    """API endpoint for agent statistics"""
    
    def get(self, request):
        return JsonResponse({
            'total_agents': Agent.objects.count(),
            'ai_agents': Agent.objects.filter(agent_type='ai').count(),
            'human_agents': Agent.objects.filter(agent_type='human').count(),
            'active_agents': Agent.objects.filter(is_active=True).count(),
            'online_agents': Agent.objects.filter(
                last_heartbeat__gte=timezone.now() - timedelta(minutes=5)
            ).count(),
            'avg_trust_score': Agent.objects.aggregate(Avg('trust_score'))['trust_score__avg'] or 0,
            'total_earned': Agent.objects.aggregate(Sum('total_earned'))['total_earned__sum'] or 0,
        })


class TaskStatsView(LoginRequiredMixin, View):
    """API endpoint for task statistics"""
    
    def get(self, request):
        return JsonResponse({
            'total_tasks': Task.objects.count(),
            'open_tasks': Task.objects.filter(state='open').count(),
            'assigned_tasks': Task.objects.filter(state='assigned').count(),
            'executing_tasks': Task.objects.filter(state='executing').count(),
            'completed_tasks': Task.objects.filter(state='completed').count(),
            'failed_tasks': Task.objects.filter(state='failed').count(),
            'avg_completion_time': Task.objects.filter(completed_at__isnull=False).aggregate(
                avg_time=Avg('completed_at__date__day')
            )['avg_time'] or 0,
            'total_budget': Task.objects.aggregate(Sum('budget_sats'))['budget_sats__sum'] or 0,
        })


class PaymentStatsView(LoginRequiredMixin, View):
    """API endpoint for payment statistics"""
    
    def get(self, request):
        return JsonResponse({
            'total_volume': Transaction.objects.filter(status='completed').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            'total_transactions': Transaction.objects.count(),
            'pending_transactions': Transaction.objects.filter(status='pending').count(),
            'completed_transactions': Transaction.objects.filter(status='completed').count(),
            'failed_transactions': Transaction.objects.filter(status='failed').count(),
            'avg_transaction_amount': Transaction.objects.filter(status='completed').aggregate(
                Avg('amount_sats')
            )['amount_sats__avg'] or 0,
            'total_fees': Transaction.objects.filter(type='fee').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
        })