# apps/agents/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Count, Sum
from django.utils import timezone
from datetime import timedelta
from .models import Agent, Capability, AgentHeartbeat
from .forms import AgentRegisterForm, AgentSettingsForm, AgentCapabilityForm

class AgentListView(View):
    template_name = 'agents/list.html'
    
    def get(self, request):
        agents = Agent.objects.filter(is_active=True)
        
        # Filtering
        agent_type = request.GET.get('type')
        if agent_type:
            agents = agents.filter(agent_type=agent_type)
        
        capability = request.GET.get('capability')
        if capability:
            agents = agents.filter(capabilities__contains=[capability])
        
        # Search
        search = request.GET.get('search')
        if search:
            agents = agents.filter(Q(name__icontains=search) | Q(description__icontains=search))
        
        # Pagination
        paginator = Paginator(agents, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'agents': page_obj,
            'agent_types': Agent.objects.values_list('agent_type', flat=True).distinct(),
            'capabilities': Capability.objects.all(),
            'total_agents': agents.count(),
            'online_agents': agents.filter(last_heartbeat__gte=timezone.now() - timedelta(minutes=5)).count(),
            'search': search,
            'selected_type': agent_type,
        }
        return render(request, self.template_name, context)

class AgentDetailView(View):
    template_name = 'agents/detail.html'
    
    def get(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id, is_active=True)
        
        # Get agent stats
        from apps.tasks.models import Task
        from apps.verification.models import Reputation
        
        context = {
            'agent': agent,
            'reputation': Reputation.objects.filter(agent=agent).first(),
            'recent_tasks': Task.objects.filter(matched_agent=agent, state='completed').order_by('-completed_at')[:10],
            'similar_agents': Agent.objects.filter(
                capabilities__overlap=agent.capabilities,
                is_active=True
            ).exclude(id=agent.id)[:5],
            'total_tasks': Task.objects.filter(matched_agent=agent).count(),
            'success_rate': self.calculate_success_rate(agent),
            'avg_response_time': AgentHeartbeat.objects.filter(agent=agent).aggregate(Avg('latency_ms'))['latency_ms__avg'] or 0,
        }
        return render(request, self.template_name, context)
    
    def calculate_success_rate(self, agent):
        from apps.tasks.models import Task
        completed = Task.objects.filter(matched_agent=agent, state='completed').count()
        total = Task.objects.filter(matched_agent=agent).exclude(state='open').count()
        return (completed / total * 100) if total > 0 else 0

class AgentRegisterView(LoginRequiredMixin, View):
    template_name = 'agents/register.html'
    
    def get(self, request):
        return render(request, self.template_name, {
            'form': AgentRegisterForm(),
            'capabilities': Capability.objects.all()
        })
    
    def post(self, request):
        form = AgentRegisterForm(request.POST)
        if form.is_valid():
            agent = form.save(commit=False)
            agent.user = request.user
            agent.save()
            agent.capabilities = request.POST.getlist('capabilities')
            agent.save()
            messages.success(request, f'Agent {agent.name} registered successfully!')
            return redirect('agents:agent_detail', agent_id=agent.id)
        return render(request, self.template_name, {'form': form})

class AIRegisterView(LoginRequiredMixin, View):
    template_name = 'agents/ai_register.html'
    
    def get(self, request):
        return render(request, self.template_name, {
            'form': AgentRegisterForm(),
            'ai_models': ['GPT-4', 'Claude', 'Gemini', 'Llama', 'Custom']
        })
    
    def post(self, request):
        form = AgentRegisterForm(request.POST)
        if form.is_valid():
            agent = form.save(commit=False)
            agent.user = request.user
            agent.agent_type = 'ai'
            agent.api_endpoint = request.POST.get('api_endpoint')
            agent.save()
            agent.capabilities = request.POST.getlist('capabilities')
            agent.save()
            messages.success(request, f'AI Agent {agent.name} created!')
            return redirect('agents:agent_detail', agent_id=agent.id)
        return render(request, self.template_name, {'form': form})

class AgentDashboardView(LoginRequiredMixin, View):
    template_name = 'agents/dashboard.html'
    
    def get(self, request):
        from apps.tasks.models import Task
        
        agents = Agent.objects.filter(user=request.user)
        context = {
            'agents': agents,
            'total_agents': agents.count(),
            'total_earned': agents.aggregate(Sum('total_earned'))['total_earned__sum'] or 0,
            'total_tasks': Task.objects.filter(matched_agent__in=agents).count(),
            'recent_tasks': Task.objects.filter(matched_agent__in=agents).order_by('-created_at')[:10],
            'online_agents': agents.filter(last_heartbeat__gte=timezone.now() - timedelta(minutes=5)).count(),
        }
        return render(request, self.template_name, context)

