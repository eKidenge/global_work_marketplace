# apps/verification/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from django.utils import timezone
from .models import Verification, Reputation, Dispute
from apps.tasks.models import Task

class VerificationDashboardView(View):
    template_name = 'verification/dashboard.html'
    
    def get(self, request):
        context = {
            'pending_verifications': Verification.objects.filter(status='pending').count(),
            'approved_today': Verification.objects.filter(
                status='approved',
                verified_at__date=timezone.now().date()
            ).count(),
            'rejected_today': Verification.objects.filter(
                status='rejected',
                verified_at__date=timezone.now().date()
            ).count(),
            'avg_quality_score': Verification.objects.filter(quality_score__gt=0).aggregate(Avg('quality_score'))['quality_score__avg'] or 0,
            'recent_verifications': Verification.objects.select_related('task').order_by('-created_at')[:20],
        }
        return render(request, self.template_name, context)

class VerificationQueueView(View):
    template_name = 'verification/queue.html'
    
    def get(self, request):
        verifications = Verification.objects.filter(status='pending').select_related('task')
        
        context = {
            'verifications': verifications[:50],
            'queue_size': verifications.count(),
        }
        return render(request, self.template_name, context)

class VerifyTaskView(LoginRequiredMixin, View):
    template_name = 'verification/verify_task.html'
    
    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, state='verifying')
        verification, created = Verification.objects.get_or_create(task=task)
        
        context = {
            'task': task,
            'verification': verification,
            'execution': task.execution if hasattr(task, 'execution') else None,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id, state='verifying')
        verification = Verification.objects.get(task=task)
        
        action = request.POST.get('action')
        
        if action == 'approve':
            verification.status = 'approved'
            verification.verified_by = request.user
            verification.verified_at = timezone.now()
            verification.quality_score = float(request.POST.get('quality_score', 0.8))
            verification.verifier_notes = request.POST.get('notes', '')
            verification.save()
            
            # Complete task
            task.state = Task.TaskState.COMPLETED
            task.save()
            
            # Update agent reputation
            if task.matched_agent:
                reputation, _ = Reputation.objects.get_or_create(agent=task.matched_agent)
                self.update_reputation(reputation, verification.quality_score)
            
            messages.success(request, 'Task verified and approved!')
            
        elif action == 'reject':
            verification.status = 'rejected'
            verification.verified_by = request.user
            verification.verified_at = timezone.now()
            verification.verifier_notes = request.POST.get('notes', '')
            verification.save()
            
            # Fail task
            task.state = Task.TaskState.FAILED
            task.save()
            
            messages.warning(request, 'Task rejected.')
        
        return redirect('verification:queue')
    
    def update_reputation(self, reputation, quality_score):
        # Update reputation based on verification
        reputation.quality_score = (reputation.quality_score * reputation.total_reviews + quality_score) / (reputation.total_reviews + 1)
        reputation.total_reviews += 1
        if quality_score >= 0.7:
            reputation.positive_reviews += 1
        else:
            reputation.negative_reviews += 1
        reputation.overall_score = (
            reputation.reliability_score * 0.3 +
            reputation.quality_score * 0.4 +
            reputation.speed_score * 0.2 +
            reputation.communication_score * 0.1
        )
        reputation.save()

class ReputationView(View):
    template_name = 'verification/reputation.html'
    
    def get(self, request, agent_id):
        from apps.agents.models import Agent
        
        agent = get_object_or_404(Agent, id=agent_id)
        reputation, _ = Reputation.objects.get_or_create(agent=agent)
        
        # Get recent reviews
        recent_verifications = Verification.objects.filter(
            task__matched_agent=agent,
            status='approved'
        ).order_by('-verified_at')[:10]
        
        context = {
            'agent': agent,
            'reputation': reputation,
            'recent_verifications': recent_verifications,
        }
        return render(request, self.template_name, context)

