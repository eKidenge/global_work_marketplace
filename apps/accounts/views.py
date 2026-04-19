# apps/accounts/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from .models import User, Profile, APIKey
from .forms import (
    LoginForm, RegisterForm, ProfileEditForm, 
    ChangePasswordForm, PasswordResetForm, APIKeyForm,
    UserRegisterForm, AdminRegisterForm  # ADD THESE TWO
)
# Add these to your existing imports
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
# apps/accounts/views.py - Add/modify this method

class LoginView(View):
    template_name = 'accounts/login.html'
    
    def get(self, request):
        """Handle GET request - show login form"""
        if request.user.is_authenticated:
            # If already logged in, redirect based on role
            if request.user.is_staff:
                return redirect('super_admin:dashboard')
            return redirect('accounts:dashboard')
        return render(request, self.template_name)
    
    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'user')
        remember = request.POST.get('remember')
        
        user = authenticate(request, username=email, password=password)
        
        if user:
            # Check role-based access
            if role == 'admin' and not user.is_staff:
                messages.error(request, 'You do not have admin access')
                return redirect('accounts:login')
            
            if role == 'agent':
                from apps.agents.models import Agent
                has_agent = Agent.objects.filter(user=user).exists()
                if not has_agent:
                    messages.error(request, 'No agent profile found. Please register as an agent first.')
                    return redirect('accounts:register')
            
            login(request, user)
            
            if not remember:
                request.session.set_expiry(0)  # Session expires on browser close
            
            # Redirect based on role
            if user.is_staff:
                return redirect('super_admin:dashboard')
            elif role == 'agent':
                return redirect('agents:agent_dashboard')
            else:
                return redirect('accounts:dashboard')
        
        messages.error(request, 'Invalid email or password')
        return redirect('accounts:login')

# apps/accounts/views.py - Add this method to your RegisterView

class RegisterView(View):
    template_name = 'accounts/register.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return render(request, self.template_name)
    
    def post(self, request):
        role = request.POST.get('role', 'user')
        
        if role == 'user':
            return self.register_user(request)
        elif role == 'agent':
            return self.register_agent(request)
        elif role == 'admin':
            return self.register_admin(request)
        else:
            messages.error(request, 'Invalid registration type')
            return redirect('accounts:register')
    
    def register_user(self, request):
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('accounts:dashboard')
        return render(request, self.template_name, {'form': form, 'errors': form.errors})
    
    def register_agent(self, request):
        from apps.agents.models import Agent
        
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Create agent profile
            agent = Agent.objects.create(
                user=user,
                name=request.POST.get('agent_name', user.username),
                agent_type=request.POST.get('agent_type', 'ai'),
                capabilities=request.POST.getlist('capabilities'),
                hourly_rate_sats=int(request.POST.get('hourly_rate', 10000)),
                description=request.POST.get('agent_description', ''),
                api_endpoint=request.POST.get('api_endpoint', ''),
                is_active=True
            )
            
            login(request, user)
            messages.success(request, f'Agent "{agent.name}" registered successfully!')
            return redirect('agents:agent_dashboard')
        
        return render(request, self.template_name, {'form': form, 'errors': form.errors})
    
    def register_admin(self, request):
        admin_code = request.POST.get('admin_code')
        
        # Verify admin code (you should store this securely)
        if admin_code != 'SUPER_SECRET_ADMIN_CODE_2024':
            messages.error(request, 'Invalid admin registration code')
            return redirect('accounts:register')
        
        form = AdminRegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_staff = True
            user.save()
            
            # Create admin profile
            from apps.super_admin.models import AdminUser
            AdminUser.objects.create(
                user=user,
                role=request.POST.get('admin_role', 'admin')
            )
            
            login(request, user)
            messages.success(request, 'Admin account created!')
            return redirect('super_admin:dashboard')
        
        return render(request, self.template_name, {'form': form, 'errors': form.errors})

class ProfileView(LoginRequiredMixin, View):
    template_name = 'accounts/profile.html'
    
    def get(self, request):
        context = {
            'user': request.user,
            'profile': request.user.profile,
            'recent_activity': self.get_recent_activity(request.user),
        }
        return render(request, self.template_name, context)
    
    def get_recent_activity(self, user):
        from apps.tasks.models import Task
        from apps.payments.models import Transaction
        
        tasks = Task.objects.filter(created_by=user).order_by('-created_at')[:5]
        transactions = Transaction.objects.filter(
            from_wallet__owner_id=user.id
        ).order_by('-created_at')[:5]
        
        return {'tasks': tasks, 'transactions': transactions}

