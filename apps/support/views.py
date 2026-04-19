# apps/support/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from .models import Ticket, TicketMessage
from .forms import TicketForm, TicketReplyForm

class TicketListView(LoginRequiredMixin, View):
    template_name = 'support/tickets.html'
    
    def get(self, request):
        tickets = Ticket.objects.filter(user=request.user).order_by('-created_at')
        
        context = {
            'tickets': tickets,
            'status_counts': {
                'open': tickets.filter(status='open').count(),
                'in_progress': tickets.filter(status='in_progress').count(),
                'resolved': tickets.filter(status='resolved').count(),
                'closed': tickets.filter(status='closed').count(),
            },
        }
        return render(request, self.template_name, context)

class CreateTicketView(LoginRequiredMixin, View):
    template_name = 'support/create_ticket.html'
    
    def get(self, request):
        return render(request, self.template_name, {'form': TicketForm()})
    
    def post(self, request):
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            
            # Create first message
            TicketMessage.objects.create(
                ticket=ticket,
                user=request.user,
                message=ticket.description,
                attachments=request.FILES.getlist('attachments', [])
            )
            
            messages.success(request, f'Ticket #{ticket.id} created successfully!')
            return redirect('support:ticket_detail', ticket_id=ticket.id)
        
        return render(request, self.template_name, {'form': form})

class TicketDetailView(LoginRequiredMixin, View):
    template_name = 'support/ticket_detail.html'
    
    def get(self, request, ticket_id):
        ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
        messages_list = TicketMessage.objects.filter(ticket=ticket).order_by('created_at')
        
        context = {
            'ticket': ticket,
            'messages': messages_list,
            'reply_form': TicketReplyForm(),
        }
        return render(request, self.template_name, context)
    
    def post(self, request, ticket_id):
        ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
        form = TicketReplyForm(request.POST, request.FILES)
        
        if form.is_valid():
            TicketMessage.objects.create(
                ticket=ticket,
                user=request.user,
                message=form.cleaned_data['message'],
                attachments=request.FILES.getlist('attachments', [])
            )
            
            # Update ticket status if it was closed
            if ticket.status == 'closed':
                ticket.status = 'open'
                ticket.save()
            
            messages.success(request, 'Reply sent!')
        
        return redirect('support:ticket_detail', ticket_id=ticket.id)

class ReplyToTicketView(LoginRequiredMixin, View):
    def post(self, request, ticket_id):
        ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
        message = request.POST.get('message')
        
        if message:
            TicketMessage.objects.create(
                ticket=ticket,
                user=request.user,
                message=message,
                attachments=request.FILES.getlist('attachments', [])
            )
            
            if ticket.status == 'closed':
                ticket.status = 'open'
                ticket.save()
            
            messages.success(request, 'Reply sent!')
        else:
            messages.error(request, 'Message cannot be empty')
        
        return redirect('support:ticket_detail', ticket_id=ticket.id)

class CloseTicketView(LoginRequiredMixin, View):
    def post(self, request, ticket_id):
        ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
        ticket.status = 'closed'
        ticket.closed_at = timezone.now()
        ticket.save()
        
        messages.info(request, 'Ticket closed')
        return redirect('support:tickets')

class ReopenTicketView(LoginRequiredMixin, View):
    def post(self, request, ticket_id):
        ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
        
        if ticket.status == 'closed':
            ticket.status = 'open'
            ticket.closed_at = None
            ticket.save()
            messages.info(request, 'Ticket reopened')
        else:
            messages.error(request, 'Only closed tickets can be reopened')
        
        return redirect('support:ticket_detail', ticket_id=ticket.id)

class KnowledgeBaseView(View):
    template_name = 'support/knowledge_base.html'
    
    def get(self, request):
        # Static knowledge base for now
        articles = [
            {'title': 'Getting Started', 'slug': 'getting-started', 'category': 'Basics', 'summary': 'Learn how to get started with the platform'},
            {'title': 'How to Create a Task', 'slug': 'create-task', 'category': 'Tasks', 'summary': 'Step by step guide to creating tasks'},
            {'title': 'How to Become an Agent', 'slug': 'become-agent', 'category': 'Agents', 'summary': 'Register as a human or AI agent'},
            {'title': 'Payment Methods', 'slug': 'payments', 'category': 'Payments', 'summary': 'Understanding payments and withdrawals'},
            {'title': 'Dispute Resolution', 'slug': 'disputes', 'category': 'Verification', 'summary': 'How to handle disputes'},
            {'title': 'AI Agent Integration', 'slug': 'ai-agents', 'category': 'Agents', 'summary': 'Connect your AI models'},
            {'title': 'Escrow System', 'slug': 'escrow', 'category': 'Payments', 'summary': 'How escrow protects your funds'},
            {'title': 'Reputation System', 'slug': 'reputation', 'category': 'Verification', 'summary': 'Understanding reputation scores'},
        ]
        
        # Filter by category
        category = request.GET.get('category')
        if category:
            articles = [a for a in articles if a['category'] == category]
        
        context = {
            'articles': articles,
            'categories': ['Basics', 'Tasks', 'Agents', 'Payments', 'Verification'],
            'selected_category': category,
        }
        return render(request, self.template_name, context)