class ReputationLeaderboardView(View):
    template_name = 'verification/leaderboard.html'
    
    def get(self, request):
        top_agents = Reputation.objects.select_related('agent').filter(
            total_reviews__gt=0
        ).order_by('-overall_score')[:50]
        
        context = {
            'top_agents': top_agents,
            'categories': {
                'ai': top_agents.filter(agent__agent_type='ai')[:10],
                'human': top_agents.filter(agent__agent_type='human')[:10],
            }
        }
        return render(request, self.template_name, context)

class DisputeListView(LoginRequiredMixin, View):
    template_name = 'verification/disputes.html'
    
    def get(self, request):
        disputes = Dispute.objects.filter(
            Q(raised_by=request.user) | Q(task__created_by=request.user) | Q(task__matched_agent__user=request.user)
        ).select_related('task', 'raised_by')
        
        context = {
            'disputes': disputes,
            'status_counts': {
                'open': disputes.filter(status='open').count(),
                'investigating': disputes.filter(status='investigating').count(),
                'resolved': disputes.filter(status='resolved').count(),
            },
        }
        return render(request, self.template_name, context)

class CreateDisputeView(LoginRequiredMixin, View):
    template_name = 'verification/create_dispute.html'
    
    def get(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        
        context = {
            'task': task,
            'reasons': Dispute.DISPUTE_REASONS,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, task_id):
        task = get_object_or_404(Task, id=task_id)
        
        dispute = Dispute.objects.create(
            task=task,
            raised_by=request.user,
            reason=request.POST.get('reason'),
            description=request.POST.get('description'),
            evidence=request.POST.getlist('evidence'),
        )
        
        messages.info(request, 'Dispute raised. An admin will review it shortly.')
        return redirect('verification:dispute_detail', dispute_id=dispute.id)

class DisputeDetailView(LoginRequiredMixin, View):
    template_name = 'verification/dispute_detail.html'
    
    def get(self, request, dispute_id):
        dispute = get_object_or_404(Dispute, id=dispute_id)
        
        context = {
            'dispute': dispute,
            'task': dispute.task,
            'raised_by': dispute.raised_by,
            'can_respond': dispute.status in ['open', 'investigating'],
        }
        return render(request, self.template_name, context)

class RespondToDisputeView(LoginRequiredMixin, View):
    def post(self, request, dispute_id):
        dispute = get_object_or_404(Dispute, id=dispute_id)
        
        # Check if user is involved
        is_involved = (
            request.user == dispute.raised_by or
            request.user == dispute.task.created_by or
            (dispute.task.matched_agent and request.user == dispute.task.matched_agent.user)
        )
        
        if is_involved and dispute.status in ['open', 'investigating']:
            response = request.POST.get('response')
            # Add response to evidence
            evidence = dispute.evidence or []
            evidence.append({
                'user': request.user.email,
                'response': response,
                'timestamp': str(timezone.now())
            })
            dispute.evidence = evidence
            dispute.save()
            
            messages.success(request, 'Response added to dispute')
        
        return redirect('verification:dispute_detail', dispute_id=dispute.id)

class VerificationReviewView(LoginRequiredMixin, View):
    """Review a specific verification"""
    template_name = 'verification/review.html'
    
    def get(self, request, verification_id):
        verification = get_object_or_404(Verification, id=verification_id)
        
        # Check permission (only admins or assigned reviewers)
        if not request.user.is_staff and request.user != getattr(verification, 'reviewer', None):
            messages.error(request, 'You do not have permission to review this verification')
            return redirect('verification:dashboard')
        
        context = {
            'verification': verification,
            'task': verification.task,
            'agent': getattr(verification.task, 'matched_agent', None),
            'submissions': getattr(verification, 'submissions', []),
        }
        return render(request, self.template_name, context)
    
    def post(self, request, verification_id):
        verification = get_object_or_404(Verification, id=verification_id)
        
        action = request.POST.get('action')
        comments = request.POST.get('comments', '')
        
        if action == 'approve':
            verification.status = 'approved'
            verification.verified_at = timezone.now()
            verification.verifier_notes = comments
            verification.save()
            
            # Update task status
            task = verification.task
            task.state = Task.TaskState.COMPLETED
            task.save()
            
            # Update reputation
            if hasattr(task, 'matched_agent') and task.matched_agent:
                reputation, _ = Reputation.objects.get_or_create(agent=task.matched_agent)
                reputation.quality_score = (reputation.quality_score * reputation.total_reviews + 0.8) / (reputation.total_reviews + 1)
                reputation.total_reviews += 1
                reputation.positive_reviews += 1
                reputation.save()
            
            messages.success(request, 'Verification approved')
            
        elif action == 'reject':
            verification.status = 'rejected'
            verification.verified_at = timezone.now()
            verification.verifier_notes = comments
            verification.save()
            
            # Update task status
            task = verification.task
            task.state = Task.TaskState.FAILED
            task.save()
            
            messages.warning(request, 'Verification rejected')
            
        elif action == 'flag':
            verification.status = 'flagged'
            verification.verified_at = timezone.now()
            verification.verifier_notes = comments
            verification.save()
            
            messages.info(request, 'Verification flagged for further review')
        
        return redirect('verification:queue')

class VerificationResultView(LoginRequiredMixin, View):
    """View verification results"""
    template_name = 'verification/results.html'
    
    def get(self, request, verification_id):
        verification = get_object_or_404(Verification, id=verification_id)
        
        context = {
            'verification': verification,
            'consensus_score': getattr(verification, 'quality_score', 0),
            'task': verification.task,
            'agent': getattr(verification.task, 'matched_agent', None),
            'results': {
                'quality_score': verification.quality_score,
                'status': verification.status,
                'verified_at': verification.verified_at,
                'verifier_notes': verification.verifier_notes,
            },
        }
        return render(request, self.template_name, context)

class EscalateDisputeView(LoginRequiredMixin, View):
    """Escalate a dispute to higher authority"""
    
    def post(self, request, dispute_id):
        dispute = get_object_or_404(Dispute, id=dispute_id)
        
        # Check if user is involved in the dispute
        is_involved = (
            request.user == dispute.raised_by or
            request.user == dispute.task.created_by or
            (dispute.task.matched_agent and request.user == dispute.task.matched_agent.user) or
            request.user.is_staff
        )
        
        if not is_involved:
            messages.error(request, 'You do not have permission to escalate this dispute')
            return redirect('verification:dispute_detail', dispute_id=dispute.id)
        
        if dispute.status in ['open', 'investigating']:
            dispute.status = 'escalated'
            dispute.escalated_at = timezone.now()
            dispute.escalated_by = request.user
            dispute.escalation_reason = request.POST.get('reason', 'No reason provided')
            dispute.save()
            
            messages.warning(request, 'Dispute has been escalated to admin review')
        else:
            messages.error(request, f'Cannot escalate dispute with status: {dispute.status}')
        
        return redirect('verification:dispute_detail', dispute_id=dispute.id)

class AppealView(LoginRequiredMixin, View):
    """Appeal a verification decision"""
    template_name = 'verification/appeal.html'
    
    def get(self, request, verification_id):
        verification = get_object_or_404(Verification, id=verification_id)
        
        # Check if user is the task creator or agent
        is_related = (
            request.user == verification.task.created_by or
            (verification.task.matched_agent and request.user == verification.task.matched_agent.user)
        )
        
        if not is_related:
            messages.error(request, 'You do not have permission to appeal this verification')
            return redirect('verification:dashboard')
        
        context = {
            'verification': verification,
            'task': verification.task,
        }
        return render(request, self.template_name, context)
    
    def post(self, request, verification_id):
        verification = get_object_or_404(Verification, id=verification_id)
        
        verification.appeal_reason = request.POST.get('reason', '')
        verification.appeal_status = 'pending'
        verification.appealed_at = timezone.now()
        verification.appealed_by = request.user
        verification.save()
        
        messages.info(request, 'Appeal submitted for review')
        return redirect('verification:queue')

class AppealReviewView(LoginRequiredMixin, View):
    """Review an appeal (admin only)"""
    
    def post(self, request, appeal_id):
        if not request.user.is_staff:
            messages.error(request, 'Only admins can review appeals')
            return redirect('verification:dashboard')
        
        verification = get_object_or_404(Verification, id=appeal_id)
        
        decision = request.POST.get('decision')
        notes = request.POST.get('notes', '')
        
        if decision == 'approve':
            verification.status = 'approved'
            verification.verified_at = timezone.now()
            verification.verifier_notes = notes
            verification.appeal_status = 'approved'
            verification.save()
            
            # Update task
            task = verification.task
            task.state = Task.TaskState.COMPLETED
            task.save()
            
            messages.success(request, 'Appeal approved, verification updated')
            
        elif decision == 'reject':
            verification.appeal_status = 'rejected'
            verification.appeal_rejection_reason = notes
            verification.save()
            
            messages.warning(request, 'Appeal rejected')
        
        return redirect('verification:queue')

class QualityMetricsView(LoginRequiredMixin, View):
    """View quality metrics for the system"""
    template_name = 'verification/metrics.html'
    
    def get(self, request):
        if not request.user.is_staff:
            messages.error(request, 'Admin access required')
            return redirect('verification:dashboard')
        
        verifications = Verification.objects.all()
        
        context = {
            'total_verifications': verifications.count(),
            'pending_count': verifications.filter(status='pending').count(),
            'approved_count': verifications.filter(status='approved').count(),
            'rejected_count': verifications.filter(status='rejected').count(),
            'flagged_count': verifications.filter(status='flagged').count(),
            'avg_quality_score': verifications.filter(quality_score__gt=0).aggregate(Avg('quality_score'))['quality_score__avg'] or 0,
            'verifications_by_type': verifications.values('task__task_type').annotate(count=Count('id')),
            'recent_verifications': verifications.select_related('task').order_by('-created_at')[:20],
            'daily_stats': self.get_daily_stats(),
        }
        return render(request, self.template_name, context)
    
    def get_daily_stats(self):
        from django.db.models.functions import TruncDate
        
        return Verification.objects.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=30)
        ).annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            count=Count('id'),
            approved=Count('id', filter=Q(status='approved')),
            rejected=Count('id', filter=Q(status='rejected'))
        ).order_by('-date')

