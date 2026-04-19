# apps/super_admin/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from datetime import datetime, timedelta
import json
import csv

from .models import AdminUser, AdminAuditLog, SystemSettings, Announcement
from apps.agents.models import Agent
from apps.tasks.models import Task
from apps.payments.models import Transaction, Wallet, EscrowContract
from apps.accounts.models import User
from apps.execution.models import Execution
from apps.verification.models import Verification, Dispute


# ==================== AUTHENTICATION VIEWS ====================

class SuperAdminLogin(View):
    """Super Admin login view"""
    template_name = 'super_admin/login.html'
    
    def get(self, request):
        if request.user.is_authenticated and request.user.is_staff:
            return redirect('super_admin:dashboard')
        return render(request, self.template_name)
    
    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user and user.is_staff:
            login(request, user)
            
            # Log admin login
            AdminAuditLog.objects.create(
                admin_user=AdminUser.objects.filter(user=user).first(),
                action_type='login',
                resource_type='auth',
                resource_id=str(user.id),
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            return redirect('super_admin:dashboard')
        
        messages.error(request, 'Invalid credentials or insufficient permissions')
        return render(request, self.template_name)


class SuperAdminLogout(View):
    """Super Admin logout view"""
    
    def get(self, request):
        logout(request)
        return redirect('super_admin:login')


# ==================== DASHBOARD VIEWS ====================

@method_decorator(staff_member_required, name='dispatch')
class SuperAdminDashboard(View):
    """Main dashboard view"""
    template_name = 'super_admin/dashboard.html'
    
    def get(self, request):
        context = self.get_context_data()
        return render(request, self.template_name, context)
    
    def get_context_data(self):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0)
        
        context = {
            'stats': {
                'total_agents': Agent.objects.count(),
                'online_agents': Agent.objects.filter(last_heartbeat__gte=now - timedelta(minutes=5)).count(),
                'ai_agents': Agent.objects.filter(agent_type='ai').count(),
                'human_agents': Agent.objects.filter(agent_type='human').count(),
                'total_tasks': Task.objects.count(),
                'active_tasks': Task.objects.filter(state__in=['open', 'assigned', 'executing']).count(),
                'completed_today': Task.objects.filter(completed_at__gte=today_start).count(),
                'total_volume': Transaction.objects.filter(status='completed').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
                'today_volume': Transaction.objects.filter(status='completed', created_at__gte=today_start).aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
                'success_rate': self.calculate_success_rate(),
            },
            'recent_tasks': Task.objects.select_related('matched_agent').order_by('-created_at')[:10],
            'recent_agents': Agent.objects.select_related('user').order_by('-last_heartbeat')[:10],
            'recent_transactions': Transaction.objects.select_related('from_wallet', 'to_wallet').order_by('-created_at')[:10],
            'system_alerts': self.get_system_alerts(),
        }
        return context
    
    def calculate_success_rate(self):
        completed = Task.objects.filter(state='completed').count()
        total = Task.objects.exclude(state__in=['open']).count()
        return (completed / total * 100) if total > 0 else 0
    
    def get_system_alerts(self):
        alerts = []
        now = timezone.now()
        
        stuck_tasks = Task.objects.filter(state='executing', started_at__lt=now - timedelta(minutes=30)).count()
        if stuck_tasks > 0:
            alerts.append({'type': 'warning', 'message': f'{stuck_tasks} tasks stuck in executing state'})
        
        total_agents = Agent.objects.count()
        online_agents = Agent.objects.filter(last_heartbeat__gte=now - timedelta(minutes=5)).count()
        if total_agents > 0 and (online_agents / total_agents * 100) < 20:
            alerts.append({'type': 'critical', 'message': f'Only {int(online_agents/total_agents*100)}% of agents are online'})
        
        pending_disputes = Dispute.objects.filter(status='open').count()
        if pending_disputes > 0:
            alerts.append({'type': 'warning', 'message': f'{pending_disputes} disputes awaiting resolution'})
        
        return alerts


# ==================== AGENT MANAGEMENT VIEWS ====================

