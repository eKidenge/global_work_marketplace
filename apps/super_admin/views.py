# apps/super_admin/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import timedelta
import json

@method_decorator(staff_member_required, name='dispatch')
class SuperAdminDashboard(View):
    """Main dashboard - entry point for all admin functionality"""
    
    def get(self, request):
        context = self.get_dashboard_context()
        return render(request, 'super_admin/dashboard.html', context)
    
    def get_dashboard_context(self):
        # Get real-time stats
        from apps.agents.models import Agent
        from apps.tasks.models import Task
        from apps.execution.models import Execution
        from apps.payments.models import Transaction
        
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        return {
            'stats': {
                'total_agents': Agent.objects.count(),
                'online_agents': Agent.objects.filter(last_heartbeat__gte=now - timedelta(minutes=5)).count(),
                'ai_agents': Agent.objects.filter(agent_type='ai').count(),
                'human_agents': Agent.objects.filter(agent_type='human').count(),
                
                'total_tasks': Task.objects.count(),
                'active_tasks': Task.objects.filter(state__in=['open', 'assigned', 'executing']).count(),
                'completed_today': Task.objects.filter(completed_at__gte=today_start).count(),
                'avg_completion_time': Execution.objects.filter(
                    completed_at__isnull=False
                ).aggregate(Avg('duration_ms'))['duration_ms__avg'] or 0,
                
                'total_volume': Transaction.objects.filter(
                    status='completed'
                ).aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
                'today_volume': Transaction.objects.filter(
                    status='completed',
                    created_at__gte=today_start
                ).aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
                
                'success_rate': Task.objects.filter(state='completed').count() / max(
                    Task.objects.exclude(state__in=['open']).count(), 1
                ) * 100,
            },
            'recent_tasks': Task.objects.order_by('-created_at')[:10],
            'recent_agents': Agent.objects.order_by('-last_heartbeat')[:10],
            'system_alerts': self.get_system_alerts(),
        }
    
    def get_system_alerts(self):
        alerts = []
        
        # Check for stuck tasks
        stuck_tasks = Task.objects.filter(
            state='executing',
            started_at__lt=timezone.now() - timedelta(minutes=30)
        ).count()
        if stuck_tasks > 0:
            alerts.append({
                'type': 'warning',
                'message': f'{stuck_tasks} tasks have been executing for over 30 minutes'
            })
        
        # Check for low agent availability
        from apps.agents.models import Agent
        online_percentage = Agent.objects.filter(
            last_heartbeat__gte=timezone.now() - timedelta(minutes=5)
        ).count() / max(Agent.objects.count(), 1) * 100
        
        if online_percentage < 20:
            alerts.append({
                'type': 'critical',
                'message': f'Only {online_percentage:.0f}% of agents are online'
            })
        
        return alerts


@method_decorator(staff_member_required, name='dispatch')
class AgentManagement(View):
    """Complete agent management interface"""
    
    def get(self, request):
        from apps.agents.models import Agent
        
        agents = Agent.objects.all().select_related('user')
        context = {
            'agents': agents,
            'agent_types': Agent.objects.values_list('agent_type', flat=True).distinct(),
            'total_agents': agents.count(),
            'online_agents': agents.filter(last_heartbeat__gte=timezone.now() - timedelta(minutes=5)).count(),
        }
        return render(request, 'super_admin/agents.html', context)
    
    def post(self, request):
        """Handle agent actions (activate, deactivate, delete)"""
        action = request.POST.get('action')
        agent_id = request.POST.get('agent_id')
        
        from apps.agents.models import Agent
        agent = get_object_or_404(Agent, id=agent_id)
        
        if action == 'activate':
            agent.is_active = True
            agent.save()
        elif action == 'deactivate':
            agent.is_active = False
            agent.save()
        elif action == 'delete':
            agent.delete()
        
        return JsonResponse({'success': True, 'message': f'Agent {action}d successfully'})


@method_decorator(staff_member_required, name='dispatch')
class TaskManagement(View):
    """Complete task management interface"""
    
    def get(self, request):
        from apps.tasks.models import Task
        
        tasks = Task.objects.all().select_related('matched_agent')
        context = {
            'tasks': tasks,
            'task_states': Task.TaskState.choices,
            'total_tasks': tasks.count(),
            'pending_tasks': tasks.filter(state='open').count(),
            'total_volume': tasks.aggregate(Sum('budget_sats'))['budget_sats__sum'] or 0,
        }
        return render(request, 'super_admin/tasks.html', context)
    
    def post(self, request):
        """Handle task actions (cancel, reassign, force complete)"""
        action = request.POST.get('action')
        task_id = request.POST.get('task_id')
        
        from apps.tasks.models import Task
        task = get_object_or_404(Task, id=task_id)
        
        if action == 'cancel':
            task.state = Task.TaskState.FAILED
            task.save()
        elif action == 'reassign':
            task.state = Task.TaskState.OPEN
            task.matched_agent = None
            task.save()
        elif action == 'force_complete':
            task.state = Task.TaskState.COMPLETED
            task.completed_at = timezone.now()
            task.save()
        
        return JsonResponse({'success': True, 'message': f'Task {action}d successfully'})


