# global_work_marketplace/asgi.py

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import re_path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'global_work_marketplace.settings')

# IMPORTANT: import inside safe block (optional best practice)
from apps.execution.consumers import ExecutionConsumer
from apps.dispatch.consumers import DispatchConsumer
from apps.super_admin.consumers import SuperAdminConsumer
from apps.agents.consumers import AgentHeartbeatConsumer
from apps.analytics.consumers import RealtimeAnalyticsConsumer
from apps.accounts.consumers import NotificationConsumer

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,

    "websocket": AuthMiddlewareStack(
        URLRouter([
            re_path(r'ws/execution/(?P<task_id>[^/]+)/$', ExecutionConsumer.as_asgi()),
            re_path(r'ws/dispatch/$', DispatchConsumer.as_asgi()),
            re_path(r'ws/super-admin/dashboard/$', SuperAdminConsumer.as_asgi()),
            re_path(r'ws/agents/(?P<agent_id>[^/]+)/heartbeat/$', AgentHeartbeatConsumer.as_asgi()),
            re_path(r'ws/analytics/realtime/$', RealtimeAnalyticsConsumer.as_asgi()),
            re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
        ])
    ),
})