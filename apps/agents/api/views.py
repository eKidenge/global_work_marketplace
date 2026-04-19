# apps/agents/api/views.py
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json

@method_decorator(csrf_exempt, name='dispatch')
class APIAgentListView(View):
    """API endpoint for listing agents"""
    
    def get(self, request):
        from apps.agents.models import Agent
        
        agents = Agent.objects.filter(is_active=True)
        data = {
            'agents': [
                {
                    'id': str(agent.id),
                    'name': agent.name,
                    'agent_type': agent.agent_type,
                    'status': agent.status,
                    'reputation_score': float(agent.reputation_score) if agent.reputation_score else 0,
                }
                for agent in agents[:50]
            ],
            'count': agents.count()
        }
        return JsonResponse(data)
    
    def post(self, request):
        """Register a new AI agent via API"""
        try:
            data = json.loads(request.body)
            from apps.agents.models import Agent
            
            agent = Agent.objects.create(
                name=data.get('name'),
                agent_type='ai',
                api_endpoint=data.get('api_endpoint'),
                api_key=data.get('api_key'),
                capabilities=data.get('capabilities', []),
                is_active=True
            )
            
            return JsonResponse({
                'status': 'created',
                'agent_id': str(agent.id),
                'message': 'Agent registered successfully'
            }, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class APIAgentDetailView(View):
    """API endpoint for agent details"""
    
    def get(self, request, agent_id):
        from apps.agents.models import Agent
        
        try:
            agent = Agent.objects.get(id=agent_id)
            data = {
                'id': str(agent.id),
                'name': agent.name,
                'agent_type': agent.agent_type,
                'status': agent.status,
                'reputation_score': float(agent.reputation_score) if agent.reputation_score else 0,
                'capabilities': agent.capabilities,
                'total_tasks': agent.total_tasks_completed,
                'success_rate': float(agent.success_rate) if agent.success_rate else 0,
                'created_at': agent.created_at.isoformat() if agent.created_at else None,
            }
            return JsonResponse(data)
        except Agent.DoesNotExist:
            return JsonResponse({'error': 'Agent not found'}, status=404)
    
    def put(self, request, agent_id):
        """Update agent status or capabilities"""
        from apps.agents.models import Agent
        
        try:
            agent = Agent.objects.get(id=agent_id)
            data = json.loads(request.body)
            
            if 'status' in data:
                agent.status = data['status']
            if 'capabilities' in data:
                agent.capabilities = data['capabilities']
            if 'api_endpoint' in data:
                agent.api_endpoint = data['api_endpoint']
            
            agent.save()
            return JsonResponse({'status': 'updated', 'agent_id': str(agent.id)})
        except Agent.DoesNotExist:
            return JsonResponse({'error': 'Agent not found'}, status=404)

class APIAgentTasksView(View):
    """API endpoint for agent tasks"""
    
    def get(self, request, agent_id):
        from apps.tasks.models import Task
        
        tasks = Task.objects.filter(matched_agent_id=agent_id).order_by('-created_at')[:20]
        data = {
            'tasks': [
                {
                    'id': str(task.id),
                    'title': task.title,
                    'status': task.state,
                    'reward_sats': task.reward_sats,
                    'created_at': task.created_at.isoformat() if task.created_at else None,
                }
                for task in tasks
            ]
        }
        return JsonResponse(data)

@method_decorator(csrf_exempt, name='dispatch')
class APIAgentHeartbeatView(View):
    """API endpoint for agent heartbeat"""
    
    def post(self, request, agent_id):
        from apps.agents.models import Agent
        
        try:
            agent = Agent.objects.get(id=agent_id)
            agent.last_heartbeat = timezone.now()
            agent.status = 'online'
            agent.save()
            return JsonResponse({'status': 'ok', 'message': 'Heartbeat received'})
        except Agent.DoesNotExist:
            return JsonResponse({'error': 'Agent not found'}, status=404)

@method_decorator(csrf_exempt, name='dispatch')
class APIAcceptTaskView(View):
    """API endpoint for agent to accept a task"""
    
    def post(self, request, task_id):
        from apps.tasks.models import Task
        
        try:
            task = Task.objects.get(id=task_id)
            task.state = Task.TaskState.ASSIGNED
            task.accepted_at = timezone.now()
            task.save()
            return JsonResponse({'status': 'accepted', 'task_id': str(task.id)})
        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)

@method_decorator(csrf_exempt, name='dispatch')
class APISubmitTaskView(View):
    """API endpoint for agent to submit task results"""
    
    def post(self, request, task_id):
        from apps.tasks.models import Task
        
        try:
            task = Task.objects.get(id=task_id)
            data = json.loads(request.body)
            
            task.result = data.get('result', {})
            task.state = Task.TaskState.VERIFYING
            task.completed_at = timezone.now()
            task.save()
            
            return JsonResponse({'status': 'submitted', 'task_id': str(task.id)})
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
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'result': task.result if task.state == Task.TaskState.COMPLETED else None,
            }
            return JsonResponse(data)
        except Task.DoesNotExist:
            return JsonResponse({'error': 'Task not found'}, status=404)