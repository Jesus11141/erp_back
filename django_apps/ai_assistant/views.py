from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import KnowledgeArticle

class KnowledgeArticleView(APIView):
    def post(self, request):
        tenant_id = request.tenant_id
        pregunta = request.data.get('question')
        solucion = request.data.get('solution')
        
        if not pregunta or not solucion:
            return Response({"error": "question y solution son requeridos"}, status=status.HTTP_400_BAD_REQUEST)
            
        # Buscar si ya existe una similar para sumar votos o crearla
        # Por simplicidad, la creamos nueva o buscamos exacta
        article, created = KnowledgeArticle.objects.get_or_create(
            tenant_id=tenant_id,
            question=pregunta,
            defaults={'solution': solucion}
        )
        
        if not created:
            article.useful_votes += 1
            article.save()
            
        return Response({"status": "ok", "article_id": article.id}, status=status.HTTP_201_CREATED)