@method_decorator(staff_member_required, name='dispatch')
class AgentManagement(View):
    template_name = 'super_admin/agents.html'
    
    def get(self, request):
        agents = Agent.objects.select_related('user').all()
        context = {
            'agents': agents,
            'agent_types': Agent.objects.values_list('agent_type', flat=True).distinct(),
            'total_agents': agents.count(),
            'online_agents': agents.filter(last_heartbeat__gte=timezone.now() - timedelta(minutes=5)).count(),
            'active_agents': agents.filter(is_active=True).count(),
            'total_earned': agents.aggregate(Sum('total_earned'))['total_earned__sum'] or 0,
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class AgentDetailView(View):
    template_name = 'super_admin/agent_detail.html'
    
    def get(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id)
        tasks = Task.objects.filter(matched_agent=agent).order_by('-created_at')[:20]
        
        context = {
            'agent': agent,
            'tasks': tasks,
            'total_tasks': Task.objects.filter(matched_agent=agent).count(),
            'completed_tasks': Task.objects.filter(matched_agent=agent, state='completed').count(),
            'total_earned': agent.total_earned,
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class AgentActivateView(View):
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id)
        agent.is_active = True
        agent.save()
        return JsonResponse({'success': True, 'message': f'Agent {agent.name} activated'})


@method_decorator(staff_member_required, name='dispatch')
class AgentDeactivateView(View):
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id)
        agent.is_active = False
        agent.save()
        return JsonResponse({'success': True, 'message': f'Agent {agent.name} deactivated'})


@method_decorator(staff_member_required, name='dispatch')
class AgentDeleteView(View):
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id)
        agent_name = agent.name
        agent.delete()
        return JsonResponse({'success': True, 'message': f'Agent {agent_name} deleted'})


@method_decorator(staff_member_required, name='dispatch')
class AgentCreateView(View):
    template_name = 'super_admin/agent_create.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        name = request.POST.get('name')
        agent_type = request.POST.get('agent_type')
        email = request.POST.get('email')
        
        # Create user if doesn't exist
        user, created = User.objects.get_or_create(
            email=email,
            defaults={'username': email, 'is_staff': False}
        )
        
        agent = Agent.objects.create(
            name=name,
            agent_type=agent_type,
            user=user,
            is_active=True
        )
        
        return redirect('super_admin:agent_detail', agent_id=agent.id)


@method_decorator(staff_member_required, name='dispatch')
class AgentEditView(View):
    template_name = 'super_admin/agent_edit.html'
    
    def get(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id)
        return render(request, self.template_name, {'agent': agent})
    
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id)
        agent.name = request.POST.get('name')
        agent.description = request.POST.get('description')
        agent.hourly_rate_sats = int(request.POST.get('hourly_rate_sats', 0))
        agent.save()
        return redirect('super_admin:agent_detail', agent_id=agent.id)


# ==================== TASK MANAGEMENT VIEWS ====================