class AgentPerformanceView(LoginRequiredMixin, View):
    template_name = 'agents/performance.html'
    
    def get(self, request, agent_id=None):
        if agent_id:
            agent = get_object_or_404(Agent, id=agent_id, user=request.user)
        else:
            agent = Agent.objects.filter(user=request.user).first()
            if not agent:
                return redirect('agents:register')
        
        from apps.tasks.models import Task
        from apps.execution.models import Execution
        
        # Performance metrics
        tasks = Task.objects.filter(matched_agent=agent)
        executions = Execution.objects.filter(agent=agent)
        
        context = {
            'agent': agent,
            'total_tasks': tasks.count(),
            'completed_tasks': tasks.filter(state='completed').count(),
            'failed_tasks': tasks.filter(state='failed').count(),
            'success_rate': self.calculate_rate(tasks),
            'avg_execution_time': executions.filter(completed_at__isnull=False).aggregate(Avg('duration_ms'))['duration_ms__avg'] or 0,
            'total_earned': agent.total_earned,
            'trust_score': agent.trust_score,
            'recent_executions': executions.order_by('-created_at')[:20],
            'daily_stats': self.get_daily_stats(agent),
        }
        return render(request, self.template_name, context)
    
    def calculate_rate(self, tasks):
        completed = tasks.filter(state='completed').count()
        total = tasks.exclude(state='open').count()
        return (completed / total * 100) if total > 0 else 0
    
    def get_daily_stats(self, agent):
        from apps.tasks.models import Task
        stats = []
        for i in range(7, 0, -1):
            date = timezone.now() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0)
            day_end = day_start + timedelta(days=1)
            
            tasks = Task.objects.filter(
                matched_agent=agent,
                completed_at__range=[day_start, day_end]
            ).count()
            
            stats.append({
                'date': date.strftime('%b %d'),
                'tasks': tasks,
            })
        return stats

class AgentEarningsView(LoginRequiredMixin, View):
    template_name = 'agents/earnings.html'
    
    def get(self, request):
        from apps.payments.models import Transaction
        
        agents = Agent.objects.filter(user=request.user)
        transactions = Transaction.objects.filter(
            to_wallet__owner_id__in=[str(a.id) for a in agents],
            to_wallet__owner_type='agent',
            status='completed'
        ).order_by('-created_at')
        
        context = {
            'agents': agents,
            'transactions': transactions[:50],
            'total_earned': transactions.aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0,
            'monthly_earnings': self.get_monthly_earnings(agents),
            'total_withdrawn': 0,  # Calculate from withdrawals
        }
        return render(request, self.template_name, context)
    
    def get_monthly_earnings(self, agents):
        from apps.payments.models import Transaction
        earnings = []
        for i in range(12):
            date = timezone.now() - timedelta(days=30 * i)
            month_start = date.replace(day=1, hour=0, minute=0, second=0)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            amount = Transaction.objects.filter(
                to_wallet__owner_id__in=[str(a.id) for a in agents],
                to_wallet__owner_type='agent',
                status='completed',
                created_at__range=[month_start, month_end]
            ).aggregate(Sum('amount_sats'))['amount_sats__sum'] or 0
            
            earnings.append({
                'month': month_start.strftime('%B'),
                'amount': amount,
            })
        return earnings

class AgentTasksView(LoginRequiredMixin, View):
    template_name = 'agents/tasks.html'
    
    def get(self, request):
        from apps.tasks.models import Task
        
        agents = Agent.objects.filter(user=request.user)
        
        # Get tasks for all user's agents
        tasks = Task.objects.filter(matched_agent__in=agents).order_by('-created_at')
        
        # Filtering
        status = request.GET.get('status')
        if status:
            tasks = tasks.filter(state=status)
        
        # Pagination
        paginator = Paginator(tasks, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'tasks': page_obj,
            'agents': agents,
            'status_counts': {
                'open': tasks.filter(state='open').count(),
                'assigned': tasks.filter(state='assigned').count(),
                'executing': tasks.filter(state='executing').count(),
                'completed': tasks.filter(state='completed').count(),
            },
            'selected_status': status,
        }
        return render(request, self.template_name, context)

class AgentTaskDetailView(LoginRequiredMixin, View):
    template_name = 'agents/task_detail.html'
    
    def get(self, request, task_id):
        from apps.tasks.models import Task
        from apps.execution.models import Execution, ExecutionLog
        
        task = get_object_or_404(Task, id=task_id)
        execution = Execution.objects.filter(task=task).first()
        logs = ExecutionLog.objects.filter(execution=execution) if execution else []
        
        context = {
            'task': task,
            'execution': execution,
            'logs': logs,
            'can_execute': task.state in ['assigned', 'executing'],
        }
        return render(request, self.template_name, context)

