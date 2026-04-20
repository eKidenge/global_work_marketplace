# global_work_marketplace/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from apps.common.views import LandingPageView  # Add this import
from django.views.generic import TemplateView  # Add this import for about page

urlpatterns = [
    # Landing page (public homepage) - Changed from redirect to landing page
    path('', LandingPageView.as_view(), name='landing'),
    
    # About page
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),
    
    # Super Admin Panel (Main admin interface)
    path('super-admin/', include('apps.super_admin.urls')),
    
    # Django's built-in admin (optional, can be disabled in production)
    path('django-admin/', admin.site.urls),
    
    # API endpoints
    path('api/accounts/', include('apps.accounts.api.urls')),
    path('api/agents/', include('apps.agents.api.urls')),
    path('api/tasks/', include('apps.tasks.api.urls')),
    path('api/dispatch/', include('apps.dispatch.api.urls')),
    path('api/execution/', include('apps.execution.api.urls')),
    path('api/payments/', include('apps.payments.api.urls')),
    path('api/verification/', include('apps.verification.api.urls')),
    path('api/webhooks/', include('apps.webhooks.api.urls')),
    path('api/analytics/', include('apps.analytics.api.urls')),
    
    # Frontend URLs (public facing)
    path('accounts/', include('apps.accounts.urls')),
    path('agents/', include('apps.agents.urls')),
    path('tasks/', include('apps.tasks.urls')),
    path('dispatch/', include('apps.dispatch.urls')),
    path('execution/', include('apps.execution.urls')),
    path('payments/', include('apps.payments.urls')),
    path('verification/', include('apps.verification.urls')),
    path('support/', include('apps.support.urls')),
    path('webhooks/', include('apps.webhooks.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)