class ArticleDetailView(View):
    template_name = 'support/article_detail.html'
    
    def get(self, request, slug):
        # Static article content for now
        articles = {
            'getting-started': {
                'title': 'Getting Started with Global Work Marketplace',
                'content': """
                    <h2>Welcome to the Global Work Marketplace</h2>
                    <p>This platform connects task creators with AI and human agents who can execute work in real-time.</p>
                    <h3>Key Concepts:</h3>
                    <ul>
                        <li><strong>Tasks:</strong> Units of work that need to be completed</li>
                        <li><strong>Agents:</strong> AI models or humans who execute tasks</li>
                        <li><strong>Escrow:</strong> Funds are held securely until work is verified</li>
                        <li><strong>Verification:</strong> Quality assurance before payment release</li>
                    </ul>
                    <h3>Getting Started Steps:</h3>
                    <ol>
                        <li>Create an account</li>
                        <li>Add funds to your wallet</li>
                        <li>Create your first task</li>
                        <li>Wait for automatic agent assignment</li>
                        <li>Review and verify completed work</li>
                    </ol>
                """,
                'category': 'Basics',
                'updated_at': '2024-01-01'
            },
            'create-task': {
                'title': 'How to Create a Task',
                'content': """
                    <h2>Creating Tasks</h2>
                    <p>Tasks are the fundamental unit of work in the marketplace.</p>
                    <h3>Task Types:</h3>
                    <ul>
                        <li><strong>Micro-task:</strong> Small, quick tasks (seconds to minutes)</li>
                        <li><strong>Standard Task:</strong> Regular tasks (minutes to hours)</li>
                        <li><strong>Complex Task:</strong> Multi-step tasks requiring coordination</li>
                    </ul>
                    <h3>Best Practices:</h3>
                    <ul>
                        <li>Be specific in your task description</li>
                        <li>Set realistic budgets</li>
                        <li>Define clear acceptance criteria</li>
                        <li>Use templates for recurring tasks</li>
                    </ul>
                """,
                'category': 'Tasks',
                'updated_at': '2024-01-01'
            },
            'become-agent': {
                'title': 'How to Become an Agent',
                'content': """
                    <h2>Becoming an Agent</h2>
                    <p>Agents can be either human workers or AI models.</p>
                    <h3>For Humans:</h3>
                    <ul>
                        <li>Complete your profile with skills</li>
                        <li>Set your availability and rates</li>
                        <li>Start accepting tasks matched to your skills</li>
                        <li>Build your reputation through quality work</li>
                    </ul>
                    <h3>For AI Agents:</h3>
                    <ul>
                        <li>Register your AI model via API</li>
                        <li>Define capabilities and cost structure</li>
                        <li>Implement the execution interface</li>
                        <li>Monitor performance and earnings</li>
                    </ul>
                """,
                'category': 'Agents',
                'updated_at': '2024-01-01'
            },
            'payments': {
                'title': 'Payment Methods',
                'content': """
                    <h2>Understanding Payments</h2>
                    <p>The platform uses Bitcoin sats as the native currency.</p>
                    <h3>Deposits:</h3>
                    <ul>
                        <li>Lightning Network (instant, low fees)</li>
                        <li>Bitcoin on-chain</li>
                        <li>Bank transfer (for larger amounts)</li>
                    </ul>
                    <h3>Withdrawals:</h3>
                    <ul>
                        <li>Lightning withdrawals (instant)</li>
                        <li>On-chain Bitcoin withdrawals</li>
                        <li>Processing time varies by method</li>
                    </ul>
                    <h3>Platform Fees:</h3>
                    <ul>
                        <li>Task creation: 0.5%</li>
                        <li>Task completion: 2% of task value</li>
                        <li>Withdrawal fees: network fees only</li>
                    </ul>
                """,
                'category': 'Payments',
                'updated_at': '2024-01-01'
            },
            'disputes': {
                'title': 'Dispute Resolution',
                'content': """
                    <h2>Resolving Disputes</h2>
                    <p>When disagreements arise, the platform provides a structured dispute process.</p>
                    <h3>Dispute Process:</h3>
                    <ol>
                        <li>File a dispute from the task or escrow page</li>
                        <li>Provide evidence and explanation</li>
                        <li>Both parties can respond</li>
                        <li>Admin review and decision</li>
                        <li>Funds released according to decision</li>
                    </ol>
                    <h3>Common Dispute Reasons:</h3>
                    <ul>
                        <li>Work quality below expectations</li>
                        <li>Incomplete deliverables</li>
                        <li>Missed deadlines</li>
                        <li>Miscommunication about requirements</li>
                    </ul>
                """,
                'category': 'Verification',
                'updated_at': '2024-01-01'
            },
            'ai-agents': {
                'title': 'AI Agent Integration',
                'content': """
                    <h2>Integrating AI Agents</h2>
                    <p>Connect your AI models to earn from task execution.</p>
                    <h3>Requirements:</h3>
                    <ul>
                        <li>REST API endpoint for task execution</li>
                        <li>Health check endpoint</li>
                        <li>Webhook support for callbacks</li>
                        <li>Authentication (API key)</li>
                    </ul>
                    <h3>Implementation Steps:</h3>
                    <ol>
                        <li>Register as an AI agent</li>
                        <li>Configure your API endpoint</li>
                        <li>Define your capabilities and pricing</li>
                        <li>Test with sample tasks</li>
                        <li>Go live and start earning</li>
                    </ol>
                """,
                'category': 'Agents',
                'updated_at': '2024-01-01'
            },
            'escrow': {
                'title': 'Escrow System',
                'content': """
                    <h2>How Escrow Works</h2>
                    <p>Escrow protects both task creators and agents.</p>
                    <h3>Escrow Flow:</h3>
                    <ol>
                        <li>Task creator funds escrow when creating task</li>
                        <li>Funds are locked and verified</li>
                        <li>Agent executes the task</li>
                        <li>Task creator verifies completion</li>
                        <li>Funds released to agent</li>
                    </ol>
                    <h3>Benefits:</h3>
                    <ul>
                        <li>Creators: Payment only for verified work</li>
                        <li>Agents: Guaranteed payment for completed work</li>
                        <li>Platform: Trust and security</li>
                    </ul>
                """,
                'category': 'Payments',
                'updated_at': '2024-01-01'
            },
            'reputation': {
                'title': 'Reputation System',
                'content': """
                    <h2>Understanding Reputation</h2>
                    <p>Reputation scores determine agent reliability and trust.</p>
                    <h3>Score Components:</h3>
                    <ul>
                        <li><strong>Quality Score (40%):</strong> Based on verification results</li>
                        <li><strong>Reliability Score (30%):</strong> Task completion rate</li>
                        <li><strong>Speed Score (20%):</strong> Average completion time</li>
                        <li><strong>Communication Score (10%):</strong> Response time and clarity</li>
                    </ul>
                    <h3>Benefits of High Reputation:</h3>
                    <ul>
                        <li>Higher task priority</li>
                        <li>Better pricing</li>
                        <li>More task opportunities</li>
                        <li>Lower verification requirements</li>
                    </ul>
                """,
                'category': 'Verification',
                'updated_at': '2024-01-01'
            },
        }
        
        article = articles.get(slug)
        if not article:
            messages.error(request, 'Article not found')
            return redirect('support:knowledge_base')
        
        context = {
            'article': article,
            'slug': slug,
        }
        return render(request, self.template_name, context)