@method_decorator(staff_member_required, name='dispatch')
class PaymentManagement(View):
    """Complete payment and transaction management"""
    
    def get(self, request):
        from apps.payments.models import Transaction, Wallet
        
        transactions = Transaction.objects.all().select_related('from_wallet', 'to_wallet')
        wallets = Wallet.objects.all()
        
        context = {
            'transactions': transactions,
            'wallets': wallets,
            'total_volume': transactions.filter(status='completed').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            'pending_transactions': transactions.filter(status='pending').count(),
            'total_wallets': wallets.count(),
        }
        return render(request, 'super_admin/payments.html', context)
    
    def post(self, request):
        """Handle payment actions (refund, manual adjustment)"""
        action = request.POST.get('action')
        transaction_id = request.POST.get('transaction_id')
        
        from apps.payments.models import Transaction
        transaction = get_object_or_404(Transaction, id=transaction_id)
        
        if action == 'refund':
            transaction.status = 'refunded'
            transaction.save()
            # Create reverse transaction
            Transaction.objects.create(
                from_wallet=transaction.to_wallet,
                to_wallet=transaction.from_wallet,
                amount_sats=transaction.amount_sats,
                type='refund',
                status='completed'
            )
        
        return JsonResponse({'success': True, 'message': f'Payment {action}ed successfully'})


@method_decorator(staff_member_required, name='dispatch')
class SystemSettingsView(View):
    """Manage all system settings"""
    
    def get(self, request):
        from .models import SystemSettings
        
        settings = SystemSettings.objects.all()
        context = {
            'settings': settings,
            'setting_categories': self.get_setting_categories(),
        }
        return render(request, 'super_admin/settings.html', context)
    
    def post(self, request):
        from .models import SystemSettings
        
        setting_key = request.POST.get('key')
        setting_value = request.POST.get('value')
        
        setting, created = SystemSettings.objects.update_or_create(
            key=setting_key,
            defaults={'value': json.loads(setting_value)}
        )
        
        return JsonResponse({'success': True, 'message': 'Setting updated'})
    
    def get_setting_categories(self):
        return {
            'general': ['site_name', 'site_description', 'contact_email'],
            'payments': ['min_deposit_sats', 'platform_fee_percent', 'escrow_timeout_hours'],
            'agents': ['min_trust_score', 'max_concurrent_tasks', 'heartbeat_timeout_seconds'],
            'tasks': ['default_task_timeout', 'max_task_budget', 'min_task_budget'],
            'security': ['require_email_verification', 'max_login_attempts', 'session_timeout_minutes'],
        }


@method_decorator(staff_member_required, name='dispatch')
class AnalyticsView(View):
    """Advanced analytics and reporting"""
    
    def get(self, request):
        from apps.analytics.models import Metric
        
        context = {
            'metrics': self.get_all_metrics(),
            'charts_data': self.get_charts_data(),
            'reports': self.get_available_reports(),
        }
        return render(request, 'super_admin/analytics.html', context)
    
    def get_all_metrics(self):
        from apps.analytics.models import Metric
        return Metric.objects.order_by('-created_at')[:100]
    
    def get_charts_data(self):
        """Get data for all charts"""
        from apps.tasks.models import Task
        from datetime import timedelta
        
        # Last 30 days task data
        today = timezone.now()
        chart_data = []
        
        for i in range(30):
            day = today - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0)
            day_end = day.replace(hour=23, minute=59, second=59)
            
            tasks_created = Task.objects.filter(created_at__range=[day_start, day_end]).count()
            tasks_completed = Task.objects.filter(completed_at__range=[day_start, day_end]).count()
            
            chart_data.append({
                'date': day.strftime('%Y-%m-%d'),
                'created': tasks_created,
                'completed': tasks_completed,
            })
        
        return chart_data
    
    def get_available_reports(self):
        return [
            {'name': 'Daily Performance Report', 'url': '/super_admin/reports/daily'},
            {'name': 'Agent Performance Report', 'url': '/super_admin/reports/agents'},
            {'name': 'Financial Summary', 'url': '/super_admin/reports/financial'},
            {'name': 'Task Analytics', 'url': '/super_admin/reports/tasks'},
        ]


@method_decorator(staff_member_required, name='dispatch')
class AdminUserManagement(View):
    """Manage admin users and permissions"""
    
    def get(self, request):
        from .models import AdminUser
        
        admin_users = AdminUser.objects.all().select_related('user')
        context = {
            'admin_users': admin_users,
            'roles': ['super_admin', 'admin', 'moderator', 'viewer'],
        }
        return render(request, 'super_admin/admin_users.html', context)
    
    def post(self, request):
        from django.contrib.auth import get_user_model
        from .models import AdminUser
        
        User = get_user_model()
        
        action = request.POST.get('action')
        
        if action == 'create':
            email = request.POST.get('email')
            password = request.POST.get('password')
            role = request.POST.get('role')
            
            user = User.objects.create_user(email=email, password=password, username=email)
            AdminUser.objects.create(user=user, role=role)
            
        elif action == 'update_role':
            admin_id = request.POST.get('admin_id')
            new_role = request.POST.get('role')
            admin_user = get_object_or_404(AdminUser, id=admin_id)
            admin_user.role = new_role
            admin_user.save()
        
        elif action == 'remove':
            admin_id = request.POST.get('admin_id')
            admin_user = get_object_or_404(AdminUser, id=admin_id)
            admin_user.user.delete()
            admin_user.delete()
        
        return JsonResponse({'success': True, 'message': f'Admin user {action}d successfully'})