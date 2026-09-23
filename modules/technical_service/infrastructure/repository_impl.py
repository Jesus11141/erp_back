from typing import Optional, List
from modules.technical_service.domain.entities import WorkOrder, WorkOrderItem
from modules.technical_service.domain.repositories import WorkOrderRepository
from modules.technical_service.infrastructure.django_models import WorkOrderModel, WorkOrderItemModel

class DjangoWorkOrderRepository(WorkOrderRepository):
    def save(self, order: WorkOrder) -> WorkOrder:
        model, created = WorkOrderModel.objects.update_or_create(
            id=order.id,
            defaults={
                'tenant_id': order.tenant_id,
                'customer_id': order.customer_id,
                'customer_name': order.customer_name,
                'device_type': order.device_type,
                'device_model': order.device_model,
                'device_identifier': order.device_identifier,
                'physical_conditions': order.physical_conditions,
                'reported_fault': order.reported_fault,
                'advance_payment': order.advance_payment,
                'status': order.status
            }
        )
        
        # Save items
        if not created:
            # Delete old items if updating
            WorkOrderItemModel.objects.filter(work_order=model).delete()
            
        for item in order.items:
            WorkOrderItemModel.objects.create(
                work_order=model,
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount=item.discount
            )
            
        return self._to_entity(model)
        
    def find_by_id(self, id: int, tenant_id: int) -> Optional[WorkOrder]:
        try:
            model = WorkOrderModel.objects.prefetch_related('items').get(id=id, tenant_id=tenant_id)
            return self._to_entity(model)
        except WorkOrderModel.DoesNotExist:
            return None
            
    def list_by_tenant(self, tenant_id: int) -> List[WorkOrder]:
        models = WorkOrderModel.objects.prefetch_related('items').filter(tenant_id=tenant_id).order_by('-created_at')
        return [self._to_entity(m) for m in models]
        
    def delete(self, id: int, tenant_id: int):
        WorkOrderModel.objects.filter(id=id, tenant_id=tenant_id).delete()
        
    def _to_entity(self, model: WorkOrderModel) -> WorkOrder:
        items = [
            WorkOrderItem(
                id=i.id,
                product_id=i.product_id,
                description=i.description,
                quantity=i.quantity,
                unit_price=i.unit_price,
                discount=i.discount
            )
            for i in model.items.all()
        ]
        
        return WorkOrder(
            id=model.id,
            tenant_id=model.tenant_id,
            customer_id=model.customer_id,
            customer_name=model.customer_name,
            device_type=model.device_type,
            device_model=model.device_model,
            device_identifier=model.device_identifier,
            physical_conditions=model.physical_conditions,
            reported_fault=model.reported_fault,
            advance_payment=model.advance_payment,
            status=model.status,
            items=items,
            created_at=model.created_at
        )
