from django.http import JsonResponse
import json
from django.views.decorators.csrf import csrf_exempt
from modules.accounting.application.extractor_use_cases import SetupSriCredentialsUseCase, RunSriExtractionUseCase
from modules.accounting.infrastructure.django_models import SriInboxModel

@csrf_exempt
def setup_sri_credentials(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tenant_id = request.tenant.id if hasattr(request, 'tenant') else data.get('tenant_id', 1)
            
            use_case = SetupSriCredentialsUseCase()
            use_case.execute(
                tenant_id=tenant_id,
                ruc=data.get('ruc'),
                password=data.get('password')
            )
            return JsonResponse({'status': 'success', 'message': 'Credenciales guardadas exitosamente'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
def run_sri_extraction(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tenant_id = request.tenant.id if hasattr(request, 'tenant') else data.get('tenant_id', 1)
            
            use_case = RunSriExtractionUseCase()
            result = use_case.execute(
                tenant_id=tenant_id,
                month=int(data.get('month') or 0),
                year=int(data.get('year', 2026))
            )
            return JsonResponse(result)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
def run_sri_invoice_extraction(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tenant_id = request.tenant.id if hasattr(request, 'tenant') else data.get('tenant_id', 1)
            from modules.accounting.application.extractor_use_cases import RunSriInvoiceExtractionUseCase
            use_case = RunSriInvoiceExtractionUseCase()
            result = use_case.execute(
                tenant_id=tenant_id,
                month=int(data.get('month') or 0),
                year=int(data.get('year', 2026))
            )
            return JsonResponse({'status': 'success', 'inserted': result})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
def get_inbox_documents(request):
    if request.method == 'GET':
        tenant_id = request.tenant.id if hasattr(request, 'tenant') else 1
        docs = SriInboxModel.objects.filter(tenant_id=tenant_id).order_by('-emission_date')
        
        from modules.accounting.infrastructure.django_models import SriCredentialModel
        cred = SriCredentialModel.objects.filter(tenant_id=tenant_id).first()
        current_ruc = cred.ruc if cred else None
        
        data = []
        for d in docs:
            # Filtrar para no mezclar facturas de distintos RUCs en un solo tenant
            # Temporalmente desactivado por problemas de parseo estricto
            # if current_ruc and d.xml_content and 'Fallo' not in d.xml_content:
            #     if f"<identificacionComprador>{current_ruc}</identificacionComprador>" not in d.xml_content:
            #         continue
                    
            data.append({
                'id': d.id,
                'supplier_name': d.supplier_name,
                'supplier_ruc': d.supplier_ruc,
                'document_type': d.document_type,
                'document_number': d.document_number,
                'access_key': d.access_key,
                'emission_date': d.emission_date.strftime('%Y-%m-%d'),
                'total_amount': str(d.total_amount),
                'xml_content': d.xml_content,
                'status': d.status
            })
        return JsonResponse({'status': 'success', 'data': data})
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
def clear_sri_inbox(request):
    if request.method == 'POST':
        tenant_id = request.tenant.id if hasattr(request, 'tenant') else 1
        SriInboxModel.objects.filter(tenant_id=tenant_id).delete()
        return JsonResponse({'status': 'success', 'message': 'Base de datos limpia'})
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
def get_sri_status(request):
    if request.method == 'GET':
        tenant_id = 1
        from modules.accounting.infrastructure.django_models import SriCredentialModel
        cred = SriCredentialModel.objects.filter(tenant_id=tenant_id).first()
        if cred:
            return JsonResponse({
                'status': 'configured',
                'ruc': cred.ruc,
                'company_name': cred.company_name,
                'tax_status': cred.tax_status,
                'tax_regime': cred.tax_regime,
                'obligated_accounting': cred.obligated_accounting,
                'taxpayer_type': cred.taxpayer_type,
                'tax_category': cred.tax_category,
                'suspension_reason': cred.suspension_reason,
                'activity_start_date': cred.activity_start_date
            })
        return JsonResponse({'status': 'not_configured'})


@csrf_exempt
def process_sri_invoice(request, inbox_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tenant_id = request.tenant.id if hasattr(request, 'tenant') else data.get('tenant_id', 1)
            account_id = data.get('account_id')
            cost_center_id = data.get('cost_center_id')
            
            if not account_id:
                return JsonResponse({'status': 'error', 'message': 'Cuenta de gasto requerida'}, status=400)
                
            from modules.accounting.infrastructure.django_models import SriInboxModel, SupplierModel, PurchaseInvoiceModel
            from modules.contabilidad.infrastructure.django_models import JournalEntryModel, JournalEntryLineModel, AccountModel, CentroCostoModel
            
            inbox_doc = SriInboxModel.objects.get(id=inbox_id, tenant_id=tenant_id)
            if inbox_doc.status == 'processed':
                return JsonResponse({'status': 'error', 'message': 'La factura ya fue contabilizada.'}, status=400)
                
            # Extraer XML
            xml_str = inbox_doc.xml_content
            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_str)
            comprobante = root.find('.//comprobante')
            if comprobante is not None and comprobante.text:
                inner_xml = comprobante.text
                root = ET.fromstring(inner_xml)
                
            info_tributaria = root.find('.//infoTributaria')
            info_factura = root.find('.//infoFactura')
            
            if info_tributaria is None or info_factura is None:
                return JsonResponse({'status': 'error', 'message': 'XML inválido o no es factura.'}, status=400)
                
            ruc = info_tributaria.find('ruc').text if info_tributaria.find('ruc') is not None else inbox_doc.supplier_ruc
            razon = info_tributaria.find('razonSocial').text if info_tributaria.find('razonSocial') is not None else inbox_doc.supplier_name
            
            supplier, _ = SupplierModel.objects.get_or_create(
                tenant_id=tenant_id, ruc=ruc,
                defaults={'business_name': razon}
            )
            
            base_0 = 0.0
            base_12 = 0.0
            iva = 0.0
            
            total_sin = float(info_factura.find('totalSinImpuestos').text) if info_factura.find('totalSinImpuestos') is not None else 0.0
            total_con = float(info_factura.find('importeTotal').text) if info_factura.find('importeTotal') is not None else 0.0
            
            total_impuestos = info_factura.find('.//totalConImpuestos')
            if total_impuestos is not None:
                for imp in total_impuestos.findall('.//totalImpuesto'):
                    codigo = imp.find('codigo').text if imp.find('codigo') is not None else ''
                    if codigo == '2':
                        base = float(imp.find('baseImponible').text) if imp.find('baseImponible') is not None else 0.0
                        valor = float(imp.find('valor').text) if imp.find('valor') is not None else 0.0
                        if valor > 0:
                            base_12 += base
                            iva += valor
                        else:
                            base_0 += base
                            
            if base_0 == 0 and base_12 == 0:
                base_0 = total_sin
                
            doc_num = info_tributaria.find('estab').text + '-' + info_tributaria.find('ptoEmi').text + '-' + info_tributaria.find('secuencial').text
            
            purchase = PurchaseInvoiceModel.objects.create(
                tenant_id=tenant_id,
                supplier=supplier,
                access_key=inbox_doc.access_key,
                document_number=inbox_doc.document_number or doc_num,
                emission_date=inbox_doc.emission_date,
                base_0=base_0,
                base_12=base_12,
                iva_amount=iva,
                total_amount=total_con
            )
            
            iva_account, _ = AccountModel.objects.get_or_create(
                tenant_id=tenant_id, code='1.1.03.01', 
                defaults={'name': 'IVA Pagado en Compras', 'type': 'is_active'}
            )
            cxp_account, _ = AccountModel.objects.get_or_create(
                tenant_id=tenant_id, code='2.1.01.01', 
                defaults={'name': 'Proveedores por Pagar', 'type': 'pasivo'}
            )
            
            expense_account = AccountModel.objects.get(id=account_id)
            
            entry = JournalEntryModel.objects.create(
                tenant_id=tenant_id,
                date=inbox_doc.emission_date,
                description=f"COMPRA FAC {purchase.document_number} - {supplier.business_name}",
                type='egreso',
                reference=inbox_doc.access_key
            )
            
            if base_0 + base_12 > 0:
                JournalEntryLineModel.objects.create(
                    entry=entry, account=expense_account, debit=base_0 + base_12, credit=0, cost_center_id=cost_center_id
                )
            
            if iva > 0:
                JournalEntryLineModel.objects.create(
                    entry=entry, account=iva_account, debit=iva, credit=0
                )
                
            JournalEntryLineModel.objects.create(
                entry=entry, account=cxp_account, debit=0, credit=total_con
            )
            
            purchase.journal_entry_id = entry.id
            purchase.save()
            
            inbox_doc.purchase_invoice = purchase
            inbox_doc.status = 'processed'
            inbox_doc.save()
            
            return JsonResponse({'status': 'success', 'message': 'Factura contabilizada con éxito', 'entry_id': entry.id})
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)



@csrf_exempt
def run_sri_emitted_extraction(request):
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            tenant_id = request.tenant.id if hasattr(request, 'tenant') else data.get('tenant_id', 1)
            env = data.get('env', 'produccion')
            from modules.accounting.application.extractor_use_cases import SyncSriEmittedDocumentsUseCase
            use_case = SyncSriEmittedDocumentsUseCase()
            inserted = use_case.execute(
                tenant_id=tenant_id,
                month=int(data.get('month') or 0),
                year=int(data.get('year', 2026)),
                env=env
            )
            return JsonResponse({'status': 'success', 'inserted': inserted})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid method'}, status=405)

@csrf_exempt
def get_outbox_documents(request):
    if request.method == 'GET':
        tenant_id = request.tenant.id if hasattr(request, 'tenant') else 1
        from modules.accounting.infrastructure.django_models import SriOutboxModel
        docs = SriOutboxModel.objects.filter(tenant_id=tenant_id).order_by('-emission_date', '-id')
        data = []
        for d in docs:
            data.append({
                'id': d.id,
                'customer_name': d.customer_name,
                'customer_ruc': d.customer_ruc,
                'document_type': d.document_type,
                'document_number': d.document_number,
                'access_key': d.access_key,
                'emission_date': str(d.emission_date) if d.emission_date else None,
                'total_amount': str(d.total_amount),
                'status': d.status,
                'xml_content': d.xml_content
            })
        return JsonResponse(data, safe=False)
    return JsonResponse({'error': 'Invalid method'}, status=405)
