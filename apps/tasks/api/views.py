# apps/tasks/api/views.py
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

@method_decorator(csrf_exempt, name='dispatch')
class APITaskListView(View):
    """API endpoint for listing tasks"""
    
    def get(self, request):
        from apps.tasks.models import Task
        
        tasks = Task.objects.filter(state='open').order_by('-created_at')[:50]
        data = {
            'tasks': [
                {
                    'id': str(task.id),
                    'title': task.title,
                    'description': task.description,
                    'reward_sats': task.reward_sats,
                    'task_type': task.task_type,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                }
                for task in tasks
            ],
            'count': tasks.count()
        }
        return JsonResponse(data)
    
    def post(self, request):
        """Create a new task via API"""
        try:
            data = json.loads(request.body)
            from apps.tasks.models import Task
            
            task = Task.objects.create(
                title=data.get('title'),
                description=data.get('description'),
                reward_sats=data.get('reward_sats', 0),
                task_type=data.get('task_type', 'micro'),
                created_by_id=data.get('created_by'),
                state='open'
            )
            
            return JsonResponse({
                'status': 'created',
                'task_id': str(task.id),
                'message': 'Task created successfully'
            }, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class APITaskDetailView(View):
    """API endpoint for task details"""
    
    def get(self, request, task_id):
        from apps.tasks.models import Task
        
        try:
            task = Task.objects.get(id=task_id)
            data = {
                'id': str(task.id),
                'title': task.title,
                'description': task.description,
                'reward_sats': task.reward_sats,
                'task_type': task.task_type,
                'state': task.state,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'matched_agent_id': str(task.matched_agent_id) if task.matched_agent_id else None,
            }
            return JsonResponse(data)
        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)

class APIAvailableTasksView(View):
    """API endpoint for available tasks for agents"""
    
    def get(self, request):
        from apps.tasks.models import Task
        
        # Get tasks that are open and not assigned
        tasks = Task.objects.filter(state='open').order_by('-created_at')[:50]
        
        data = {
            'tasks': [
                {
                    'id': str(task.id),
                    'title': task.title,
                    'description': task.description[:200],
                    'reward_sats': task.reward_sats,
                    'task_type': task.task_type,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                }
                for task in tasks
            ]
        }
        return JsonResponse(data)

@method_decorator(csrf_exempt, name='dispatch')
class APIAcceptTaskView(View):
    """API endpoint for agent to accept a task"""
    
    def post(self, request, task_id):
        from apps.tasks.models import Task
        from apps.agents.models import Agent
        
        try:
            task = Task.objects.get(id=task_id)
            
            # Get agent ID from request (would come from auth in production)
            data = json.loads(request.body)
            agent_id = data.get('agent_id')
            
            if task.state != 'open':
                return JsonResponse({'error': 'Task is not available'}, status=400)
            
            task.state = 'assigned'
            task.matched_agent_id = agent_id
            task.assigned_at = timezone.now()
            task.save()
            
            return JsonResponse({
                'status': 'accepted',
                'task_id': str(task.id),
                'message': 'Task accepted successfully'
            })
        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class APISubmitTaskView(View):
    """API endpoint for agent to submit task results"""
    
    def post(self, request, task_id):
        from apps.tasks.models import Task
        
        try:
            task = Task.objects.get(id=task_id)
            data = json.loads(request.body)
            
            if task.state != 'assigned':
                return JsonResponse({'error': 'Task is not assigned to you'}, status=400)
            
            task.result = data.get('result', {})
            task.state = 'verifying'
            task.completed_at = timezone.now()
            task.save()
            
            return JsonResponse({
                'status': 'submitted',
                'task_id': str(task.id),
                'message': 'Task results submitted for verification'
            })
        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)

class APITaskStatusView(View):
    """API endpoint to check task status"""
    
    def get(self, request, task_id):
        from apps.tasks.models import Task
        
        try:
            task = Task.objects.get(id=task_id)
            data = {
                'task_id': str(task.id),
                'status': task.state,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'assigned_at': task.assigned_at.isoformat() if task.assigned_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'result': task.result if task.state == 'completed' else None,
            }
            return JsonResponse(data)
        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)

class APITaskCategoriesView(View):
    """API endpoint for task categories"""
    
    def get(self, request):
        data = {
            'categories': [
                {'id': 'micro', 'name': 'Micro Task', 'description': 'Small tasks taking seconds to minutes'},
                {'id': 'standard', 'name': 'Standard Task', 'description': 'Regular tasks taking minutes to hours'},
                {'id': 'complex', 'name': 'Complex Task', 'description': 'Multi-step tasks requiring coordination'},
                {'id': 'ai_only', 'name': 'AI Only', 'description': 'Tasks best suited for AI agents'},
                {'id': 'human_only', 'name': 'Human Only', 'description': 'Tasks requiring human judgment'},
            ]
        }
        return JsonResponse(data)