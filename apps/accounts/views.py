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
from django.db.models import Q
from django.utils.crypto import get_random_string
from .models import User, Profile, APIKey
from .forms import (
    LoginForm, RegisterForm, ProfileEditForm, 
    ChangePasswordForm, PasswordResetForm, APIKeyForm,
    UserRegisterForm, AdminRegisterForm
)
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes

# Import for API key encryption
from cryptography.fernet import Fernet
import base64
import os


class LoginView(View):
    template_name = 'accounts/login.html'
    
    def get(self, request):
        """Handle GET request - show login form"""
        if request.user.is_authenticated:
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
                request.session.set_expiry(0)
            
            if user.is_staff:
                return redirect('super_admin:dashboard')
            elif role == 'agent':
                return redirect('agents:agent_dashboard')
            else:
                return redirect('accounts:dashboard')
        
        messages.error(request, 'Invalid email or password')
        return redirect('accounts:login')


class RegisterView(View):
    template_name = 'accounts/register.html'
    
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:dashboard')
        return render(request, self.template_name)
    
    def _get_encryption_key(self):
        """Get or create a consistent encryption key for API keys"""
        # Use Django's SECRET_KEY as base for encryption
        from django.conf import settings
        key = settings.SECRET_KEY[:32].encode()
        # Ensure key is 32 bytes for Fernet
        key = key.ljust(32, b'_')
        # Fernet requires base64 encoded 32-byte key
        return base64.urlsafe_b64encode(key)
    
    def _encrypt_api_key(self, api_key):
        """Encrypt API key for secure storage"""
        if not api_key:
            return None
        
        try:
            encryption_key = self._get_encryption_key()
            cipher = Fernet(encryption_key)
            encrypted = cipher.encrypt(api_key.encode())
            return encrypted
        except Exception as e:
            # Log error but don't fail registration
            print(f"API key encryption failed: {e}")
            return None
    
    def post(self, request):
        role = request.POST.get('role', 'user')
        
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        agree_terms = request.POST.get('agree_terms')
        
        # Validation
        errors = []
        
        if not agree_terms:
            errors.append('You must agree to the Terms of Service')
        
        if not password1 or not password2:
            errors.append('Password is required')
        elif password1 != password2:
            errors.append('Passwords do not match')
        elif len(password1) < 8:
            errors.append('Password must be at least 8 characters')
        
        if not email:
            errors.append('Email is required')
        elif User.objects.filter(email=email).exists():
            errors.append('Email already registered')
        
        if not username:
            errors.append('Username is required')
        elif User.objects.filter(username=username).exists():
            errors.append('Username already taken')
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, self.template_name)
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name
            )
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return render(request, self.template_name)
        
        # Create profile
        Profile.objects.get_or_create(user=user)
        
        # Handle agent registration
        if role == 'agent':
            from apps.agents.models import Agent
            
            agent_name = request.POST.get('agent_name', username)
            agent_type = request.POST.get('agent_type', 'human')
            hourly_rate = request.POST.get('hourly_rate', 10000)
            agent_description = request.POST.get('agent_description', '')
            capabilities = request.POST.getlist('capabilities')
            api_endpoint = request.POST.get('api_endpoint', '')
            api_key = request.POST.get('api_key', '')
            
            # Encrypt the API key if provided
            encrypted_api_key = self._encrypt_api_key(api_key) if api_key else None
            
            Agent.objects.create(
                user=user,
                name=agent_name,
                agent_type=agent_type,
                hourly_rate_sats=int(hourly_rate),
                description=agent_description,
                capabilities=capabilities,
                api_endpoint=api_endpoint,
                api_key_encrypted=encrypted_api_key,
                is_active=True
            )
        
        # Login user
        login(request, user)
        
        messages.success(request, f'Welcome {first_name or username}! Your account has been created.')
        
        if role == 'agent':
            return redirect('agents:agent_dashboard')
        else:
            return redirect('accounts:dashboard')


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
        from apps.execution.models import Execution
        from apps.dispatch.models import DispatchQueue, Assignment
        from apps.verification.models import Verification
        
        user = request.user
        
        # Get user's agent profile
        user_agent = Agent.objects.filter(user=user).first()
        
        # Initialize task queries
        tasks_as_creator = Task.objects.none()
        tasks_as_agent = Task.objects.none()
        tasks_as_reviewer = Task.objects.none()
        
        # Tasks where user is the matched agent
        if user_agent:
            tasks_as_agent = Task.objects.filter(matched_agent=user_agent)
        
        # Tasks from dispatch queue assigned to user's agent
        if user_agent:
            dispatch_assignments = DispatchQueue.objects.filter(assigned_agent=user_agent)
            tasks_from_dispatch = Task.objects.filter(dispatch_queue__in=dispatch_assignments)
            tasks_as_agent = tasks_as_agent | tasks_from_dispatch
        
        # Tasks from assignments
        if user_agent:
            assignments = Assignment.objects.filter(agent=user_agent)
            tasks_from_assignments = Task.objects.filter(assignment__in=assignments)
            tasks_as_agent = tasks_as_agent | tasks_from_assignments
        
        # Tasks where user is the executor via execution
        if user_agent:
            executions = Execution.objects.filter(agent=user_agent)
            tasks_from_executions = Task.objects.filter(execution__in=executions)
            tasks_as_agent = tasks_as_agent | tasks_from_executions
        
        # Tasks where user is the verifier
        verifications = Verification.objects.filter(verified_by=user_agent)
        tasks_as_reviewer = Task.objects.filter(verification__in=verifications)
        
        # Combine all unique tasks
        all_user_tasks = (tasks_as_agent | tasks_as_reviewer).distinct()
        
        # Get recent transactions
        recent_transactions = Transaction.objects.filter(
            Q(from_wallet__owner_id=user.id) |
            Q(to_wallet__owner_id=user.id)
        ).order_by('-created_at')[:10]
        
        # Get user's agents
        user_agents = Agent.objects.filter(user=user)
        
        # Calculate statistics
        total_tasks = all_user_tasks.count()
        completed_tasks = all_user_tasks.filter(state='completed').count()
        pending_tasks = all_user_tasks.filter(state='pending').count()
        in_progress_tasks = all_user_tasks.filter(state='running').count()
        failed_tasks = all_user_tasks.filter(state='failed').count()
        cancelled_tasks = all_user_tasks.filter(state='cancelled').count()
        
        # Calculate success rate
        success_rate = 0
        if completed_tasks + failed_tasks > 0:
            success_rate = (completed_tasks / (completed_tasks + failed_tasks)) * 100
        
        # Calculate earnings and spending
        total_earned = user.total_earned
        total_spent = user.total_spent
        wallet_balance = user.wallet_balance
        
        # Get recent tasks with details
        recent_tasks = all_user_tasks.select_related(
            'matched_agent',
            'execution',
            'verification'
        ).order_by('-created_at')[:10]
        
        # Get pending verifications
        pending_verifications = Verification.objects.filter(
            task__in=all_user_tasks,
            status='pending'
        ).count()
        
        # Get active disputes
        from apps.verification.models import Dispute
        active_disputes = Dispute.objects.filter(
            Q(task__in=all_user_tasks) | Q(raised_by=user),
            status__in=['open', 'investigating']
        ).count()
        
        # Get agent performance metrics if user is an agent
        agent_performance = {}
        if user_agent:
            agent_performance = {
                'total_tasks': user_agent.total_tasks_completed,
                'success_rate': user_agent.success_rate,
                'average_rating': user_agent.average_rating,
                'total_earned': user_agent.total_earned,
                'hourly_rate': user_agent.hourly_rate_sats,
                'trust_score': user_agent.trust_score,
                'response_time_avg': user_agent.average_response_time,
                'completion_time_avg': user_agent.average_completion_time,
            }
        
        # Get platform statistics
        platform_stats = {
            'total_agents': Agent.objects.filter(is_active=True).count(),
            'total_tasks_platform': Task.objects.count(),
            'completed_tasks_platform': Task.objects.filter(state='completed').count(),
            'active_tasks': Task.objects.filter(state__in=['open', 'assigned', 'running']).count(),
        }
        
        context = {
            # User info
            'user': user,
            'profile': user.profile,
            'user_agent': user_agent,
            'has_agent': user_agent is not None,
            'user_agents': user_agents,
            
            # Task statistics
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'pending_tasks': pending_tasks,
            'in_progress_tasks': in_progress_tasks,
            'failed_tasks': failed_tasks,
            'cancelled_tasks': cancelled_tasks,
            'success_rate': success_rate,
            
            # Financial metrics
            'total_earned': total_earned,
            'total_spent': total_spent,
            'wallet_balance': wallet_balance,
            
            # Recent data
            'recent_tasks': recent_tasks,
            'recent_transactions': recent_transactions,
            
            # Verification and disputes
            'pending_verifications': pending_verifications,
            'active_disputes': active_disputes,
            
            # Agent performance (if applicable)
            'agent_performance': agent_performance,
            
            # Platform stats
            'platform_stats': platform_stats,
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
        request.user.email_notifications = request.POST.get('email_notifications') == 'on'
        request.user.save()
        messages.success(request, 'Settings updated!')
        return redirect('accounts:settings')


class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.info(request, 'You have been logged out')
        return redirect('accounts:login')


class VerifyEmailView(View):
    """Email verification view"""
    template_name = 'accounts/verify_email.html'
    
    def get(self, request, uidb64, token):
        try:
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
        user = request.user
        
        if user.is_verified:
            messages.info(request, 'Email already verified')
            return redirect('accounts:dashboard')
        
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        
        verification_link = request.build_absolute_uri(
            reverse_lazy('accounts:verify_email', kwargs={'uidb64': uid, 'token': token})
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
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                reset_link = request.build_absolute_uri(
                    reverse_lazy('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
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
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
            
            if default_token_generator.check_token(user, token):
                return render(request, self.template_name, {'uidb64': uidb64, 'token': token, 'validlink': True})
            else:
                return render(request, self.template_name, {'validlink': False})
        except Exception:
            return render(request, self.template_name, {'validlink': False})
    
    def post(self, request, uidb64, token):
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