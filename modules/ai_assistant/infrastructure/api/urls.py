from django.urls import path
from .views import ChatView
from django_apps.ai_assistant.views import KnowledgeArticleView

urlpatterns = [
    path('chat/', ChatView.as_view(), name='ai-chat'),
    path('knowledge/', KnowledgeArticleView.as_view(), name='ai-knowledge'),
]