class ProfileEditView(LoginRequiredMixin, View):
    template_name = 'accounts/edit_profile.html'
    
    def get(self, request):
        form = ProfileEditForm(instance=request.user.profile)
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
        return render(request, self.template_name, {'form': form})

class ChangePasswordView(LoginRequiredMixin, View):
    template_name = 'accounts/change_password.html'
    
    def get(self, request):
        return render(request, self.template_name, {'form': ChangePasswordForm()})
    
    def post(self, request):
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            if request.user.check_password(form.cleaned_data['old_password']):
                request.user.set_password(form.cleaned_data['new_password'])
                request.user.save()
                messages.success(request, 'Password changed successfully!')
                return redirect('accounts:login')
            messages.error(request, 'Current password is incorrect')
        return render(request, self.template_name, {'form': form})

class ForgotPasswordView(View):
    template_name = 'accounts/forgot_password.html'
    
    def get(self, request):
        return render(request, self.template_name, {'form': PasswordResetForm()})
    
    def post(self, request):
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email=email).first()
            if user:
                token = get_random_string(64)
                # Store token in cache or database
                reset_link = request.build_absolute_uri(
                    reverse_lazy('accounts:reset_password', kwargs={'token': token})
                )
                send_mail(
                    'Password Reset Request',
                    f'Click here to reset your password: {reset_link}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                )
                messages.success(request, 'Password reset link sent to your email!')
                return redirect('accounts:login')
            messages.error(request, 'No user found with this email')
        return render(request, self.template_name, {'form': form})

class UserDashboardView(LoginRequiredMixin, View):
    template_name = 'accounts/dashboard.html'
    
    def get(self, request):
        from apps.tasks.models import Task
        from apps.agents.models import Agent
        from apps.payments.models import Transaction
        
        context = {
            'user': request.user,
            'total_tasks': Task.objects.filter(created_by=request.user).count(),
            'completed_tasks': Task.objects.filter(created_by=request.user, state='completed').count(),
            'total_spent': request.user.total_spent,
            'recent_tasks': Task.objects.filter(created_by=request.user).order_by('-created_at')[:5],
            'agents': Agent.objects.filter(user=request.user),
            'recent_transactions': Transaction.objects.filter(
                from_wallet__owner_id=request.user.id
            ).order_by('-created_at')[:5],
        }
        return render(request, self.template_name, context)

class APIKeyListView(LoginRequiredMixin, View):
    template_name = 'accounts/api_keys.html'
    
    def get(self, request):
        api_keys = APIKey.objects.filter(user=request.user)
        return render(request, self.template_name, {'api_keys': api_keys})
    
    def post(self, request):
        form = APIKeyForm(request.POST)
        if form.is_valid():
            api_key = APIKey.objects.create(
                user=request.user,
                name=form.cleaned_data['name'],
                key=get_random_string(32)
            )
            messages.success(request, f'API Key created: {api_key.key}')
        return redirect('accounts:api_keys')

class UserSettingsView(LoginRequiredMixin, View):
    template_name = 'accounts/settings.html'
    
    def get(self, request):
        return render(request, self.template_name, {'user': request.user})
    
    def post(self, request):
        # Handle settings updates
        request.user.email_notifications = request.POST.get('email_notifications') == 'on'
        request.user.save()
        messages.success(request, 'Settings updated!')
        return redirect('accounts:settings')

class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, 'You have been logged out')
        return redirect('accounts:login')

# Add these missing views to your apps/accounts/views.py

class VerifyEmailView(View):
    """Email verification view"""
    template_name = 'accounts/verify_email.html'
    
    def get(self, request, uidb64, token):
        try:
            from django.utils.http import urlsafe_base64_decode
            from django.contrib.auth.tokens import default_token_generator
            
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, token):
                user.is_verified = True
                user.verified_at = timezone.now()
                user.save()
                messages.success(request, 'Email verified successfully!')
                return redirect('accounts:login')
            else:
                messages.error(request, 'Invalid verification link')
                return redirect('accounts:login')
                
        except Exception:
            messages.error(request, 'Verification failed')
            return redirect('accounts:login')