class AgentSettingsView(LoginRequiredMixin, View):
    template_name = 'agents/settings.html'
    
    def get(self, request):
        agents = Agent.objects.filter(user=request.user)
        context = {
            'agents': agents,
            'form': AgentSettingsForm(),
        }
        return render(request, self.template_name, context)
    
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id, user=request.user)
        form = AgentSettingsForm(request.POST, instance=agent)
        if form.is_valid():
            form.save()
            messages.success(request, 'Agent settings updated!')
        return redirect('agents:settings')

class AgentCapabilitiesView(LoginRequiredMixin, View):
    template_name = 'agents/capabilities.html'
    
    def get(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id, user=request.user)
        all_capabilities = Capability.objects.all()
        
        context = {
            'agent': agent,
            'capabilities': all_capabilities,
            'form': AgentCapabilityForm(),
        }
        return render(request, self.template_name, context)
    
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id, user=request.user)
        capabilities = request.POST.getlist('capabilities')
        agent.capabilities = capabilities
        agent.save()
        messages.success(request, 'Capabilities updated!')
        return redirect('agents:capabilities', agent_id=agent.id)

class AgentHeartbeatView(View):
    """API endpoint for agent heartbeat"""
    
    def post(self, request):
        import json
        data = json.loads(request.body)
        agent_id = data.get('agent_id')
        status = data.get('status', 'online')
        latency_ms = data.get('latency_ms', 0)
        metrics = data.get('metrics', {})
        
        agent = Agent.objects.filter(id=agent_id).first()
        if agent:
            agent.last_heartbeat = timezone.now()
            agent.is_available = status == 'online'
            agent.save()
            
            AgentHeartbeat.objects.create(
                agent=agent,
                status=status,
                latency_ms=latency_ms,
                metrics=metrics
            )
            
            return JsonResponse({'success': True})
        return JsonResponse({'success': False}, status=404)

class AgentVerificationView(LoginRequiredMixin, View):
    template_name = 'agents/verification.html'
    
    def get(self, request):
        agents = Agent.objects.filter(user=request.user)
        context = {
            'agents': agents,
            'verification_status': {
                agent.id: self.get_verification_status(agent) for agent in agents
            },
        }
        return render(request, self.template_name, context)
    
    def get_verification_status(self, agent):
        from apps.verification.models import Verification
        verification = Verification.objects.filter(
            task__matched_agent=agent,
            status='approved'
        ).first()
        return {
            'is_verified': verification is not None,
            'verified_at': verification.verified_at if verification else None,
            'quality_score': verification.quality_score if verification else 0,
        }
    
class AgentEditView(LoginRequiredMixin, View):
    template_name = 'agents/edit.html'
    
    def get(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id, user=request.user)
        return render(request, self.template_name, {'agent': agent})
    
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id, user=request.user)
        agent.name = request.POST.get('name')
        agent.description = request.POST.get('description')
        agent.hourly_rate_sats = int(request.POST.get('hourly_rate_sats', 0))
        agent.is_available = request.POST.get('is_available') == 'on'
        agent.save()
        messages.success(request, 'Agent updated successfully!')
        return redirect('agents:agent_detail', agent_id=agent.id)


class AgentDeleteView(LoginRequiredMixin, View):
    def post(self, request, agent_id):
        agent = get_object_or_404(Agent, id=agent_id, user=request.user)
        agent.delete()
        messages.success(request, 'Agent deleted successfully!')
        return redirect('agents:dashboard')


class HumanRegisterView(LoginRequiredMixin, View):
    template_name = 'agents/human_register.html'
    
    def get(self, request):
        return render(request, self.template_name, {
            'form': AgentRegisterForm(),
            'capabilities': Capability.objects.all()
        })
    
    def post(self, request):
        form = AgentRegisterForm(request.POST)
        if form.is_valid():
            agent = form.save(commit=False)
            agent.user = request.user
            agent.agent_type = 'human'
            agent.save()
            agent.capabilities = request.POST.getlist('capabilities')
            agent.save()
            messages.success(request, f'Human Agent {agent.name} registered!')
            return redirect('agents:agent_detail', agent_id=agent.id)
        return render(request, self.template_name, {'form': form})

class StartVerificationView(LoginRequiredMixin, View):
    def post(self, request):
        agent_id = request.POST.get('agent_id')
        agent = get_object_or_404(Agent, id=agent_id, user=request.user)
        
        from apps.verification.models import Verification
        from apps.tasks.models import Task
        
        # Create verification request
        verification = Verification.objects.create(
            task=None,  # Will be linked when agent completes a task
            verification_type='human',
            status='pending',
            quality_score=0,
            confidence=0
        )
        
        messages.info(request, f'Verification requested for {agent.name}. An admin will review shortly.')
        return redirect('agents:verification')