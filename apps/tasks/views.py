# apps/tasks/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.utils import timezone
from datetime import timedelta
from .models import Task, TaskTemplate, MicroTask
from .forms import TaskCreateForm, TaskEditForm, TaskBidForm, MicroTaskForm


class TaskListView(View):
    template_name = 'tasks/list.html'
    
    def get(self, request):
        tasks = Task.objects.filter(state='open', is_microtask=False)
        
        category = request.GET.get('category')
        if category:
            tasks = tasks.filter(required_capabilities__contains=[category])
        
        min_budget = request.GET.get('min_budget')
        if min_budget:
            tasks = tasks.filter(budget_sats__gte=int(min_budget))
        
        max_budget = request.GET.get('max_budget')
        if max_budget:
            tasks = tasks.filter(budget_sats__lte=int(max_budget))
        
        search = request.GET.get('search')
        if search:
            tasks = tasks.filter(Q(title__icontains=search) | Q(description__icontains=search))
        
        paginator = Paginator(tasks, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'tasks': page_obj,
            'total_tasks': tasks.count(),
            'total_volume': tasks.aggregate(Sum('budget_sats'))['budget_sats__sum'] or 0,
            'search': search,
            'categories': self.get_categories(),
        }
        return render(request, self.template_name, context)
    
    def get_categories(self):
        from apps.agents.models import Capability
        return Capability.objects.all()


class OpenTasksView(View):
    template_name = 'tasks/open_tasks.html'
    
    def get(self, request):
        tasks = Task.objects.filter(state='open', is_microtask=False).order_by('-created_at')
        
        priority = request.GET.get('priority')
        if priority:
            tasks = tasks.filter(priority=priority)
        
        context = {
            'tasks': tasks[:50],
            'priority_counts': {
                'urgent': tasks.filter(priority='urgent').count(),
                'high': tasks.filter(priority='high').count(),
                'normal': tasks.filter(priority='normal').count(),
                'low': tasks.filter(priority='low').count(),
            },
        }
        return render(request, self.template_name, context)


class MyTasksView(LoginRequiredMixin, View):
    template_name = 'tasks/my_tasks.html'
    
    def get(self, request):
        from apps.agents.models import Agent
        
        user = request.user
        
        # Get the user's agent profile if exists
        user_agent = Agent.objects.filter(user=user).first()
        
        # Initialize empty queryset
        tasks = Task.objects.none()
        
        if user_agent:
            # Tasks where user's agent is matched
            tasks = tasks | Task.objects.filter(matched_agent=user_agent)
            
            # Tasks from assignments
            from apps.dispatch.models import Assignment
            assignments = Assignment.objects.filter(agent=user_agent)
            tasks = tasks | Task.objects.filter(assignment__in=assignments)
            
            # Tasks from execution
            from apps.execution.models import Execution
            executions = Execution.objects.filter(agent=user_agent)
            tasks = tasks | Task.objects.filter(execution__in=executions)
        
        # Remove duplicates and order
        tasks = tasks.distinct().order_by('-created_at')
        
        context = {
            'tasks': tasks[:50],
            'status_counts': {
                'open': tasks.filter(state='open').count(),
                'assigned': tasks.filter(state='assigned').count(),
                'executing': tasks.filter(state='executing').count(),
                'completed': tasks.filter(state='completed').count(),
                'failed': tasks.filter(state='failed').count(),
            },
        }
        return render(request, self.template_name, context)


class AssignedTasksView(LoginRequiredMixin, View):
    template_name = 'tasks/assigned_to_me.html'
    
    def get(self, request):
        from apps.agents.models import Agent
        
        agents = Agent.objects.filter(user=request.user)
        tasks = Task.objects.filter(
            matched_agent__in=agents,
            state__in=['assigned', 'executing']
        ).order_by('-assigned_at')
        
        context = {
            'tasks': tasks,
            'agents': agents,
        }
        return render(request, self.template_name, context)


class CompletedTasksView(View):
    template_name = 'tasks/completed.html'
    
    def get(self, request):
        tasks = Task.objects.filter(state='completed').order_by('-completed_at')[:100]
        
        context = {
            'tasks': tasks,
            'total_completed': tasks.count(),
            'total_volume': tasks.aggregate(Sum('budget_sats'))['budget_sats__sum'] or 0,
        }
        return render(request, self.template_name, context)