class ResendVerificationView(LoginRequiredMixin, View):
    """Resend verification email"""
    
    def post(self, request):
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        from django.contrib.auth.tokens import default_token_generator
        from django.urls import reverse
        
        user = request.user
        
        if user.is_verified:
            messages.info(request, 'Email already verified')
            return redirect('accounts:dashboard')
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        verification_link = request.build_absolute_uri(
            reverse('accounts:verify_email', kwargs={'uidb64': uid, 'token': token})
        )
        
        send_mail(
            'Verify Your Email',
            f'Click here to verify your email: {verification_link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
        )
        
        messages.success(request, 'Verification email sent!')
        return redirect('accounts:dashboard')


class PasswordResetView(View):
    template_name = 'accounts/password_reset.html'
    
    def get(self, request):
        return render(request, self.template_name, {'form': PasswordResetForm()})
    
    def post(self, request):
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            user = User.objects.filter(email=email).first()
            if user:
                from django.utils.http import urlsafe_base64_encode
                from django.utils.encoding import force_bytes
                from django.contrib.auth.tokens import default_token_generator
                from django.urls import reverse
                
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                reset_link = request.build_absolute_uri(
                    reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
                )
                
                send_mail(
                    'Password Reset Request',
                    f'Click here to reset your password: {reset_link}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                )
                messages.success(request, 'Password reset link sent to your email!')
                return redirect('accounts:login')
            messages.error(request, 'No user found with this email')
        return render(request, self.template_name, {'form': form})


class PasswordResetConfirmView(View):
    template_name = 'accounts/password_reset_confirm.html'
    
    def get(self, request, uidb64, token):
        try:
            from django.utils.http import urlsafe_base64_decode
            from django.contrib.auth.tokens import default_token_generator
            
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, token):
                return render(request, self.template_name, {'uidb64': uidb64, 'token': token, 'validlink': True})
            else:
                return render(request, self.template_name, {'validlink': False})
        except Exception:
            return render(request, self.template_name, {'validlink': False})
    
    def post(self, request, uidb64, token):
        from django.utils.http import urlsafe_base64_decode
        from django.contrib.auth.tokens import default_token_generator
        
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        if password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, self.template_name, {'uidb64': uidb64, 'token': token, 'validlink': True})
        
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, token):
                user.set_password(password)
                user.save()
                messages.success(request, 'Password reset successful! Please login.')
                return redirect('accounts:login')
            else:
                messages.error(request, 'Invalid reset link')
                return redirect('accounts:login')
        except Exception:
            messages.error(request, 'Invalid reset link')
            return redirect('accounts:login')


class PasswordResetDoneView(View):
    template_name = 'accounts/password_reset_done.html'
    
    def get(self, request):
        return render(request, self.template_name)


class PasswordResetCompleteView(View):
    template_name = 'accounts/password_reset_complete.html'
    
    def get(self, request):
        return render(request, self.template_name)

# Add this class to your apps/accounts/views.py

class ProfileDeleteView(LoginRequiredMixin, View):
    """Delete user profile/view"""
    
    def post(self, request):
        user = request.user
        logout(request)
        user.delete()
        messages.success(request, 'Your account has been deleted successfully.')
        return redirect('accounts:login')
    
class APIKeyCreateView(LoginRequiredMixin, View):
    def post(self, request):
        name = request.POST.get('name')
        api_key = APIKey.objects.create(
            user=request.user,
            name=name,
            key=get_random_string(32)
        )
        messages.success(request, f'API Key created: {api_key.key}')
        return redirect('accounts:api_keys')


class APIKeyRevokeView(LoginRequiredMixin, View):
    def post(self, request, key_id):
        api_key = get_object_or_404(APIKey, id=key_id, user=request.user)
        api_key.delete()
        messages.success(request, 'API Key revoked')
        return redirect('accounts:api_keys')

class NotificationSettingsView(LoginRequiredMixin, View):
    template_name = 'accounts/notification_settings.html'
    
    def get(self, request):
        return render(request, self.template_name, {'user': request.user})
    
    def post(self, request):
        user = request.user
        user.email_notifications = request.POST.get('email_notifications') == 'on'
        user.push_notifications = request.POST.get('push_notifications') == 'on'
        user.save()
        messages.success(request, 'Notification settings updated!')
        return redirect('accounts:notification_settings')