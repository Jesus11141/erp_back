from .create_work_order import CreateWorkOrderUseCase
from .list_work_orders import ListWorkOrdersUseCase
from .update_status import UpdateWorkOrderStatusUseCase
from .pay_work_order import PayWorkOrderUseCase

class TechnicalServiceUseCases:
    def __init__(self, order_repo, register_repo=None, param_repo=None, inventory_service=None):
        self.create_work_order = CreateWorkOrderUseCase(
            order_repo, 
            register_repo=register_repo, 
            param_repo=param_repo, 
            inventory_service=inventory_service
        )
        self.list_work_orders = ListWorkOrdersUseCase(order_repo)
        self.update_status = UpdateWorkOrderStatusUseCase(order_repo)
        self.pay_work_order = PayWorkOrderUseCase(order_repo, register_repo)