class TaskCreateView(LoginRequiredMixin, View):
    template_name = 'tasks/create.html'
    
    def get(self, request):
        from apps.agents.models import Capability
        
        context = {
            'form': TaskCreateForm(),
            'capabilities': Capability.objects.all(),
            'templates': TaskTemplate.objects.filter(is_active=True),
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        form = TaskCreateForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.expires_at = timezone.now() + timedelta(hours=24)
            task.save()
            task.required_capabilities = request.POST.getlist('capabilities')
            task.save()
            
            messages.success(request, f'Task "{task.title}" created successfully!')
            return redirect('tasks:task_detail', task_id=task.id)
        
        return render(request, self.template_name, {'form': form})


class TaskDetailView(View):
    template_name = 'tasks/detail.html'
    
    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        from apps.agents.models import Agent
        from apps.execution.models import Execution, ExecutionLog
        
        similar_tasks = Task.objects.filter(
            required_capabilities__overlap=task.required_capabilities
        ).exclude(id=task.id)[:5]
        
        context = {
            'task': task,
            'similar_tasks': similar_tasks,
            'suggested_agents': self.get_suggested_agents(task),
            'execution': Execution.objects.filter(task=task).first(),
            'logs': ExecutionLog.objects.filter(execution__task=task)[:50] if task.execution else [],
            'can_bid': task.state == 'open' and request.user.is_authenticated,
            'can_execute': task.state in ['assigned', 'executing'] and self.is_assigned_to_user(task, request),
        }
        return render(request, self.template_name, context)
    
    def get_suggested_agents(self, task):
        from apps.agents.models import Agent
        return Agent.objects.filter(
            capabilities__overlap=task.required_capabilities,
            is_active=True,
            is_available=True
        ).order_by('-trust_score')[:5]
    
    def is_assigned_to_user(self, task, request):
        if not request.user.is_authenticated:
            return False
        from apps.agents.models import Agent
        user_agents = Agent.objects.filter(user=request.user)
        return task.matched_agent in user_agents


class TaskEditView(LoginRequiredMixin, View):
    template_name = 'tasks/edit.html'
    
    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, created_by=request.user)
        form = TaskEditForm(instance=task)
        
        context = {
            'form': form,
            'task': task,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, created_by=request.user)
        form = TaskEditForm(request.POST, instance=task)
        
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully!')
            return redirect('tasks:task_detail', task_id=task.id)
        
        return render(request, self.template_name, {'form': form, 'task': task})


class TaskDeleteView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, created_by=request.user)
        task.delete()
        messages.success(request, 'Task deleted successfully!')
        return redirect('tasks:my_tasks')


class TaskCancelView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        
        from apps.agents.models import Agent
        user_agents = Agent.objects.filter(user=request.user)
        
        if task.created_by == request.user or task.matched_agent in user_agents:
            task.state = Task.TaskState.CANCELLED
            task.save()
            messages.success(request, 'Task cancelled successfully!')
        else:
            messages.error(request, 'You do not have permission to cancel this task.')
        
        return redirect('tasks:task_detail', task_id=task.id)


class TaskBidView(LoginRequiredMixin, View):
    template_name = 'tasks/bid.html'
    
    def get(self, request, task_id):
        from apps.agents.models import Agent
        
        task = get_object_or_404(Task, id=task_id, state='open')
        agents = Agent.objects.filter(user=request.user, is_active=True)
        
        context = {
            'task': task,
            'agents': agents,
            'form': TaskBidForm(),
        }
        return render(request, self.template_name, context)
    
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, state='open')
        agent_id = request.POST.get('agent_id')
        bid_amount = request.POST.get('bid_amount')
        
        from apps.agents.models import Agent
        agent = get_object_or_404(Agent, id=agent_id, user=request.user)
        
        from apps.dispatch.models import Assignment
        assignment = Assignment.objects.create(
            task=task,
            agent=agent,
            assigned_at=timezone.now()
        )
        
        if int(bid_amount) <= task.budget_sats:
            task.state = Task.TaskState.ASSIGNED
            task.matched_agent = agent
            task.assigned_price_sats = bid_amount
            task.assigned_at = timezone.now()
            task.save()
            
            messages.success(request, f'Your bid has been accepted! Task assigned to {agent.name}')
        else:
            messages.info(request, 'Your bid has been submitted for review.')
        
        return redirect('tasks:task_detail', task_id=task.id)


class TaskAcceptView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, created_by=request.user, state='assigned')
        task.state = Task.TaskState.EXECUTING
        task.started_at = timezone.now()
        task.save()
        
        messages.success(request, 'Task accepted and execution started!')
        return redirect('tasks:task_detail', task_id=task.id)


class TaskStartView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        from apps.agents.models import Agent
        
        task = get_object_or_404(Task, id=task_id)
        user_agents = Agent.objects.filter(user=request.user)
        
        if task.matched_agent in user_agents and task.state == 'assigned':
            task.state = Task.TaskState.EXECUTING
            task.started_at = timezone.now()
            task.save()
            
            from apps.execution.models import Execution
            Execution.objects.create(
                task=task,
                agent=task.matched_agent,
                execution_type='human' if task.matched_agent.agent_type == 'human' else 'ai',
                state='running',
                started_at=timezone.now()
            )
            
            messages.success(request, 'Task execution started!')
        
        return redirect('tasks:task_detail', task_id=task.id)


