# apps/support/api/views.py
from django.views import View
from django.http import JsonResponse
import uuid

class APITicketListView(View):
    def get(self, request):
        return JsonResponse({'tickets': [], 'total': 0})
    
    def post(self, request):
        return JsonResponse({'status': 'created', 'ticket_id': str(uuid.uuid4())})

class APITicketDetailView(View):
    def get(self, request, ticket_id):
        return JsonResponse({'id': ticket_id, 'status': 'open', 'messages': []})

class APIFAQView(View):
    def get(self, request):
        return JsonResponse({'faqs': []})