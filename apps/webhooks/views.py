# apps/webhooks/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
import json
import hmac
import hashlib
import secrets
from .models import WebhookEndpoint, WebhookDelivery

# Available events list
AVAILABLE_EVENTS = [
    'task.created', 'task.completed', 'task.failed',
    'agent.online', 'agent.offline',
    'payment.received', 'payment.sent',
    'verification.approved', 'verification.rejected'
]

class WebhookEndpointListView(LoginRequiredMixin, View):
    template_name = 'webhooks/endpoints.html'
    
    def get(self, request):
        endpoints = WebhookEndpoint.objects.filter(
            owner_id=request.user.id,
            owner_type='user'
        )
        
        context = {
            'endpoints': endpoints,
            'available_events': AVAILABLE_EVENTS,
        }
        return render(request, self.template_name, context)

class WebhookEndpointCreateView(LoginRequiredMixin, View):
    template_name = 'webhooks/create_endpoint.html'
    
    def get(self, request):
        return render(request, self.template_name, {
            'available_events': AVAILABLE_EVENTS
        })
    
    def post(self, request):
        url = request.POST.get('url')
        events = request.POST.getlist('events')
        secret = request.POST.get('secret', '')
        
        if not secret:
            secret = secrets.token_urlsafe(32)
        
        endpoint = WebhookEndpoint.objects.create(
            owner_id=request.user.id,
            owner_type='user',
            url=url,
            secret=secret,
            events=events,
            is_active=True
        )
        
        messages.success(request, f'Webhook endpoint created! Secret: {secret}')
        return redirect('webhooks:detail', endpoint_id=endpoint.id)

class WebhookEndpointDetailView(LoginRequiredMixin, View):
    template_name = 'webhooks/detail.html'
    
    def get(self, request, endpoint_id):
        endpoint = get_object_or_404(
            WebhookEndpoint,
            id=endpoint_id,
            owner_id=request.user.id,
            owner_type='user'
        )
        
        recent_deliveries = WebhookDelivery.objects.filter(endpoint=endpoint).order_by('-created_at')[:20]
        
        context = {
            'endpoint': endpoint,
            'recent_deliveries': recent_deliveries,
            'events': endpoint.events,
        }
        return render(request, self.template_name, context)

class WebhookEndpointEditView(LoginRequiredMixin, View):
    template_name = 'webhooks/edit_endpoint.html'
    
    def get(self, request, endpoint_id):
        endpoint = get_object_or_404(
            WebhookEndpoint,
            id=endpoint_id,
            owner_id=request.user.id,
            owner_type='user'
        )
        
        return render(request, self.template_name, {
            'endpoint': endpoint,
            'available_events': AVAILABLE_EVENTS
        })
    
    def post(self, request, endpoint_id):
        endpoint = get_object_or_404(
            WebhookEndpoint,
            id=endpoint_id,
            owner_id=request.user.id,
            owner_type='user'
        )
        
        endpoint.url = request.POST.get('url')
        endpoint.events = request.POST.getlist('events')
        endpoint.is_active = request.POST.get('is_active') == 'on'
        endpoint.save()
        
        messages.success(request, 'Webhook endpoint updated!')
        return redirect('webhooks:detail', endpoint_id=endpoint.id)

class WebhookEndpointDeleteView(LoginRequiredMixin, View):
    def post(self, request, endpoint_id):
        endpoint = get_object_or_404(
            WebhookEndpoint,
            id=endpoint_id,
            owner_id=request.user.id,
            owner_type='user'
        )
        endpoint.delete()
        
        messages.success(request, 'Webhook endpoint deleted!')
        return redirect('webhooks:endpoints')

class RegenerateSecretView(LoginRequiredMixin, View):
    """Regenerate webhook endpoint secret"""
    
    def post(self, request, endpoint_id):
        endpoint = get_object_or_404(
            WebhookEndpoint,
            id=endpoint_id,
            owner_id=request.user.id,
            owner_type='user'
        )
        
        new_secret = secrets.token_urlsafe(32)
        endpoint.secret = new_secret
        endpoint.save()
        
        messages.success(request, f'Webhook secret regenerated successfully! New secret: {new_secret}')
        return redirect('webhooks:detail', endpoint_id=endpoint.id)

class WebhookTestView(LoginRequiredMixin, View):
    def post(self, request, endpoint_id):
        endpoint = get_object_or_404(
            WebhookEndpoint,
            id=endpoint_id,
            owner_id=request.user.id,
            owner_type='user'
        )
        
        # Send test webhook
        import requests
        
        test_payload = {
            'event': 'test',
            'timestamp': str(timezone.now()),
            'data': {'message': 'Test webhook from Global Work Marketplace'}
        }
        
        signature = hmac.new(
            endpoint.secret.encode(),
            json.dumps(test_payload).encode(),
            hashlib.sha256
        ).hexdigest()
        
        try:
            response = requests.post(
                endpoint.url,
                json=test_payload,
                headers={'X-Webhook-Signature': signature},
                timeout=5
            )
            
            WebhookDelivery.objects.create(
                endpoint=endpoint,
                event_type='test',
                payload=test_payload,
                status='success' if response.status_code == 200 else 'failed',
                response_status=response.status_code,
                response_body=response.text[:500]
            )
            
            if response.status_code == 200:
                messages.success(request, 'Test webhook sent successfully!')
            else:
                messages.warning(request, f'Test webhook received status {response.status_code}')
                
        except Exception as e:
            WebhookDelivery.objects.create(
                endpoint=endpoint,
                event_type='test',
                payload=test_payload,
                status='failed',
                response_body=str(e)
            )
            messages.error(request, f'Failed to send test webhook: {str(e)}')
        
        return redirect('webhooks:detail', endpoint_id=endpoint.id)

