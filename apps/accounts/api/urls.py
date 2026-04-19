# apps/accounts/api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('users', views.UserViewSet)
router.register('profiles', views.ProfileViewSet)
router.register('api-keys', views.APIKeyViewSet, basename='api-key')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', views.RegisterView.as_view(), name='api_register'),
    path('auth/login/', views.LoginView.as_view(), name='api_login'),
    path('auth/logout/', views.LogoutView.as_view(), name='api_logout'),
    path('auth/me/', views.MeView.as_view(), name='api_me'),
    path('auth/change-password/', views.ChangePasswordView.as_view(), name='api_change_password'),
]