# apps/support/api/urls.py
from django.urls import path
from . import views

app_name = 'support_api'

urlpatterns = [
    path('tickets/', views.APITicketListView.as_view(), name='api_tickets'),
    path('tickets/<uuid:ticket_id>/', views.APITicketDetailView.as_view(), name='api_ticket_detail'),
    path('faq/', views.APIFAQView.as_view(), name='api_faq'),
]