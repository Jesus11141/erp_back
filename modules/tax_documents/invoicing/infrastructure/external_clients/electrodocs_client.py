import os
import requests
from django.conf import settings
from decimal import Decimal
from datetime import datetime

def get_electrodocs_url():
    return getattr(settings, 'ELECTRODOCS_URL', 'http://localhost:8080')

def get_electrodocs_headers():
    # If the go endpoints are protected by auth middleware, we would need to generate a token or 
    # adjust the go service. For now, assuming we bypass or have a generic token.
    # We will pass a standard Content-Type.
    return {'Content-Type': 'application/json'}

def build_invoice_via_go(invoice, issuer: dict) -> str:
    url = f"{get_electrodocs_url()}/v1/builder/invoice"
    
    items_dto = []
    for item in invoice.items:
        vat_rate_str = str(getattr(item, 'vat_rate', '15'))
        vat_percentage = float(vat_rate_str)
        subtotal = float(item.subtotal)
        iva = round(subtotal * (vat_percentage / 100), 2)
        total = round(subtotal + iva, 2)
        
        tax_code = "2"
        tax_name = "IVA"
        
        items_dto.append({
            "item_id": getattr(item, 'main_code', '001') or '001',
            "item_name": item.description,
            "item_quantity": int(item.quantity),
            "price": {
                "per_item": {
                    "subtotal_without_taxes": float(item.unit_price),
                    "discount_percentage": 0,
                    "discounts_value": float(item.discount),
                    "subtotal_include_discounts": float(item.unit_price) - float(item.discount),
                    "tax_value": round((float(item.unit_price) - float(item.discount)) * (vat_percentage / 100), 2),
                    "total": round((float(item.unit_price) - float(item.discount)) * (1 + (vat_percentage / 100)), 2),
                    "taxes": [{
                        "tax_name": tax_name,
                        "tax_code": tax_code,
                        "tax_percentage": vat_percentage,
                        "total_tax_value": round((float(item.unit_price) - float(item.discount)) * (vat_percentage / 100), 2),
                        "base_amount": float(item.unit_price) - float(item.discount)
                    }]
                },
                "total_price": {
                    "subtotal_without_taxes": subtotal,
                    "discount_percentage": 0,
                    "discounts_value": float(item.discount * item.quantity),
                    "subtotal_include_discounts": subtotal,
                    "tax_value": iva,
                    "total": total,
                    "taxes": [{
                        "tax_name": tax_name,
                        "tax_code": tax_code,
                        "tax_percentage": vat_percentage,
                        "total_tax_value": iva,
                        "base_amount": subtotal
                    }]
                }
            }
        })
    
    subtotal_without_taxes = sum(item["price"]["total_price"]["subtotal_without_taxes"] for item in items_dto)
    discounts_value = sum(item["price"]["total_price"]["discounts_value"] for item in items_dto)
    tax_value = sum(item["price"]["total_price"]["tax_value"] for item in items_dto)
    total = sum(item["price"]["total_price"]["total"] for item in items_dto)
    
    taxes_dict = {}
    for item in items_dto:
        for t in item["price"]["total_price"]["taxes"]:
            key = (t["tax_name"], t["tax_code"], t["tax_percentage"])
            if key not in taxes_dict:
                taxes_dict[key] = {"base": 0.0, "value": 0.0}
            taxes_dict[key]["base"] += t["base_amount"]
            taxes_dict[key]["value"] += t["total_tax_value"]
            
    totals_taxes = []
    for k, v in taxes_dict.items():
        totals_taxes.append({
            "tax_name": k[0],
            "tax_code": k[1],
            "tax_percentage": k[2],
            "base_amount": round(v["base"], 2),
            "total_tax_value": round(v["value"], 2)
        })

    payload = {
        "transaction_date": f"{invoice.date.strftime('%Y-%m-%dT%H:%M:%S')}Z",
        "format": "xml",
        "point_of_sale": {
            "company_id": issuer.get('ruc', ''),
            "company_name": issuer.get('razon_social', ''),
            "company_address": issuer.get('direccion', ''),
            "branch_office_id": issuer.get('establecimiento', '001'),
            "point_of_sale_id": issuer.get('punto_emision', '001'),
            "sequential": int(invoice.number.split('-')[-1]) if invoice.number and '-' in invoice.number else 0
        },
        "client": {
            "client_id": invoice.client_identification,
            "name": invoice.client,
            "government_id_type": invoice.client_id_type,
            "government_id_number": invoice.client_identification,
            "address": invoice.client_address or "S/N",
            "email": invoice.client_email or "no@email.com"
        },
        "details": {
            "order_id": invoice.number,
            "created_at": invoice.date.strftime('%Y-%m-%d 00:00:00'),
            "items": items_dto
        },
        "payments": {
            "payment_methods": [
                {
                    "method": invoice.payment_method,
                    "amount": round(total, 2)
                }
            ]
        },
        "totals": {
            "subtotal_without_taxes": round(subtotal_without_taxes, 2),
            "discounts_value": round(discounts_value, 2),
            "tax_value": round(tax_value, 2),
            "total": round(total, 2),
            "taxes": totals_taxes
        },
        "additional_data": [
            {"key": "Direccion", "value": invoice.client_address or "S/N"},
            {"key": "Email", "value": invoice.client_email or "no@email.com"}
        ],
        "location_to_store": {
            "url": "dummy",
            "server": {"host": "http://dummy", "user": "dummy", "pass": "dummy"}
        }
    }
    
    response = requests.post(url, json=payload, headers=get_electrodocs_headers())
    if response.status_code != 200:
        raise ValueError(f"Error generando factura en Go: {response.text}")
        
    data = response.json()
    if not data.get("success"):
        raise ValueError(f"Error Go: {data.get('message')}")
        
    return data["data"]["storage_url"]


