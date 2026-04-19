# apps/execution/views.py
from django.shortcuts import render, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
import json
import time
from .models import Execution, ExecutionLog, Checkpoint
from apps.tasks.models import Task

class ExecutionDashboardView(View):
    template_name = 'execution/dashboard.html'
    
    def get(self, request):
        from django.db.models import Count, Avg
        
        context = {
            'active_executions': Execution.objects.filter(state='running').count(),
            'pending_executions': Execution.objects.filter(state='pending').count(),
            'completed_today': Execution.objects.filter(
                completed_at__date=timezone.now().date()
            ).count(),
            'avg_execution_time': Execution.objects.filter(
                completed_at__isnull=False
            ).aggregate(Avg('duration_ms'))['duration_ms__avg'] or 0,
            'recent_executions': Execution.objects.select_related('task', 'agent').order_by('-created_at')[:20],
            'executions_by_type': {
                'ai': Execution.objects.filter(execution_type='ai').count(),
                'human': Execution.objects.filter(execution_type='human').count(),
                'hybrid': Execution.objects.filter(execution_type='hybrid').count(),
            },
        }
        return render(request, self.template_name, context)

class ExecutionMonitorView(View):
    template_name = 'execution/monitor.html'
    
    def get(self, request):
        executions = Execution.objects.select_related('task', 'agent').order_by('-created_at')
        
        # Filtering
        status = request.GET.get('status')
        if status:
            executions = executions.filter(state=status)
        
        paginator = Paginator(executions, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'executions': page_obj,
            'status_counts': {
                'pending': Execution.objects.filter(state='pending').count(),
                'running': Execution.objects.filter(state='running').count(),
                'completed': Execution.objects.filter(state='completed').count(),
                'failed': Execution.objects.filter(state='failed').count(),
            },
            'selected_status': status,
        }
        return render(request, self.template_name, context)

class LiveExecutionView(View):
    template_name = 'execution/live_view.html'
    
    def get(self, request):
        context = {
            'running_executions': Execution.objects.filter(state='running').select_related('task', 'agent'),
            'websocket_url': 'ws://' + request.get_host() + '/ws/execution/',
        }
        return render(request, self.template_name, context)

class ExecutionDetailView(View):
    template_name = 'execution/detail.html'
    
    def get(self, request, execution_id):
        execution = get_object_or_404(Execution, id=execution_id)
        logs = ExecutionLog.objects.filter(execution=execution).order_by('timestamp')
        checkpoints = Checkpoint.objects.filter(execution=execution).order_by('-created_at')
        
        context = {
            'execution': execution,
            'logs': logs[:200],
            'checkpoints': checkpoints[:10],
            'task': execution.task,
            'agent': execution.agent,
        }
        return render(request, self.template_name, context)

class ExecutionLogView(View):
    template_name = 'execution/log_viewer.html'
    
    def get(self, request, execution_id):
        execution = get_object_or_404(Execution, id=execution_id)
        logs = ExecutionLog.objects.filter(execution=execution).order_by('-timestamp')
        
        # Filter by level
        level = request.GET.get('level')
        if level:
            logs = logs.filter(log_level=level)
        
        paginator = Paginator(logs, 100)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'execution': execution,
            'logs': page_obj,
            'levels': ['info', 'warning', 'error', 'debug'],
            'selected_level': level,
        }
        return render(request, self.template_name, context)

class ExecutionHistoryView(View):
    template_name = 'execution/history.html'
    
    def get(self, request):
        executions = Execution.objects.select_related('task', 'agent').order_by('-created_at')
        
        # Date filtering
        days = request.GET.get('days', 7)
        try:
            days = int(days)
        except:
            days = 7
        
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        executions = executions.filter(created_at__gte=cutoff_date)
        
        context = {
            'executions': executions[:100],
            'days': days,
            'total_count': executions.count(),
            'success_rate': self.calculate_success_rate(executions),
        }
        return render(request, self.template_name, context)
    
    def calculate_success_rate(self, executions):
        completed = executions.filter(state='completed').count()
        total = executions.exclude(state='pending').count()
        return (completed / total * 100) if total > 0 else 0

class PauseExecutionView(LoginRequiredMixin, View):
    def post(self, request, execution_id):
        execution = get_object_or_404(Execution, id=execution_id)
        
        if execution.state == 'running':
            execution.state = 'pending'
            execution.save()
            
            ExecutionLog.objects.create(
                execution=execution,
                log_level='info',
                message=f'Execution paused by {request.user.email}'
            )
            
            return JsonResponse({'success': True, 'message': 'Execution paused'})
        
        return JsonResponse({'success': False, 'error': 'Cannot pause execution'})

class ResumeExecutionView(LoginRequiredMixin, View):
    def post(self, request, execution_id):
        execution = get_object_or_404(Execution, id=execution_id)
        
        if execution.state == 'pending':
            execution.state = 'running'
            execution.save()
            
            ExecutionLog.objects.create(
                execution=execution,
                log_level='info',
                message=f'Execution resumed by {request.user.email}'
            )
            
            return JsonResponse({'success': True, 'message': 'Execution resumed'})
        
        return JsonResponse({'success': False, 'error': 'Cannot resume execution'})