class TaskCompleteView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        from apps.agents.models import Agent
        from apps.payments.models import Transaction, Wallet
        from apps.verification.models import Verification
        
        task = get_object_or_404(Task, id=task_id)
        user_agents = Agent.objects.filter(user=request.user)
        
        if task.matched_agent in user_agents and task.state == 'executing':
            task.state = Task.TaskState.VERIFYING
            task.completed_at = timezone.now()
            task.save()
            
            from apps.execution.models import Execution
            execution = Execution.objects.filter(task=task).first()
            if execution:
                execution.state = 'completed'
                execution.completed_at = timezone.now()
                execution.duration_ms = int((timezone.now() - execution.started_at).total_seconds() * 1000)
                execution.save()
            
            Verification.objects.create(
                task=task,
                verification_type='auto',
                status='pending',
                quality_score=0.0,
                confidence=0.0
            )
            
            messages.success(request, 'Task completed! Awaiting verification.')
        
        return redirect('tasks:task_detail', task_id=task.id)


class TaskReportView(LoginRequiredMixin, View):
    template_name = 'tasks/report.html'
    
    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        
        from apps.execution.models import Execution, ExecutionLog
        from apps.verification.models import Verification, Dispute
        
        context = {
            'task': task,
            'execution': Execution.objects.filter(task=task).first(),
            'logs': ExecutionLog.objects.filter(execution__task=task)[:100],
            'verification': Verification.objects.filter(task=task).first(),
            'dispute': Dispute.objects.filter(task=task).first(),
        }
        return render(request, self.template_name, context)


class MicroTaskListView(View):
    template_name = 'tasks/microtasks.html'
    
    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        microtasks = MicroTask.objects.filter(parent_task=task).order_by('order')
        
        context = {
            'task': task,
            'microtasks': microtasks,
            'progress': self.calculate_progress(microtasks),
        }
        return render(request, self.template_name, context)
    
    def calculate_progress(self, microtasks):
        if not microtasks:
            return 0
        completed = microtasks.filter(completed=True).count()
        return int(completed / len(microtasks) * 100)


class MicroTaskCreateView(LoginRequiredMixin, View):
    template_name = 'tasks/microtask_create.html'
    
    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, created_by=request.user)
        return render(request, self.template_name, {
            'task': task,
            'form': MicroTaskForm(),
            'next_order': MicroTask.objects.filter(parent_task=task).count() + 1
        })
    
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, created_by=request.user)
        form = MicroTaskForm(request.POST)
        
        if form.is_valid():
            microtask = form.save(commit=False)
            microtask.parent_task = task
            microtask.order = MicroTask.objects.filter(parent_task=task).count() + 1
            microtask.save()
            
            messages.success(request, 'Microtask created!')
            return redirect('tasks:microtask_list', task_id=task.id)
        
        return render(request, self.template_name, {'form': form, 'task': task})


class TaskTemplateListView(View):
    template_name = 'tasks/templates/list.html'
    
    def get(self, request):
        templates = TaskTemplate.objects.filter(is_active=True)
        
        context = {
            'templates': templates,
            'categories': templates.values_list('category', flat=True).distinct(),
        }
        return render(request, self.template_name, context)


class TaskTemplateCreateView(LoginRequiredMixin, View):
    template_name = 'tasks/templates/create.html'
    
    def get(self, request):
        from apps.agents.models import Capability
        
        context = {
            'form': TaskCreateForm(),
            'capabilities': Capability.objects.all(),
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        form = TaskCreateForm(request.POST)
        if form.is_valid():
            template = form.save()
            template.required_capabilities = request.POST.getlist('capabilities')
            template.save()
            
            messages.success(request, f'Template "{template.name}" created!')
            return redirect('tasks:template_list')
        
        return render(request, self.template_name, {'form': form})


class TaskRejectView(LoginRequiredMixin, View):
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, matched_agent__user=request.user, state='assigned')
        task.state = Task.TaskState.OPEN
        task.matched_agent = None
        task.assigned_at = None
        task.save()
        messages.info(request, 'Task rejected and returned to open pool')
        return redirect('tasks:assigned_to_me')


class MicroTaskDetailView(LoginRequiredMixin, View):
    template_name = 'tasks/microtask_detail.html'
    
    def get(self, request, microtask_id):
        microtask = get_object_or_404(MicroTask, id=microtask_id)
        return render(request, self.template_name, {'microtask': microtask})


class MicroTaskCompleteView(LoginRequiredMixin, View):
    def post(self, request, microtask_id):
        microtask = get_object_or_404(MicroTask, id=microtask_id)
        microtask.completed = True
        microtask.completed_at = timezone.now()
        microtask.save()
        messages.success(request, 'Microtask completed!')
        return redirect('tasks:microtask_list', task_id=microtask.parent_task.id)


class TaskTemplateDetailView(View):
    template_name = 'tasks/templates/detail.html'
    
    def get(self, request, template_id):
        template = get_object_or_404(TaskTemplate, id=template_id)
        return render(request, self.template_name, {'template': template})


class UseTemplateView(LoginRequiredMixin, View):
    def post(self, request, template_id):
        template = get_object_or_404(TaskTemplate, id=template_id)
        
        task = Task.objects.create(
            title=template.name,
            description=template.description,
            budget_sats=template.default_budget_sats,
            required_capabilities=template.required_capabilities,
            created_by=request.user,
            expires_at=timezone.now() + timedelta(hours=24),
            state='open'
        )
        
        messages.success(request, f'Task created from template "{template.name}"')
        return redirect('tasks:task_detail', task_id=task.id)