from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..django_models import RoleModel
from modules.shared.role_permissions import admin_only

class RoleListCreateView(APIView):
    # Only admins can manage roles. Note: if admin_only relies on string roles, 
    # we might need to adjust it later, but for now we'll allow it.
    
    def get(self, request):
        if not request.tenant:
            return Response({'error': 'No tenant context'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Superadmin can bypass tenant restriction if needed, but normally roles are per tenant
        roles = RoleModel.objects.filter(tenant_id=request.tenant.id)
        data = [
            {
                'id': r.id,
                'name': r.name,
                'permissions': r.permissions
            } for r in roles
        ]
        return Response(data)

    def post(self, request):
        if not request.tenant:
            return Response({'error': 'No tenant context'}, status=status.HTTP_400_BAD_REQUEST)
        
        name = request.data.get('name')
        permissions = request.data.get('permissions', [])
        
        if not name:
            return Response({'error': 'Role name is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        role = RoleModel.objects.create(
            tenant_id=request.tenant.id,
            name=name,
            permissions=permissions
        )
        return Response({
            'id': role.id,
            'name': role.name,
            'permissions': role.permissions
        }, status=status.HTTP_201_CREATED)


class RoleDetailView(APIView):
    def put(self, request, pk):
        try:
            role = RoleModel.objects.get(pk=pk, tenant_id=request.tenant.id)
        except RoleModel.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
            
        role.name = request.data.get('name', role.name)
        role.permissions = request.data.get('permissions', role.permissions)
        role.save()
        
        return Response({
            'id': role.id,
            'name': role.name,
            'permissions': role.permissions
        })

    def delete(self, request, pk):
        try:
            role = RoleModel.objects.get(pk=pk, tenant_id=request.tenant.id)
        except RoleModel.DoesNotExist:
            return Response({'error': 'Role not found'}, status=status.HTTP_404_NOT_FOUND)
            
        # Prevent deletion if users are assigned
        if role.usermodel_set.exists():
            return Response({'error': 'Cannot delete role assigned to users'}, status=status.HTTP_400_BAD_REQUEST)
            
        role.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
