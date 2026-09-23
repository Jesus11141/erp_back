from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...application.services import AIChatService

class ChatView(APIView):
    def post(self, request):
        if not request.tenant:
            return Response({'error': 'Tenant not found'}, status=status.HTTP_404_NOT_FOUND)
            
        messages = request.data.get('messages', [])
        
        if not messages:
            return Response({'error': 'No messages provided'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            service = AIChatService(request.tenant.id)
            response_message = service.process_chat(messages)
            return Response({'message': response_message})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
