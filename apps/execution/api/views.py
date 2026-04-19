# apps/execution/api/views.py
from django.views import View
from django.http import JsonResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
import json
import uuid
import time

@method_decorator(csrf_exempt, name='dispatch')
class APIExecuteTaskView(View):
    """API endpoint to execute a task"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            task_id = data.get('task_id')
            agent_id = data.get('agent_id')
            execution_type = data.get('execution_type', 'auto')
            
            execution_id = str(uuid.uuid4())
            
            return JsonResponse({
                'status': 'started',
                'execution_id': execution_id,
                'task_id': task_id,
                'agent_id': agent_id,
                'execution_type': execution_type,
                'message': 'Task execution started',
                'started_at': timezone.now().isoformat()
            }, status=202)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class APIExecutionStatusView(View):
    """API endpoint to check execution status"""
    
    def get(self, request, execution_id):
        # Mock response - in production, query actual execution record
        data = {
            'execution_id': execution_id,
            'status': 'running',
            'progress': 65,
            'started_at': timezone.now().isoformat(),
            'duration_ms': 6500,
            'current_step': 'Processing data',
            'logs': [
                {'timestamp': timezone.now().isoformat(), 'level': 'info', 'message': 'Task started'},
                {'timestamp': timezone.now().isoformat(), 'level': 'info', 'message': 'Step 1 completed'},
                {'timestamp': timezone.now().isoformat(), 'level': 'info', 'message': 'Step 2 in progress'},
            ]
        }
        return JsonResponse(data)

@method_decorator(csrf_exempt, name='dispatch')
class APICancelExecutionView(View):
    """API endpoint to cancel an execution"""
    
    def post(self, request, execution_id):
        try:
            data = json.loads(request.body)
            reason = data.get('reason', 'Cancelled by user')
            
            return JsonResponse({
                'status': 'cancelled',
                'execution_id': execution_id,
                'reason': reason,
                'cancelled_at': timezone.now().isoformat(),
                'message': 'Execution cancelled successfully'
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class APISandboxTestView(View):
    """API endpoint to test sandbox environment"""
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            code = data.get('code', '')
            language = data.get('language', 'python')
            
            # Mock sandbox execution
            return JsonResponse({
                'status': 'completed',
                'output': 'Test execution completed successfully',
                'execution_time_ms': 45,
                'memory_used_mb': 12.5,
                'sandbox_id': str(uuid.uuid4())
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class APIExecutionStreamView(View):
    """API endpoint for streaming execution logs"""
    
    def get(self, request, execution_id):
        def generate():
            # Simulate streaming logs
            logs = [
                f"data: {json.dumps({'type': 'log', 'level': 'info', 'message': 'Starting execution...', 'timestamp': time.time()})}\n\n",
                f"data: {json.dumps({'type': 'log', 'level': 'info', 'message': 'Loading task configuration...', 'timestamp': time.time() + 0.5})}\n\n",
                f"data: {json.dumps({'type': 'log', 'level': 'info', 'message': 'Executing task...', 'timestamp': time.time() + 1})}\n\n",
                f"data: {json.dumps({'type': 'progress', 'progress': 50, 'message': 'Halfway there!', 'timestamp': time.time() + 1.5})}\n\n",
                f"data: {json.dumps({'type': 'log', 'level': 'info', 'message': 'Finalizing results...', 'timestamp': time.time() + 2})}\n\n",
                f"data: {json.dumps({'type': 'complete', 'message': 'Execution completed successfully!', 'timestamp': time.time() + 2.5})}\n\n",
            ]
            
            for log in logs:
                yield log
                time.sleep(0.5)
        
        response = StreamingHttpResponse(generate(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response