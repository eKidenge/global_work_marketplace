import os
from celery import Celery

# Set Django settings module
os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    'global_work_marketplace.settings'
)

app = Celery('global_work_marketplace')

# Load settings from Django settings.py (CELERY_*)
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all apps
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')