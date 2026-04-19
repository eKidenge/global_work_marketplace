# apps/support/urls.py
from django.urls import path
from . import views

app_name = 'support'

urlpatterns = [
    # Tickets
    path('tickets/', views.TicketListView.as_view(), name='tickets'),
    path('tickets/create/', views.CreateTicketView.as_view(), name='create_ticket'),
    path('tickets/<uuid:ticket_id>/', views.TicketDetailView.as_view(), name='ticket_detail'),
    path('tickets/<uuid:ticket_id>/reply/', views.ReplyToTicketView.as_view(), name='reply_ticket'),
    path('tickets/<uuid:ticket_id>/close/', views.CloseTicketView.as_view(), name='close_ticket'),
    path('tickets/<uuid:ticket_id>/reopen/', views.ReopenTicketView.as_view(), name='reopen_ticket'),
    
    # Knowledge base
    path('knowledge-base/', views.KnowledgeBaseView.as_view(), name='knowledge_base'),
    path('knowledge-base/<slug:slug>/', views.ArticleDetailView.as_view(), name='article_detail'),
    path('knowledge-base/category/<slug:slug>/', views.CategoryView.as_view(), name='category'),
    path('knowledge-base/search/', views.SearchArticlesView.as_view(), name='search_articles'),
    
    # FAQs
    path('faq/', views.FAQView.as_view(), name='faq'),
    path('faq/category/<slug:slug>/', views.FAQCategoryView.as_view(), name='faq_category'),
    
    # Contact
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('contact/success/', views.ContactSuccessView.as_view(), name='contact_success'),
    
    # Announcements (public)
    path('announcements/', views.PublicAnnouncementView.as_view(), name='announcements'),
]