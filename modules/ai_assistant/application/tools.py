from typing import List, Dict, Any
from modules.technical_service.infrastructure.django_models import WorkOrderModel
from django_apps.ai_assistant.models import KnowledgeArticle
from django.db.models import Q

def get_technical_service_tools() -> List[Dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "buscar_estado_orden",
                "description": "Busca el estado de una o varias órdenes de servicio técnico por nombre de cliente, cédula o identificador del dispositivo (ej. IMEI).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "termino_busqueda": {
                            "type": "string",
                            "description": "El nombre, cédula, identificador o IMEI a buscar."
                        }
                    },
                    "required": ["termino_busqueda"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "buscar_soluciones_pasadas",
                "description": "Busca en la base de conocimientos soluciones técnicas a problemas o fallas comunes de dispositivos. Úsalo si el usuario describe un problema con un dispositivo.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "problema": {
                            "type": "string",
                            "description": "Descripción breve del problema o síntoma del dispositivo (ej. 'pantalla rota iphone 13', 'no carga samsung')."
                        }
                    },
                    "required": ["problema"]
                }
            }
        }
    ]

def execute_tool(tenant_id: int, name: str, kwargs: Dict[str, Any]) -> str:
    if name == "buscar_estado_orden":
        termino = kwargs.get('termino_busqueda', '')
        if not termino:
            return "El término de búsqueda está vacío."
            
        # Buscar en la BD
        ordenes = WorkOrderModel.objects.filter(
            Q(customer_name__icontains=termino) |
            Q(device_identifier__icontains=termino),
            tenant_id=tenant_id
        ).order_by('-created_at')[:3]
        
        if not ordenes:
            return f"No encontré ninguna orden bajo el término '{termino}'."
            
        resultado = "Encontré las siguientes órdenes:\n"
        for o in ordenes:
            resultado += f"- Orden #{o.id} ({o.device_type} {o.device_model}): Estado actual es '{o.status}'. Total: ${o.total}, Abono: ${o.advance_payment}.\n"
            
        return resultado
        
    elif name == "buscar_soluciones_pasadas":
        problema = kwargs.get('problema', '')
        if not problema:
            return "Debe proporcionar una descripción del problema."
            
        keywords = problema.split()
        query = Q()
        for kw in keywords:
            query |= Q(question__icontains=kw) | Q(solution__icontains=kw)
            
        articles = KnowledgeArticle.objects.filter(tenant_id=tenant_id).filter(query).distinct()[:3]
        
        if not articles.exists():
            return "No se encontraron soluciones pasadas para este problema en la base de conocimientos."
            
        result = "Soluciones encontradas en la base de conocimientos:\n"
        for art in articles:
            result += f"- Problema: {art.question}\n  Solución: {art.solution}\n  (Votos útiles: {art.useful_votes})\n\n"
            
        return result
        
    return f"Herramienta desconocida: {name}"
