# apps/accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('verify-email/<uidb64>/<token>/', views.VerifyEmailView.as_view(), name='verify_email'),
    path('resend-verification/', views.ResendVerificationView.as_view(), name='resend_verification'),
    
    # Password Management
    path('password-reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change_password'),
    
    # Profile
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileEditView.as_view(), name='profile_edit'),
    path('profile/delete/', views.ProfileDeleteView.as_view(), name='profile_delete'),
    
    # API Keys
    path('api-keys/', views.APIKeyListView.as_view(), name='api_keys'),
    path('api-keys/create/', views.APIKeyCreateView.as_view(), name='api_key_create'),
    path('api-keys/<uuid:key_id>/revoke/', views.APIKeyRevokeView.as_view(), name='api_key_revoke'),
    
    # Dashboard
    path('dashboard/', views.UserDashboardView.as_view(), name='dashboard'),
    path('settings/', views.UserSettingsView.as_view(), name='settings'),
    path('notifications/', views.NotificationSettingsView.as_view(), name='notification_settings'),
]