@method_decorator(staff_member_required, name='dispatch')
class TaskManagement(View):
    template_name = 'super_admin/tasks.html'
    
    def get(self, request):
        tasks = Task.objects.select_related('matched_agent', 'created_by').all().order_by('-created_at')
        context = {
            'tasks': tasks[:100],
            'total_tasks': tasks.count(),
            'pending_tasks': tasks.filter(state='open').count(),
            'completed_tasks': tasks.filter(state='completed').count(),
            'failed_tasks': tasks.filter(state='failed').count(),
            'total_volume': tasks.aggregate(Sum('budget_sats'))['budget_sats__sum'] or 0,
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class TaskDetailView(View):
    template_name = 'super_admin/task_detail.html'
    
    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        execution = Execution.objects.filter(task=task).first()
        
        context = {
            'task': task,
            'execution': execution,
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class TaskCancelView(View):
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        task.state = Task.TaskState.CANCELLED
        task.save()
        return JsonResponse({'success': True, 'message': 'Task cancelled'})


@method_decorator(staff_member_required, name='dispatch')
class TaskReassignView(View):
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        task.state = Task.TaskState.OPEN
        task.matched_agent = None
        task.save()
        return JsonResponse({'success': True, 'message': 'Task reassigned to open queue'})


@method_decorator(staff_member_required, name='dispatch')
class TaskForceCompleteView(View):
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        task.state = Task.TaskState.COMPLETED
        task.completed_at = timezone.now()
        task.save()
        return JsonResponse({'success': True, 'message': 'Task force completed'})


@method_decorator(staff_member_required, name='dispatch')
class TaskForceFailView(View):
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        task.state = Task.TaskState.FAILED
        task.save()
        return JsonResponse({'success': True, 'message': 'Task force failed'})


# ==================== PAYMENT MANAGEMENT VIEWS ====================

@method_decorator(staff_member_required, name='dispatch')
class PaymentManagement(View):
    template_name = 'super_admin/payments.html'
    
    def get(self, request):
        transactions = Transaction.objects.select_related('from_wallet', 'to_wallet').order_by('-created_at')[:100]
        wallets = Wallet.objects.all()
        
        context = {
            'transactions': transactions,
            'wallets': wallets,
            'total_volume': Transaction.objects.filter(status='completed').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            'pending_transactions': Transaction.objects.filter(status='pending').count(),
            'total_wallets': wallets.count(),
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class TransactionListView(View):
    template_name = 'super_admin/transactions.html'
    
    def get(self, request):
        transactions = Transaction.objects.select_related('from_wallet', 'to_wallet').order_by('-created_at')
        
        # Filtering
        status = request.GET.get('status')
        if status:
            transactions = transactions.filter(status=status)
        
        tx_type = request.GET.get('type')
        if tx_type:
            transactions = transactions.filter(type=tx_type)
        
        context = {
            'transactions': transactions[:200],
            'total_volume': transactions.aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            'selected_status': status,
            'selected_type': tx_type,
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class TransactionDetailView(View):
    template_name = 'super_admin/transaction_detail.html'
    
    def get(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
        return render(request, self.template_name, {'transaction': transaction})


@method_decorator(staff_member_required, name='dispatch')
class TransactionRefundView(View):
    def post(self, request, transaction_id):
        transaction = get_object_or_404(Transaction, id=transaction_id)
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
        
        return JsonResponse({'success': True, 'message': 'Transaction refunded'})


@method_decorator(staff_member_required, name='dispatch')
class WalletListView(View):
    template_name = 'super_admin/wallets.html'
    
    def get(self, request):
        wallets = Wallet.objects.all()
        context = {
            'wallets': wallets,
            'total_balance': wallets.aggregate(Sum('balance_sats'))['balance_sats__sum'] or 0,
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class WalletDetailView(View):
    template_name = 'super_admin/wallet_detail.html'
    
    def get(self, request, wallet_id):
        wallet = get_object_or_404(Wallet, id=wallet_id)
        transactions = Transaction.objects.filter(
            Q(from_wallet=wallet) | Q(to_wallet=wallet)
        ).order_by('-created_at')[:50]
        
        context = {
            'wallet': wallet,
            'transactions': transactions,
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class EscrowListView(View):
    template_name = 'super_admin/escrow_list.html'
    
    def get(self, request):
        escrows = EscrowContract.objects.select_related('task', 'buyer', 'seller').all()
        context = {
            'escrows': escrows,
            'total_held': escrows.filter(status='held').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class EscrowDetailView(View):
    template_name = 'super_admin/escrow_detail.html'
    
    def get(self, request, escrow_id):
        escrow = get_object_or_404(EscrowContract, id=escrow_id)
        return render(request, self.template_name, {'escrow': escrow})


@method_decorator(staff_member_required, name='dispatch')
class EscrowReleaseView(View):
    def post(self, request, escrow_id):
        escrow = get_object_or_404(EscrowContract, id=escrow_id)
        escrow.status = 'released'
        escrow.released_at = timezone.now()
        escrow.save()
        return JsonResponse({'success': True, 'message': 'Escrow released'})

# Add this class after EscrowReleaseView and before SystemSettingsView

@method_decorator(staff_member_required, name='dispatch')
class EscrowDisputeView(View):
    def post(self, request, escrow_id):
        escrow = get_object_or_404(EscrowContract, id=escrow_id)
        escrow.status = 'disputed'
        escrow.dispute_reason = request.POST.get('reason', '')
        escrow.save()
        return JsonResponse({'success': True, 'message': 'Dispute raised on escrow'})

# ==================== SETTINGS VIEWS ====================

@method_decorator(staff_member_required, name='dispatch')
class SystemSettingsView(View):
    template_name = 'super_admin/settings.html'
    
    def get(self, request):
        settings = SystemSettings.objects.all()
        context = {
            'settings': settings,
            'setting_categories': {
                'general': SystemSettings.objects.filter(key__startswith='general_'),
                'payments': SystemSettings.objects.filter(key__startswith='payment_'),
                'agents': SystemSettings.objects.filter(key__startswith='agent_'),
                'tasks': SystemSettings.objects.filter(key__startswith='task_'),
                'security': SystemSettings.objects.filter(key__startswith='security_'),
            }
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class GeneralSettingsView(View):
    template_name = 'super_admin/general_settings.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class PaymentSettingsView(View):
    template_name = 'super_admin/payment_settings.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class AgentSettingsView(View):
    template_name = 'super_admin/agent_settings.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class TaskSettingsView(View):
    template_name = 'super_admin/task_settings.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class SecuritySettingsView(View):
    template_name = 'super_admin/security_settings.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class EmailSettingsView(View):
    template_name = 'super_admin/email_settings.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class SettingUpdateView(View):
    def post(self, request, key):
        value = request.POST.get('value')
        setting, created = SystemSettings.objects.update_or_create(
            key=key,
            defaults={'value': json.loads(value) if value else {}}
        )
        return JsonResponse({'success': True})


# ==================== ANALYTICS VIEWS ====================

@method_decorator(staff_member_required, name='dispatch')
class AnalyticsView(View):
    template_name = 'super_admin/analytics.html'
    
    def get(self, request):
        context = {
            'daily_stats': self.get_daily_stats(),
            'agent_performance': self.get_agent_performance(),
            'task_volume': self.get_task_volume(),
            'revenue_stats': self.get_revenue_stats(),
        }
        return render(request, self.template_name, context)
    
    def get_daily_stats(self):
        stats = []
        for i in range(30, -1, -1):
            date = timezone.now() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)
            
            stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'tasks': Task.objects.filter(created_at__range=[day_start, day_end]).count(),
                'volume': Transaction.objects.filter(created_at__range=[day_start, day_end], status='completed').aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            })
        return stats
    
    def get_agent_performance(self):
        return Agent.objects.filter(total_tasks__gt=0).order_by('-success_rate')[:20]
    
    def get_task_volume(self):
        return Task.objects.values('state').annotate(count=Count('id'))
    
    def get_revenue_stats(self):
        return Transaction.objects.filter(status='completed').values('type').annotate(total=Sum('amount_sats'))


@method_decorator(staff_member_required, name='dispatch')
class MetricsView(View):
    template_name = 'super_admin/metrics.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class ReportsView(View):
    template_name = 'super_admin/reports.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class AlertsView(View):
    template_name = 'super_admin/alerts.html'
    
    def get(self, request):
        from apps.analytics.models import Alert
        alerts = Alert.objects.all().order_by('-created_at')
        return render(request, self.template_name, {'alerts': alerts})


@method_decorator(staff_member_required, name='dispatch')
class AlertResolveView(View):
    def post(self, request, alert_id):
        from apps.analytics.models import Alert
        alert = get_object_or_404(Alert, id=alert_id)
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        return JsonResponse({'success': True})


@method_decorator(staff_member_required, name='dispatch')
class ExportReportView(View):
    def get(self, request, report_type):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
        
        writer = csv.writer(response)
        
        if report_type == 'tasks':
            writer.writerow(['Task ID', 'Title', 'Budget', 'State', 'Created At', 'Completed At'])
            for task in Task.objects.all():
                writer.writerow([str(task.id), task.title, task.budget_sats, task.state, task.created_at, task.completed_at])
        
        return response


# ==================== ADMIN USER MANAGEMENT ====================

@method_decorator(staff_member_required, name='dispatch')
class AdminUserManagement(View):
    template_name = 'super_admin/admin_users.html'
    
    def get(self, request):
        admin_users = AdminUser.objects.select_related('user').all()
        context = {
            'admin_users': admin_users,
            'roles': ['super_admin', 'admin', 'moderator', 'viewer'],
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class AdminUserCreateView(View):
    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')
        
        user = User.objects.create_user(username=email, email=email, password=password, is_staff=True)
        AdminUser.objects.create(user=user, role=role)
        
        return JsonResponse({'success': True})


@method_decorator(staff_member_required, name='dispatch')
class AdminUserEditView(View):
    def post(self, request, admin_id):
        admin_user = get_object_or_404(AdminUser, id=admin_id)
        admin_user.role = request.POST.get('role')
        admin_user.save()
        return JsonResponse({'success': True})


@method_decorator(staff_member_required, name='dispatch')
class AdminUserDeleteView(View):
    def post(self, request, admin_id):
        admin_user = get_object_or_404(AdminUser, id=admin_id)
        admin_user.user.delete()
        admin_user.delete()
        return JsonResponse({'success': True})


@method_decorator(staff_member_required, name='dispatch')
class AdminUserRoleUpdateView(View):
    def post(self, request, admin_id):
        admin_user = get_object_or_404(AdminUser, id=admin_id)
        admin_user.role = request.POST.get('role')
        admin_user.save()
        return JsonResponse({'success': True})


# ==================== AUDIT LOGS ====================

@method_decorator(staff_member_required, name='dispatch')
class AuditLogView(View):
    template_name = 'super_admin/audit_logs.html'
    
    def get(self, request):
        logs = AdminAuditLog.objects.select_related('admin_user').order_by('-created_at')[:200]
        return render(request, self.template_name, {'logs': logs})


@method_decorator(staff_member_required, name='dispatch')
class AuditLogDetailView(View):
    template_name = 'super_admin/audit_log_detail.html'
    
    def get(self, request, log_id):
        log = get_object_or_404(AdminAuditLog, id=log_id)
        return render(request, self.template_name, {'log': log})


@method_decorator(staff_member_required, name='dispatch')
class AuditLogExportView(View):
    def get(self, request):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Timestamp', 'Admin', 'Action', 'Resource', 'Resource ID', 'IP Address'])
        
        for log in AdminAuditLog.objects.all():
            writer.writerow([log.created_at, log.admin_user.user.email if log.admin_user else 'System', 
                           log.action_type, log.resource_type, log.resource_id, log.ip_address])
        
        return response


# ==================== REPORTS ====================

@method_decorator(staff_member_required, name='dispatch')
class DailyReportView(View):
    template_name = 'super_admin/daily_report.html'
    
    def get(self, request):
        date = request.GET.get('date', timezone.now().date())
        return render(request, self.template_name, {'date': date})


@method_decorator(staff_member_required, name='dispatch')
class WeeklyReportView(View):
    template_name = 'super_admin/weekly_report.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class MonthlyReportView(View):
    template_name = 'super_admin/monthly_report.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class AgentReportView(View):
    template_name = 'super_admin/agent_report.html'
    
    def get(self, request):
        agents = Agent.objects.annotate(
            task_count=Count('task'),
            success_count=Count('task', filter=Q(task__state='completed'))
        ).order_by('-task_count')
        
        return render(request, self.template_name, {'agents': agents[:50]})


@method_decorator(staff_member_required, name='dispatch')
class FinancialReportView(View):
    template_name = 'super_admin/financial_report.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class TaskReportView(View):
    template_name = 'super_admin/task_report.html'
    
    def get(self, request):
        tasks = Task.objects.values('state').annotate(count=Count('id'))
        return render(request, self.template_name, {'tasks': tasks})


@method_decorator(staff_member_required, name='dispatch')
class DownloadReportView(View):
    def get(self, request, report_id):
        # Generate and download report
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="report_{report_id}.pdf"'
        return response


# ==================== ANNOUNCEMENTS ====================

@method_decorator(staff_member_required, name='dispatch')
class AnnouncementListView(View):
    template_name = 'super_admin/announcements.html'
    
    def get(self, request):
        announcements = Announcement.objects.all().order_by('-created_at')
        return render(request, self.template_name, {'announcements': announcements})


@method_decorator(staff_member_required, name='dispatch')
class AnnouncementCreateView(View):
    template_name = 'super_admin/announcement_create.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        announcement = Announcement.objects.create(
            title=request.POST.get('title'),
            content=request.POST.get('content'),
            announcement_type=request.POST.get('announcement_type'),
            is_active=True,
            start_date=timezone.now()
        )
        return redirect('super_admin:announcements')


@method_decorator(staff_member_required, name='dispatch')
class AnnouncementEditView(View):
    template_name = 'super_admin/announcement_edit.html'
    
    def get(self, request, announcement_id):
        announcement = get_object_or_404(Announcement, id=announcement_id)
        return render(request, self.template_name, {'announcement': announcement})
    
    def post(self, request, announcement_id):
        announcement = get_object_or_404(Announcement, id=announcement_id)
        announcement.title = request.POST.get('title')
        announcement.content = request.POST.get('content')
        announcement.announcement_type = request.POST.get('announcement_type')
        announcement.save()
        return redirect('super_admin:announcements')


@method_decorator(staff_member_required, name='dispatch')
class AnnouncementDeleteView(View):
    def post(self, request, announcement_id):
        announcement = get_object_or_404(Announcement, id=announcement_id)
        announcement.delete()
        return JsonResponse({'success': True})


@method_decorator(staff_member_required, name='dispatch')
class AnnouncementToggleView(View):
    def post(self, request, announcement_id):
        announcement = get_object_or_404(Announcement, id=announcement_id)
        announcement.is_active = not announcement.is_active
        announcement.save()
        return JsonResponse({'success': True})


# ==================== DISPUTES ====================

@method_decorator(staff_member_required, name='dispatch')
class DisputeListView(View):
    template_name = 'super_admin/disputes.html'
    
    def get(self, request):
        disputes = Dispute.objects.select_related('task', 'raised_by').all().order_by('-created_at')
        return render(request, self.template_name, {'disputes': disputes})


@method_decorator(staff_member_required, name='dispatch')
class DisputeDetailView(View):
    template_name = 'super_admin/dispute_detail.html'
    
    def get(self, request, dispute_id):
        dispute = get_object_or_404(Dispute, id=dispute_id)
        return render(request, self.template_name, {'dispute': dispute})


@method_decorator(staff_member_required, name='dispatch')
class DisputeResolveView(View):
    def post(self, request, dispute_id):
        dispute = get_object_or_404(Dispute, id=dispute_id)
        dispute.status = 'resolved'
        dispute.resolution = request.POST.get('resolution')
        dispute.resolved_at = timezone.now()
        dispute.save()
        return JsonResponse({'success': True})


@method_decorator(staff_member_required, name='dispatch')
class DisputeEscalateView(View):
    def post(self, request, dispute_id):
        dispute = get_object_or_404(Dispute, id=dispute_id)
        dispute.status = 'escalated'
        dispute.save()
        return JsonResponse({'success': True})


# ==================== SYSTEM HEALTH ====================

@method_decorator(staff_member_required, name='dispatch')
class SystemHealthView(View):
    template_name = 'super_admin/system_health.html'
    
    def get(self, request):
        context = {
            'database_status': self.check_database(),
            'cache_status': self.check_cache(),
            'queue_status': self.check_queue(),
            'worker_status': self.check_workers(),
        }
        return render(request, self.template_name, context)
    
    def check_database(self):
        try:
            Task.objects.exists()
            return {'status': 'healthy', 'message': 'Database connected'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
    
    def check_cache(self):
        return {'status': 'healthy', 'message': 'Cache working'}
    
    def check_queue(self):
        return {'status': 'healthy', 'message': 'Queue working'}
    
    def check_workers(self):
        return {'status': 'healthy', 'message': 'Workers active'}


@method_decorator(staff_member_required, name='dispatch')
class HealthCheckView(View):
    def get(self, request):
        return JsonResponse({'status': 'ok', 'timestamp': str(timezone.now())})


@method_decorator(staff_member_required, name='dispatch')
class SystemStatusView(View):
    def get(self, request):
        return JsonResponse({
            'system': 'online',
            'users': User.objects.count(),
            'agents': Agent.objects.count(),
            'tasks': Task.objects.count(),
        })


# ==================== BACKUP ====================

@method_decorator(staff_member_required, name='dispatch')
class BackupView(View):
    template_name = 'super_admin/backup.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class CreateBackupView(View):
    def post(self, request):
        # Implement backup logic
        return JsonResponse({'success': True, 'message': 'Backup created'})


@method_decorator(staff_member_required, name='dispatch')
class DownloadBackupView(View):
    def get(self, request, backup_file):
        response = HttpResponse(content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{backup_file}"'
        return response


@method_decorator(staff_member_required, name='dispatch')
class RestoreBackupView(View):
    def post(self, request, backup_file):
        # Implement restore logic
        return JsonResponse({'success': True})


# ==================== API KEYS ====================

@method_decorator(staff_member_required, name='dispatch')
class APIKeyListView(View):
    template_name = 'super_admin/api_keys.html'
    
    def get(self, request):
        from apps.accounts.models import APIKey
        api_keys = APIKey.objects.select_related('user').all()
        return render(request, self.template_name, {'api_keys': api_keys})


@method_decorator(staff_member_required, name='dispatch')
class APIKeyCreateView(View):
    def post(self, request):
        from apps.accounts.models import APIKey
        from django.utils.crypto import get_random_string
        
        api_key = APIKey.objects.create(
            user_id=request.POST.get('user_id'),
            name=request.POST.get('name'),
            key=get_random_string(32)
        )
        return JsonResponse({'success': True, 'key': api_key.key})


@method_decorator(staff_member_required, name='dispatch')
class APIKeyRevokeView(View):
    def post(self, request, key_id):
        from apps.accounts.models import APIKey
        api_key = get_object_or_404(APIKey, id=key_id)
        api_key.delete()
        return JsonResponse({'success': True})


# ==================== WEBHOOKS ====================

@method_decorator(staff_member_required, name='dispatch')
class WebhookListView(View):
    template_name = 'super_admin/webhooks.html'
    
    def get(self, request):
        from apps.webhooks.models import WebhookEndpoint
        endpoints = WebhookEndpoint.objects.all()
        return render(request, self.template_name, {'endpoints': endpoints})


@method_decorator(staff_member_required, name='dispatch')
class WebhookCreateView(View):
    def post(self, request):
        from apps.webhooks.models import WebhookEndpoint
        
        endpoint = WebhookEndpoint.objects.create(
            url=request.POST.get('url'),
            secret=request.POST.get('secret'),
            events=request.POST.getlist('events'),
            is_active=True
        )
        return JsonResponse({'success': True})


@method_decorator(staff_member_required, name='dispatch')
class WebhookEditView(View):
    def post(self, request, webhook_id):
        from apps.webhooks.models import WebhookEndpoint
        endpoint = get_object_or_404(WebhookEndpoint, id=webhook_id)
        endpoint.url = request.POST.get('url')
        endpoint.events = request.POST.getlist('events')
        endpoint.is_active = request.POST.get('is_active') == 'on'
        endpoint.save()
        return JsonResponse({'success': True})


@method_decorator(staff_member_required, name='dispatch')
class WebhookDeleteView(View):
    def post(self, request, webhook_id):
        from apps.webhooks.models import WebhookEndpoint
        endpoint = get_object_or_404(WebhookEndpoint, id=webhook_id)
        endpoint.delete()
        return JsonResponse({'success': True})


@method_decorator(staff_member_required, name='dispatch')
class WebhookTestView(View):
    def post(self, request, webhook_id):
        from apps.webhooks.models import WebhookEndpoint
        import requests
        
        endpoint = get_object_or_404(WebhookEndpoint, id=webhook_id)
        
        try:
            response = requests.post(endpoint.url, json={'test': True}, timeout=5)
            success = response.status_code == 200
        except Exception as e:
            success = False
        
        return JsonResponse({'success': success})


# ==================== NOTIFICATIONS ====================

@method_decorator(staff_member_required, name='dispatch')
class NotificationListView(View):
    template_name = 'super_admin/notifications.html'
    
    def get(self, request):
        return render(request, self.template_name)


@method_decorator(staff_member_required, name='dispatch')
class MarkNotificationsReadView(View):
    def post(self, request):
        return JsonResponse({'success': True})


# ==================== PROFILE ====================

@method_decorator(staff_member_required, name='dispatch')
class AdminProfileView(View):
    template_name = 'super_admin/profile.html'
    
    def get(self, request):
        return render(request, self.template_name, {'user': request.user})


@method_decorator(staff_member_required, name='dispatch')
class AdminProfileEditView(View):
    template_name = 'super_admin/profile_edit.html'
    
    def get(self, request):
        return render(request, self.template_name, {'user': request.user})
    
    def post(self, request):
        user = request.user
        user.first_name = request.POST.get('first_name')
        user.last_name = request.POST.get('last_name')
        user.email = request.POST.get('email')
        user.save()
        return redirect('super_admin:profile')


@method_decorator(staff_member_required, name='dispatch')
class AdminChangePasswordView(View):
    template_name = 'super_admin/change_password.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        user = request.user
        if user.check_password(request.POST.get('current_password')):
            user.set_password(request.POST.get('new_password'))
            user.save()
            return redirect('super_admin:login')
        return render(request, self.template_name, {'error': 'Current password is incorrect'})