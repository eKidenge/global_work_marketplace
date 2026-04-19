# apps/dispatch/api/views.py
from django.views import View
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
import uuid

@method_decorator(csrf_exempt, name='dispatch')
class APIDispatchTaskView(View):
    """API endpoint for dispatching a task to an agent"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')
            agent_id = data.get('agent_id')
            
            # In production, this would use the dispatch engine
            dispatch_id = str(uuid.uuid4())
            
            return JsonResponse({
                'status': 'dispatched',
                'dispatch_id': dispatch_id,
                'task_id': task_id,
                'agent_id': agent_id,
                'message': 'Task dispatched successfully',
                'timestamp': timezone.now().isoformat()
            }, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class APIDispatchStatusView(View):
    """API endpoint to check dispatch status"""
    
    def get(self, request, dispatch_id):
        # Mock response - in production, query actual dispatch record
        data = {
            'dispatch_id': dispatch_id,
            'status': 'completed',
            'task_id': 'mock-task-id',
            'agent_id': 'mock-agent-id',
            'dispatched_at': timezone.now().isoformat(),
            'completed_at': timezone.now().isoformat(),
            'duration_ms': 150
        }
        return JsonResponse(data)

class APIDispatchQueueView(View):
    """API endpoint to view dispatch queue"""
    
    def get(self, request):
        data = {
            'queue_size': 5,
            'pending_dispatches': 3,
            'active_dispatches': 2,
            'queue': [
                {
                    'task_id': 'task-1',
                    'priority': 'high',
                    'waiting_time_ms': 120
                },
                {
                    'task_id': 'task-2', 
                    'priority': 'medium',
                    'waiting_time_ms': 45
                }
            ]
        }
        return JsonResponse(data)

@method_decorator(csrf_exempt, name='dispatch')
class APIMatchTaskView(View):
    """API endpoint to match a task with suitable agents"""
    
    def get(self, request, task_id):
        # Mock matching logic
        data = {
            'task_id': task_id,
            'matched_agents': [
                {
                    'agent_id': 'agent-1',
                    'name': 'GPT-4 Agent',
                    'match_score': 0.95,
                    'estimated_cost_sats': 100
                },
                {
                    'agent_id': 'agent-2',
                    'name': 'Human Expert',
                    'match_score': 0.87,
                    'estimated_cost_sats': 250
                }
            ],
            'best_match': 'agent-1'
        }
        return JsonResponse(data)
    
    def post(self, request, task_id):
        try:
            data = json.loads(request.body)
            agent_id = data.get('agent_id')
            
            return JsonResponse({
                'status': 'matched',
                'task_id': task_id,
                'agent_id': agent_id,
                'match_score': 0.95,
                'message': 'Task matched successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class APIMatchAgentView(View):
    """API endpoint to find tasks for an agent"""
    
    def get(self, request, agent_id):
        data = {
            'agent_id': agent_id,
            'available_tasks': [
                {
                    'task_id': 'task-1',
                    'title': 'Data Entry Task',
                    'reward_sats': 50,
                    'match_score': 0.92
                },
                {
                    'task_id': 'task-2',
                    'title': 'Code Review',
                    'reward_sats': 200,
                    'match_score': 0.78
                }
            ],
            'recommended_task': 'task-1'
        }
        return JsonResponse(data)

class APITaskPriorityView(View):
    """API endpoint to get/set task priority"""
    
    def get(self, request, task_id):
        data = {
            'task_id': task_id,
            'priority': 'medium',
            'priority_score': 0.65,
            'factors': {
                'urgency': 0.7,
                'budget': 0.6,
                'sla': 0.8,
                'user_tier': 0.5
            }
        }
        return JsonResponse(data)
    
    def post(self, request, task_id):
        try:
            data = json.loads(request.body)
            priority = data.get('priority', 'medium')
            
            return JsonResponse({
                'status': 'updated',
                'task_id': task_id,
                'priority': priority,
                'message': 'Task priority updated'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class APIQueuePriorityView(View):
    """API endpoint to view queue priorities"""
    
    def get(self, request):
        data = {
            'queues': {
                'urgent': {
                    'count': 3,
                    'max_wait_time_ms': 5000
                },
                'normal': {
                    'count': 12,
                    'max_wait_time_ms': 30000
                },
                'batch': {
                    'count': 45,
                    'max_wait_time_ms': 300000
                }
            },
            'total_tasks': 60,
            'average_wait_time_ms': 15000
        }
        return JsonResponse(data)