class DeliveryLogListView(LoginRequiredMixin, View):
    template_name = 'webhooks/deliveries.html'
    
    def get(self, request):
        endpoints = WebhookEndpoint.objects.filter(
            owner_id=request.user.id,
            owner_type='user'
        )
        
        deliveries = WebhookDelivery.objects.filter(endpoint__in=endpoints).order_by('-created_at')
        
        # Pagination
        from django.core.paginator import Paginator
        paginator = Paginator(deliveries, 50)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'deliveries': page_obj,
            'endpoints': endpoints,
        }
        return render(request, self.template_name, context)

class DeliveryLogDetailView(LoginRequiredMixin, View):
    template_name = 'webhooks/delivery_detail.html'
    
    def get(self, request, delivery_id):
        endpoints = WebhookEndpoint.objects.filter(
            owner_id=request.user.id,
            owner_type='user'
        )
        
        delivery = get_object_or_404(
            WebhookDelivery,
            id=delivery_id,
            endpoint__in=endpoints
        )
        
        context = {
            'delivery': delivery,
            'endpoint': delivery.endpoint,
            'payload_json': json.dumps(delivery.payload, indent=2) if delivery.payload else '{}',
        }
        return render(request, self.template_name, context)

class RetryDeliveryView(LoginRequiredMixin, View):
    """Retry a failed webhook delivery"""
    
    def post(self, request, delivery_id):
        endpoints = WebhookEndpoint.objects.filter(
            owner_id=request.user.id,
            owner_type='user'
        )
        
        original_delivery = get_object_or_404(
            WebhookDelivery,
            id=delivery_id,
            endpoint__in=endpoints
        )
        
        endpoint = original_delivery.endpoint
        
        import requests
        
        signature = hmac.new(
            endpoint.secret.encode(),
            json.dumps(original_delivery.payload).encode(),
            hashlib.sha256
        ).hexdigest()
        
        try:
            response = requests.post(
                endpoint.url,
                json=original_delivery.payload,
                headers={'X-Webhook-Signature': signature},
                timeout=5
            )
            
            # Create new delivery record for retry
            new_delivery = WebhookDelivery.objects.create(
                endpoint=endpoint,
                event_type=original_delivery.event_type,
                payload=original_delivery.payload,
                status='success' if response.status_code == 200 else 'failed',
                response_status=response.status_code,
                response_body=response.text[:500]
            )
            
            if response.status_code == 200:
                messages.success(request, 'Webhook retry sent successfully!')
            else:
                messages.warning(request, f'Webhook retry received status {response.status_code}')
                
        except Exception as e:
            WebhookDelivery.objects.create(
                endpoint=endpoint,
                event_type=original_delivery.event_type,
                payload=original_delivery.payload,
                status='failed',
                response_body=str(e)
            )
            messages.error(request, f'Failed to retry webhook: {str(e)}')
        
        return redirect('webhooks:delivery_detail', delivery_id=original_delivery.id)

@method_decorator(csrf_exempt, name='dispatch')
class WebhookReceiverView(View):
    """Public endpoint for receiving webhooks"""
    
    def post(self, request, endpoint_secret):
        # Verify webhook
        signature = request.headers.get('X-Webhook-Signature')
        payload = request.body
        
        # Find endpoint by secret
        endpoint = WebhookEndpoint.objects.filter(secret=endpoint_secret, is_active=True).first()
        if not endpoint:
            return HttpResponse('Unauthorized', status=401)
        
        # Verify signature
        expected_signature = hmac.new(
            endpoint.secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature or '', expected_signature):
            return HttpResponse('Invalid signature', status=401)
        
        # Process webhook
        try:
            data = json.loads(payload)
            event_type = data.get('event')
        except json.JSONDecodeError:
            return HttpResponse('Invalid JSON', status=400)
        
        # Create delivery record
        WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type=event_type,
            payload=data,
            status='success',
            completed_at=timezone.now()
        )
        
        return JsonResponse({'status': 'received'})

class WebhookStatsView(LoginRequiredMixin, View):
    template_name = 'webhooks/stats.html'
    
    def get(self, request):
        endpoints = WebhookEndpoint.objects.filter(
            owner_id=request.user.id,
            owner_type='user'
        )
        
        deliveries = WebhookDelivery.objects.filter(endpoint__in=endpoints)
        
        total = deliveries.count()
        success_count = deliveries.filter(status='success').count()
        failed_count = deliveries.filter(status='failed').count()
        
        context = {
            'total_deliveries': total,
            'success_count': success_count,
            'failed_count': failed_count,
            'pending_count': deliveries.filter(status='pending').count(),
            'success_rate': (success_count / total * 100) if total > 0 else 0,
            'recent_failures': deliveries.filter(status='failed').order_by('-created_at')[:20],
            'endpoints': endpoints,
        }
        return render(request, self.template_name, context)