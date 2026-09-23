from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...infrastructure.django_models import AuditLogModel
from modules.shared.role_permissions import admin_only

class AuditLogView(APIView):
    def get(self, request):
        if not request.tenant:
            return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
            
        # Optional: restrict to admin/superadmin
        if request.user.role not in ('admin', 'superadmin'):
            return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
            
        logs = AuditLogModel.objects.filter(tenant_id=request.tenant.id).order_by('-created_at')[:200]
        
        data = []
        for log in logs:
            data.append({
                'id': log.id,
                'user_id': log.user_id,
                'table_name': log.table_name,
                'record_id': log.record_id,
                'action': log.action,
                'changes': log.changes,
                'ip_address': log.ip_address,
                'created_at': log.created_at,
            })
            
        return Response(data)