class VerificationReportView(LoginRequiredMixin, View):
    """Generate verification reports"""
    template_name = 'verification/reports.html'
    
    def get(self, request):
        if not request.user.is_staff:
            messages.error(request, 'Admin access required')
            return redirect('verification:dashboard')
        
        # Report type
        report_type = request.GET.get('type', 'summary')
        
        context = {
            'report_type': report_type,
            'summary': self.get_summary(),
            'agent_performance': self.get_agent_performance(),
            'task_performance': self.get_task_performance(),
        }
        return render(request, self.template_name, context)
    
    def get_summary(self):
        return {
            'total_verifications': Verification.objects.count(),
            'avg_response_time': 120,  # minutes, would calculate from actual data
            'approval_rate': Verification.objects.filter(status='approved').count() / max(Verification.objects.count(), 1) * 100,
            'dispute_rate': Dispute.objects.count() / max(Verification.objects.count(), 1) * 100,
        }
    
    def get_agent_performance(self):
        from apps.agents.models import Agent
        
        agents = Agent.objects.filter(task__verification__isnull=False).distinct()
        performance = []
        
        for agent in agents[:20]:
            verifications = Verification.objects.filter(task__matched_agent=agent)
            performance.append({
                'agent': agent.name,
                'total_tasks': verifications.count(),
                'avg_quality': verifications.aggregate(Avg('quality_score'))['quality_score__avg'] or 0,
                'approval_rate': verifications.filter(status='approved').count() / max(verifications.count(), 1) * 100,
            })
        
        return sorted(performance, key=lambda x: x['avg_quality'], reverse=True)
    
    def get_task_performance(self):
        task_types = Verification.objects.values('task__task_type').annotate(
            count=Count('id'),
            avg_quality=Avg('quality_score'),
            approval_rate=Count('id', filter=Q(status='approved')) * 100.0 / Count('id')
        )
        return task_types