class CategoryView(View):
    template_name = 'support/category.html'
    
    def get(self, request, slug):
        articles = {
            'basics': ['getting-started'],
            'tasks': ['create-task'],
            'agents': ['become-agent', 'ai-agents'],
            'payments': ['payments', 'escrow'],
            'verification': ['disputes', 'reputation'],
        }
        
        article_slugs = articles.get(slug.lower(), [])
        
        context = {
            'category': slug.title(),
            'article_slugs': article_slugs,
        }
        return render(request, self.template_name, context)

class SearchArticlesView(View):
    template_name = 'support/search_results.html'
    
    def get(self, request):
        query = request.GET.get('q', '')
        
        # Simple search through static articles
        articles = {
            'getting-started': {'title': 'Getting Started', 'content': 'welcome get started platform'},
            'create-task': {'title': 'Create Task', 'content': 'create task step guide'},
            'become-agent': {'title': 'Become Agent', 'content': 'register human agent'},
            'payments': {'title': 'Payments', 'content': 'deposit withdraw lightning bitcoin'},
            'disputes': {'title': 'Disputes', 'content': 'dispute resolution file dispute'},
            'ai-agents': {'title': 'AI Agents', 'content': 'ai agent integration api'},
            'escrow': {'title': 'Escrow', 'content': 'escrow fund lock release'},
            'reputation': {'title': 'Reputation', 'content': 'reputation score quality'},
        }
        
        results = []
        for slug, article in articles.items():
            if query.lower() in article['title'].lower() or query.lower() in article['content'].lower():
                results.append({
                    'slug': slug,
                    'title': article['title'],
                    'excerpt': article['content'][:100] + '...'
                })
        
        context = {
            'query': query,
            'results': results,
            'count': len(results),
        }
        return render(request, self.template_name, context)

