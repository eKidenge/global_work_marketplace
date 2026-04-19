# apps/dispatch/views.py
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.db.models import Count, Avg
from django.utils import timezone
from datetime import timedelta
from .models import DispatchQueue, DispatchRecord, Assignment
from apps.tasks.models import Task
from apps.agents.models import Agent

class DispatchDashboardView(View):
    template_name = 'dispatch/dashboard.html'
    
    def get(self, request):
        context = {
            'queue_stats': self.get_queue_stats(),
            'active_assignments': Assignment.objects.filter(is_active=True).count(),
            'today_dispatch_count': DispatchRecord.objects.filter(
                created_at__date=timezone.now().date()
            ).count(),
            'avg_dispatch_latency': DispatchRecord.objects.aggregate(Avg('dispatch_latency_ms'))['dispatch_latency_ms__avg'] or 0,
            'recent_dispatches': DispatchRecord.objects.select_related('task', 'selected_agent').order_by('-created_at')[:20],
        }
        return render(request, self.template_name, context)
    
    def get_queue_stats(self):
        return {
            'urgent': DispatchQueue.objects.filter(priority='urgent').count(),
            'high': DispatchQueue.objects.filter(priority='high').count(),
            'normal': DispatchQueue.objects.filter(priority='normal').count(),
            'low': DispatchQueue.objects.filter(priority='low').count(),
            'total': DispatchQueue.objects.count(),
        }

class QueueMonitorView(View):
    template_name = 'dispatch/queue_monitor.html'
    
    def get(self, request):
        queues = {
            'urgent': DispatchQueue.objects.filter(priority='urgent').order_by('queue_position'),
            'high': DispatchQueue.objects.filter(priority='high').order_by('queue_position'),
            'normal': DispatchQueue.objects.filter(priority='normal').order_by('queue_position'),
            'low': DispatchQueue.objects.filter(priority='low').order_by('queue_position'),
        }
        
        context = {
            'queues': queues,
            'total_waiting': sum(q.count() for q in queues.values()),
            'avg_wait_time': DispatchQueue.objects.aggregate(Avg('estimated_wait_ms'))['estimated_wait_ms__avg'] or 0,
        }
        return render(request, self.template_name, context)

class AssignmentListView(View):
    template_name = 'dispatch/assignments.html'
    
    def get(self, request):
        assignments = Assignment.objects.select_related('task', 'agent').order_by('-assigned_at')
        
        context = {
            'assignments': assignments[:100],
            'active_assignments': assignments.filter(is_active=True).count(),
            'completed_assignments': assignments.filter(is_active=False).count(),
        }
        return render(request, self.template_name, context)

class RealtimeDispatchView(View):
    template_name = 'dispatch/realtime_board.html'
    
    def get(self, request):
        context = {
            'pending_tasks': Task.objects.filter(state='open').count(),
            'available_agents': Agent.objects.filter(is_available=True, is_active=True).count(),
            'recent_matches': DispatchRecord.objects.select_related('task', 'selected_agent').order_by('-created_at')[:10],
        }
        return render(request, self.template_name, context)

class DispatchHistoryView(View):
    template_name = 'dispatch/history.html'
    
    def get(self, request):
        records = DispatchRecord.objects.select_related('task', 'selected_agent').order_by('-created_at')
        
        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(records, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'records': page_obj,
            'total_dispatches': records.count(),
        }
        return render(request, self.template_name, context)

@method_decorator(staff_member_required, name='dispatch')
class MatchTaskView(View):
    """API endpoint for matching tasks"""
    
    def post(self, request):
        import json
        data = json.loads(request.body)
        task_id = data.get('task_id')
        
        task = get_object_or_404(Task, id=task_id, state='open')
        
        # Find best matching agent
        from apps.core_engine.router import Router
        router = Router()
        best_agent = router.route_task(task)
        
        if best_agent:
            # Create dispatch record
            DispatchRecord.objects.create(
                task=task,
                selected_agent=best_agent,
                candidate_agents=[best_agent.id],
                decision_reason="Best match based on capabilities and trust score",
                score=best_agent.trust_score,
                dispatch_latency_ms=100
            )
            
            # Create assignment
            Assignment.objects.create(
                task=task,
                agent=best_agent,
                assigned_at=timezone.now()
            )
            
            return JsonResponse({
                'success': True,
                'agent_id': str(best_agent.id),
                'agent_name': best_agent.name
            })
        
        return JsonResponse({'success': False, 'error': 'No suitable agent found'})

class AssignmentDetailView(LoginRequiredMixin, View):
    template_name = 'dispatch/assignment_detail.html'
    
    def get(self, request, assignment_id):
        assignment = get_object_or_404(Assignment, id=assignment_id)
        return render(request, self.template_name, {'assignment': assignment})


class ReassignTaskView(LoginRequiredMixin, View):
    def post(self, request, assignment_id):
        assignment = get_object_or_404(Assignment, id=assignment_id)
        assignment.is_active = False
        assignment.save()
        
        task = assignment.task
        task.state = 'open'
        task.matched_agent = None
        task.save()
        
        messages.success(request, 'Task reassigned to open pool')
        return redirect('dispatch:assignments')

class DispatchBoardView(LoginRequiredMixin, View):
    template_name = 'dispatch/dispatch_board.html'
    
    def get(self, request):
        from apps.tasks.models import Task
        from apps.agents.models import Agent
        
        context = {
            'pending_tasks': Task.objects.filter(state='open').count(),
            'available_agents': Agent.objects.filter(is_available=True, is_active=True).count(),
            'recent_matches': DispatchRecord.objects.select_related('task', 'selected_agent').order_by('-created_at')[:10],
        }
        return render(request, self.template_name, context)

class DispatchStatsView(View):
    def get(self, request):
        from apps.tasks.models import Task
        from apps.agents.models import Agent
        from .models import DispatchQueue
        
        data = {
            'pending_tasks': Task.objects.filter(state='open').count(),
            'available_agents': Agent.objects.filter(is_available=True, is_active=True).count(),
            'queue_size': DispatchQueue.objects.count(),
            'avg_wait_time': DispatchQueue.objects.aggregate(Avg('estimated_wait_ms'))['estimated_wait_ms__avg'] or 0,
        }
        return JsonResponse(data)

class DispatchRecordView(View):
    template_name = 'dispatch/dispatch_record.html'
    
    def get(self, request, record_id):
        record = get_object_or_404(DispatchRecord, id=record_id)
        return render(request, self.template_name, {'record': record})

class AssignTaskView(LoginRequiredMixin, View):
    def post(self, request):
        task_id = request.POST.get('task_id')
        agent_id = request.POST.get('agent_id')
        
        task = get_object_or_404(Task, id=task_id, state='open')
        agent = get_object_or_404(Agent, id=agent_id, is_active=True)
        
        task.state = Task.TaskState.ASSIGNED
        task.matched_agent = agent
        task.assigned_at = timezone.now()
        task.save()
        
        Assignment.objects.create(
            task=task,
            agent=agent,
            assigned_at=timezone.now(),
            is_active=True
        )
        
        messages.success(request, f'Task assigned to {agent.name}')
        return redirect('dispatch:assignments')