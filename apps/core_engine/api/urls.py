# apps/core_engine/api/urls.py
from django.urls import path
from . import views

app_name = 'core_engine_api'

urlpatterns = [
    path('route/', views.APIRouteTaskView.as_view(), name='api_route'),
    path('price/', views.APIPriceTaskView.as_view(), name='api_price'),
    path('risk/', views.APIRiskAssessmentView.as_view(), name='api_risk'),
    path('optimize/', views.APIOptimizeView.as_view(), name='api_optimize'),
]