class CancelExecutionView(LoginRequiredMixin, View):
    def post(self, request, execution_id):
        execution = get_object_or_404(Execution, id=execution_id)
        
        if execution.state in ['pending', 'running']:
            execution.state = 'cancelled'
            execution.save()
            
            # Update task
            task = execution.task
            task.state = Task.TaskState.FAILED
            task.save()
            
            ExecutionLog.objects.create(
                execution=execution,
                log_level='warning',
                message=f'Execution cancelled by {request.user.email}'
            )
            
            return JsonResponse({'success': True, 'message': 'Execution cancelled'})
        
        return JsonResponse({'success': False, 'error': 'Cannot cancel execution'})

class RetryExecutionView(LoginRequiredMixin, View):
    def post(self, request, execution_id):
        execution = get_object_or_404(Execution, id=execution_id)
        
        if execution.state == 'failed':
            # Reset execution
            execution.state = 'pending'
            execution.retry_count += 1
            execution.error_message = ''
            execution.save()
            
            # Reset task
            task = execution.task
            task.state = Task.TaskState.ASSIGNED
            task.save()
            
            ExecutionLog.objects.create(
                execution=execution,
                log_level='info',
                message=f'Retry attempt #{execution.retry_count} initiated by {request.user.email}'
            )
            
            return JsonResponse({'success': True, 'message': f'Retry #{execution.retry_count} initiated'})
        
        return JsonResponse({'success': False, 'error': 'Cannot retry execution'})

class ExecutionStreamView(View):
    """Stream execution logs in real-time"""
    
    def get(self, request, execution_id):
        def generate():
            last_id = 0
            while True:
                logs = ExecutionLog.objects.filter(
                    execution_id=execution_id,
                    id__gt=last_id
                ).order_by('timestamp')
                
                for log in logs:
                    yield f"data: {json.dumps({'message': log.message, 'level': log.log_level, 'timestamp': str(log.timestamp)})}\n\n"
                    last_id = log.id
                
                time.sleep(1)
        
        response = StreamingHttpResponse(generate(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        return response
    
class CheckpointView(View):
    """View for managing execution checkpoints"""
    template_name = 'execution/checkpoints.html'
    
    def get(self, request, execution_id):
        execution = get_object_or_404(Execution, id=execution_id)
        checkpoints = Checkpoint.objects.filter(execution=execution).order_by('-created_at')
        
        context = {
            'execution': execution,
            'checkpoints': checkpoints,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, execution_id):
        execution = get_object_or_404(Execution, id=execution_id)
        
        try:
            data = json.loads(request.body)
            
            checkpoint = Checkpoint.objects.create(
                execution=execution,
                name=data.get('name', f'Checkpoint at {timezone.now()}'),
                step_number=data.get('step_number', 0),
                state_data=data.get('state_data', {}),
                output_snapshot=data.get('output_snapshot'),
                metadata=data.get('metadata', {})
            )
            
            ExecutionLog.objects.create(
                execution=execution,
                log_level='info',
                message=f'Checkpoint created: {checkpoint.name}'
            )
            
            return JsonResponse({
                'success': True,
                'checkpoint': {
                    'id': str(checkpoint.id),
                    'name': checkpoint.name,
                    'created_at': str(checkpoint.created_at)
                }
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class RestoreCheckpointView(View):
    """Restore execution from a checkpoint"""
    
    def post(self, request, execution_id, checkpoint_id):
        execution = get_object_or_404(Execution, id=execution_id)
        checkpoint = get_object_or_404(Checkpoint, id=checkpoint_id, execution=execution)
        
        try:
            # Restore state from checkpoint
            execution.state = 'pending'
            execution.save()
            
            ExecutionLog.objects.create(
                execution=execution,
                log_level='warning',
                message=f'Restoring from checkpoint: {checkpoint.name}'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Restored from checkpoint {checkpoint.name}',
                'state_data': checkpoint.state_data
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
        
class AgentExecutionHistoryView(View):
    """View execution history for a specific agent"""
    template_name = 'execution/agent_history.html'
    
    def get(self, request, agent_id):
        from apps.agents.models import Agent
        
        agent = get_object_or_404(Agent, id=agent_id)
        executions = Execution.objects.filter(agent=agent).order_by('-created_at')
        
        # Statistics
        total = executions.count()
        completed = executions.filter(state='completed').count()
        failed = executions.filter(state='failed').count()
        
        context = {
            'agent': agent,
            'executions': executions[:50],
            'total_count': total,
            'success_rate': (completed / total * 100) if total > 0 else 0,
            'failed_count': failed,
        }
        return render(request, self.template_name, context)


class TaskExecutionHistoryView(View):
    """View execution history for a specific task"""
    template_name = 'execution/task_history.html'
    
    def get(self, request, task_id):
        from apps.tasks.models import Task
        
        task = get_object_or_404(Task, id=task_id)
        executions = Execution.objects.filter(task=task).order_by('-created_at')
        
        context = {
            'task': task,
            'executions': executions,
            'execution_count': executions.count(),
        }
        return render(request, self.template_name, context)


class ExecutionWebSocketView(View):
    """WebSocket handler for real-time execution updates"""
    
    def get(self, request, execution_id):
        execution = get_object_or_404(Execution, id=execution_id)
        
        # This would typically be handled by Django Channels
        # For now, return a simple response
        context = {
            'execution': execution,
            'websocket_url': f'ws://{request.get_host()}/ws/execution/{execution_id}/',
        }
        return render(request, 'execution/websocket_test.html', context)