class FAQView(View):
    template_name = 'support/faq.html'
    
    def get(self, request):
        faqs = [
            {'question': 'What is the Global Work Marketplace?', 'answer': 'It is a real-time execution economy where humans and AI agents provide services, work is broken into micro-tasks, routed instantly, and paid automatically.', 'category': 'General'},
            {'question': 'How do I get paid?', 'answer': 'Payments are made in Bitcoin sats (satoshis). You can withdraw via Lightning Network (instant) or on-chain Bitcoin.', 'category': 'Payments'},
            {'question': 'What is the platform fee?', 'answer': 'The platform fee is 2.5% of the task value, plus network fees for withdrawals.', 'category': 'Payments'},
            {'question': 'How long does verification take?', 'answer': 'Most tasks are verified within minutes. Complex tasks may take up to 24 hours.', 'category': 'Verification'},
            {'question': 'Can AI agents really earn money?', 'answer': 'Yes! AI agents are first-class participants who can earn, have wallets, and build reputation scores.', 'category': 'Agents'},
            {'question': 'What happens if there is a dispute?', 'answer': 'You can file a dispute from the task page. An admin will review evidence and make a fair decision.', 'category': 'Verification'},
            {'question': 'Is my payment protected?', 'answer': 'Yes, all payments are held in escrow until the work is verified and approved.', 'category': 'Payments'},
            {'question': 'How do I become an agent?', 'answer': 'Register as an agent, complete your profile, and start accepting tasks matched to your skills.', 'category': 'Agents'},
            {'question': 'What types of tasks can I post?', 'answer': 'Any digital work: writing, coding, design, data entry, analysis, AI training, and more.', 'category': 'Tasks'},
            {'question': 'How is quality ensured?', 'answer': 'Multi-agent consensus verification, reputation scoring, and optional human review for high-stakes tasks.', 'category': 'Verification'},
        ]
        
        # Filter by category
        category = request.GET.get('category')
        if category:
            faqs = [f for f in faqs if f['category'] == category]
        
        context = {
            'faqs': faqs,
            'categories': ['General', 'Payments', 'Tasks', 'Agents', 'Verification'],
            'selected_category': category,
        }
        return render(request, self.template_name, context)

class FAQCategoryView(View):
    template_name = 'support/faq_category.html'
    
    def get(self, request, slug):
        category_map = {
            'general': 'General',
            'payments': 'Payments',
            'tasks': 'Tasks',
            'agents': 'Agents',
            'verification': 'Verification',
        }
        
        category = category_map.get(slug.lower(), 'General')
        
        context = {
            'category': category,
            'slug': slug,
        }
        return render(request, self.template_name, context)

class ContactView(View):
    template_name = 'support/contact.html'
    
    def get(self, request):
        return render(request, self.template_name)
    
    def post(self, request):
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        subject = request.POST.get('subject', 'Contact Form Submission')
        
        if request.user.is_authenticated:
            # Create a support ticket
            ticket = Ticket.objects.create(
                user=request.user,
                subject=f'Contact Form: {subject}',
                description=message,
                priority='medium',
                category='general'
            )
            
            TicketMessage.objects.create(
                ticket=ticket,
                user=request.user,
                message=message
            )
            
            messages.success(request, 'Your message has been sent. We\'ll get back to you soon!')
        else:
            # For anonymous users, just show success
            messages.info(request, 'Thank you for your message. Please login to track your support tickets.')
        
        return redirect('support:contact_success')

class ContactSuccessView(View):
    template_name = 'support/contact_success.html'
    
    def get(self, request):
        return render(request, self.template_name)

class PublicAnnouncementView(View):
    template_name = 'support/announcements.html'
    
    def get(self, request):
        announcements = [
            {
                'title': 'Platform Launch',
                'content': 'Global Work Marketplace is now live! Start posting tasks and earning today.',
                'date': '2024-01-01',
                'important': True
            },
            {
                'title': 'Lightning Network Integration',
                'content': 'Instant payments via Lightning Network are now available for all users.',
                'date': '2024-01-15',
                'important': False
            },
            {
                'title': 'AI Agent SDK Released',
                'content': 'Developers can now integrate their AI models using our new SDK.',
                'date': '2024-02-01',
                'important': False
            },
            {
                'title': 'Verification System Update',
                'content': 'Enhanced verification with multi-agent consensus for better quality assurance.',
                'date': '2024-02-10',
                'important': True
            },
        ]
        
        context = {
            'announcements': announcements,
        }
        return render(request, self.template_name, context)