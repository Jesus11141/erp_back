from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ...application.period_service import PeriodManagementService


def _check_tenant(request):
    if not getattr(request, 'tenant', None):
        return Response({'error': 'Company not found'}, status=status.HTTP_404_NOT_FOUND)
    return None


class AccountingPeriodsView(APIView):
    """
    Lista el estado de los 12 meses del año especificado con métricas resumidas
    y datos de auditoría de cierre.
    """
    def get(self, request):
        if err := _check_tenant(request): return err

        try:
            year = int(request.query_params.get('year', date.today().year))
        except (ValueError, TypeError):
            year = date.today().year

        service = PeriodManagementService(request.tenant.id)
        periods = service.list_periods_for_year(year)
        return Response({
            'year': year,
            'periods': periods
        })


class AccountingPeriodStatusUpdateView(APIView):
    """
    Actualiza el estado de un período fiscal: 'open', 'locked' (bloqueo operativo) o 'closed' (cerrado definitivo).
    Registra quién realizó el cambio y las notas de auditoría.
    """
    def post(self, request):
        if err := _check_tenant(request): return err

        data = request.data
        try:
            year = int(data.get('year', date.today().year))
            month = int(data.get('month', 1))
            new_status = str(data.get('status', 'open')).strip().lower()
            notes = str(data.get('notes', '')).strip()

            user_name = getattr(request.user, 'email', None) or getattr(request.user, 'username', 'Contabilidad')

            service = PeriodManagementService(request.tenant.id)
            result = service.set_status(
                year=year,
                month=month,
                new_status=new_status,
                user_name=user_name,
                notes=notes
            )
            return Response(result, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
