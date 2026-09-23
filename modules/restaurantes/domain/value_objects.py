from enum import Enum

class TableStatus(Enum):
    FREE = 'libre'
    OCCUPIED = 'ocupada'

class OrderStatus(Enum):
    OPEN = 'abierto'
    CLOSED = 'cerrado'
    CANCELLED = 'cancelado'

class KitchenStatus(Enum):
    PENDING = 'pendiente'
    PREPARING = 'preparando'
    READY = 'listo'
    DELIVERED = 'entregado'
