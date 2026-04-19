# apps/verification/api/views.py
from django.views import View
from django.http import JsonResponse
from django.utils import timezone
import json
import uuid

class APIVerifyTaskView(View):
    def post(self, request, task_id):
        return JsonResponse({
            'status': 'submitted',
            'verification_id': str(uuid.uuid4()),
            'task_id': task_id,
            'message': 'Verification submitted'
        })

class APIVerificationStatusView(View):
    def get(self, request, verification_id):
        return JsonResponse({
            'id': verification_id,
            'status': 'pending',
            'quality_score': None,
            'created_at': timezone.now().isoformat()
        })

class APIReputationView(View):
    def get(self, request, agent_id):
        return JsonResponse({
            'agent_id': agent_id,
            'overall_score': 0.85,
            'reliability_score': 0.90,
            'quality_score': 0.82,
            'speed_score': 0.88,
            'total_reviews': 42
        })

class APIDisputeListView(View):
    def get(self, request):
        return JsonResponse({'disputes': [], 'total': 0})

class APIDisputeDetailView(View):
    def get(self, request, dispute_id):
        return JsonResponse({
            'id': dispute_id,
            'status': 'open',
            'reason': 'quality',
            'created_at': timezone.now().isoformat()
        })