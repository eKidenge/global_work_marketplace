# apps/webhooks/api/views.py
from django.views import View
from django.http import JsonResponse

class APIWebhookEndpointsView(View):
    def get(self, request):
        return JsonResponse({'endpoints': [], 'total': 0})
    
    def post(self, request):
        return JsonResponse({'status': 'created', 'endpoint_id': 'new-id'})

class APIWebhookDeliveriesView(View):
    def get(self, request):
        return JsonResponse({'deliveries': [], 'total': 0})