def sign_invoice_via_go(storage_url: str, cert_path: str, cert_pass: str) -> str:
    url = f"{get_electrodocs_url()}/v1/signing"
    
    # Suponiendo que el backend de Django corre en localhost:8000 para descargar la firma
    # En producción esto debería apuntar a la URL pública del servidor
    # En producción esto debería apuntar a la URL pública del servidor
    host = getattr(settings, 'BACKEND_URL', 'http://80.190.74.18')
    cert_url = f"{host}/media/{cert_path}"
    
    payload = {
        "file": {
            "url": storage_url,
            "server": {"host": "", "user": "", "pass": ""}
        },
        "signature": {
            "url": cert_url,
            "pass": cert_pass,
            "server": {"host": "", "user": "", "pass": ""}
        },
        "location_file_signed": {
            "url": "",
            "server": {"host": "", "user": "", "pass": ""}
        },
        "file_type": "xml"
    }
    
    response = requests.post(url, json=payload, headers=get_electrodocs_headers())
    if response.status_code != 200:
        raise ValueError(f"Error firmando en Go: {response.text}")
        
    data = response.json()
    if not data.get("success"):
        raise ValueError(f"Error Go: {data.get('message')}")
        
    return data["data"]["storage_url"]


def send_receipt_via_go(signed_storage_url: str, environment: str, issuer: dict, tenant_id: int, invoice_id: int, doc_type: str = 'invoice', comprobant_code: str = '01') -> dict:
    url = f"{get_electrodocs_url()}/v1/notifier/government"
    
    payload = {
        "file_signed": {
            "url": signed_storage_url,
            "server": {"host": "", "user": "", "pass": ""}
        },
        "government": {
            "url": "https://celcer.sri.gob.ec/comprobantes-electronicos-ws/" if environment == '1' else "https://cel.sri.gob.ec/comprobantes-electronicos-ws/",
            "user": issuer.get('ruc', ''),
            "pass": issuer.get('sri_password', '')
        },
        "file_signed_authorized": {
            "url": "",
            "server": {"host": "", "user": "", "pass": ""}
        },
        "company_ruc": issuer.get('ruc', ''),
        "branch_office": issuer.get('establecimiento', '001'),
        "point_of_sale": issuer.get('punto_emision', '001'),
        "comprobant_code": comprobant_code,
        "metadata": {
            "tenant_id": str(tenant_id),
            "invoice_id": str(invoice_id),
            "doc_type": doc_type
        }
    }
    
    response = requests.post(url, json=payload, headers=get_electrodocs_headers())
    if response.status_code != 200:
        raise ValueError(f"Error notificando SRI en Go: {response.text}")
        
    data = response.json()
    if not data.get("success"):
        return {'estado': 'RECHAZADA', 'messages': [data.get('message')]}
        
    return {'estado': 'RECIBIDA', 'messages': ['Recibida y procesada por el Facturador Go']}
