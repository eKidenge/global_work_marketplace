# apps/common/views.py
from django.shortcuts import render
from django.views import View

class LandingPageView(View):
    """Public landing page for the marketplace"""
    template_name = 'common/landing.html'  # Changed to match your path
    
    def get(self, request):
        context = {
            'title': 'Global Work Marketplace',
            'description': 'The economic operating system for AI + humans',
            'user': request.user,
        }
        return render(request, self.template_name, context)