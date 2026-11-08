from typing import Optional, List
from decimal import Decimal
from django.db import transaction
from ...domain.invoice import (
    Invoice, InvoiceItem, CreditNote, CreditNoteItem, Withholding, WithholdingItem,
    DispatchGuide, DispatchGuideItem, PurchaseSettlement, PurchaseSettlementItem
)
from ...domain.repositories import (
    InvoiceRepository, CreditNoteRepository, WithholdingRepository,
    DispatchGuideRepository, PurchaseSettlementRepository
)
from .django_models import (
    InvoiceModel, InvoiceItemModel, InvoiceSequentialModel,
    CreditNoteModel, CreditNoteItemModel,
    WithholdingModel, WithholdingItemModel,
    DispatchGuideModel, DispatchGuideItemModel,
    PurchaseSettlementModel, PurchaseSettlementItemModel
)


class DjangoInvoiceRepository(InvoiceRepository):

    def _to_entity(self, model: InvoiceModel) -> Invoice:
        items = [
            InvoiceItem(
                description=i.description,
                quantity=i.quantity,
                unit_price=i.unit_price,
                discount=i.discount,
                main_code=i.main_code,
                auxiliary_code=i.auxiliary_code,
                vat_rate=i.vat_rate,
            ) for i in model.items.all()
        ]
        return Invoice(
            id=model.id,
            tenant_id=model.tenant_id,
            document_type=model.document_type,
            number=model.number,
            client=model.client,
            client_identification=model.client_identification,
            client_id_type=model.client_id_type,
            client_address=model.client_address,
            client_email=model.client_email,
            date=model.date,
            status=model.status,
            items=items,
            vat=model.vat,
            payment_method=model.payment_method,
            notes=model.notes,
            access_key=model.access_key,
            authorization_number=model.authorization_number,
            authorization_date=model.authorization_date,
            environment=model.environment,
            signed_xml=model.signed_xml,
            ride_url=model.ride_url,
            sri_status=model.sri_status,
            sri_message=model.sri_message,
            created_at=model.created_at,
        )

    def save(self, invoice: Invoice) -> Invoice:
        defaults = {
            'tenant_id': invoice.tenant_id,
            'document_type': getattr(invoice, 'document_type', '01'),
            'number': invoice.number,
            'client': invoice.client,
            'client_identification': invoice.client_identification,
            'client_id_type': invoice.client_id_type,
            'client_address': invoice.client_address,
            'client_email': invoice.client_email,
            'status': invoice.status,
            'vat': invoice.vat,
            'payment_method': invoice.payment_method,
            'notes': invoice.notes,
            'access_key': invoice.access_key,
            'authorization_number': invoice.authorization_number,
            'authorization_date': invoice.authorization_date,
            'environment': invoice.environment,
            'signed_xml': invoice.signed_xml,
            'ride_url': invoice.ride_url,
            'sri_status': invoice.sri_status,
            'sri_message': invoice.sri_message,
        }
        if invoice.created_at:
            defaults['created_at'] = invoice.created_at

        def _execute_save():
            if invoice.id:
                InvoiceModel.objects.filter(id=invoice.id).update(**defaults)
                m = InvoiceModel.objects.get(id=invoice.id)
            else:
                m = InvoiceModel.objects.create(**defaults)
                for item in invoice.items:
                    InvoiceItemModel.objects.create(
                        invoice=m,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                        discount=item.discount,
                        main_code=item.main_code,
                        auxiliary_code=item.auxiliary_code,
                        vat_rate=getattr(item, 'vat_rate', '15'),
                    )
            return self._to_entity(m)

        try:
            return _execute_save()
        except Exception as e:
            if 'column' in str(e).lower() or 'does not exist' in str(e).lower():
                from django.db import connection
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS tipo_comprobante varchar(2) DEFAULT '01';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS cliente_identificacion varchar(20) DEFAULT '9999999999999';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS cliente_tipo_id varchar(2) DEFAULT '05';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS cliente_direccion varchar(200) DEFAULT '';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS cliente_email varchar(254) DEFAULT '';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS forma_pago varchar(2) DEFAULT '01';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS notas text DEFAULT '';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS clave_acceso varchar(49) DEFAULT '';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS numero_autorizacion varchar(49) DEFAULT '';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS fecha_autorizacion varchar(30) DEFAULT '';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS ambiente varchar(1) DEFAULT '1';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS xml_firmado text DEFAULT '';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS ride_url varchar(255) DEFAULT '';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS sri_estado varchar(20) DEFAULT '';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS sri_mensaje text DEFAULT '';
                            ALTER TABLE facturas ADD COLUMN IF NOT EXISTS created_at timestamp with time zone DEFAULT NOW();
                            ALTER TABLE factura_items ADD COLUMN IF NOT EXISTS codigo_principal varchar(50) DEFAULT '';
                            ALTER TABLE factura_items ADD COLUMN IF NOT EXISTS codigo_auxiliar varchar(50) DEFAULT '';
                            ALTER TABLE factura_items ADD COLUMN IF NOT EXISTS descuento numeric(12, 2) DEFAULT 0;
                            ALTER TABLE factura_items ADD COLUMN IF NOT EXISTS tarifa_iva varchar(10) DEFAULT '15';
                        """)
                    return _execute_save()
                except Exception as e2:
                    import logging
                    logging.getLogger(__name__).error("Auto-heal invoice columns failed: %s", e2)
            raise e

    def find_by_id(self, id: int, tenant_id: int) -> Optional[Invoice]:
        try:
            return self._to_entity(InvoiceModel.objects.get(id=id, tenant_id=tenant_id))
        except InvoiceModel.DoesNotExist:
            return None

    def list_by_tenant(self, tenant_id: int, page: int = 1, limit: int = 10) -> dict:
        qs = InvoiceModel.objects.filter(tenant_id=tenant_id).order_by('-id')
        total = qs.count()
        offset = (page - 1) * limit
        items = [self._to_entity(m) for m in qs[offset:offset+limit]]
        return {'total': total, 'page': page, 'limit': limit, 'items': items}

    def next_number(self, tenant_id: int, estab: str = '001', pto_emi: str = '001', document_type: str = '01') -> str:
        def _get_next():
            with transaction.atomic():
                seq, _ = InvoiceSequentialModel.objects.select_for_update().get_or_create(
                    tenant_id=tenant_id, estab=estab, pto_emi=pto_emi, document_type=document_type,
                    defaults={'ultimo': 0},
                )
                seq.ultimo += 1
                seq.save(update_fields=['ultimo'])
                return f"{estab}-{pto_emi}-{str(seq.ultimo).zfill(9)}"

        try:
            return _get_next()
        except Exception as e:
            from django.db import connection
            try:
                with connection.cursor() as cursor:
                    cursor.execute("ALTER TABLE factura_secuenciales ADD COLUMN IF NOT EXISTS document_type varchar(2) DEFAULT '01';")
                    cursor.execute("ALTER TABLE facturas ADD COLUMN IF NOT EXISTS tipo_comprobante varchar(2) DEFAULT '01';")
                return _get_next()
            except Exception as e2:
                import logging
                logging.getLogger(__name__).error("Error obteniendo secuencial: %s | Auto-heal error: %s", e, e2)
                raise e


from ...domain.invoice import CreditNote, CreditNoteItem
from ...domain.repositories import CreditNoteRepository
from .django_models import CreditNoteModel, CreditNoteItemModel

class DjangoCreditNoteRepository(CreditNoteRepository):

    def _to_entity(self, model: CreditNoteModel) -> CreditNote:
        items = [
            CreditNoteItem(
                description=i.description,
                quantity=i.quantity,
                unit_price=i.unit_price,
                discount=i.discount,
                main_code=i.main_code,
                vat_rate=i.vat_rate,
            ) for i in model.items.all()
        ]
        return CreditNote(
            id=model.id,
            tenant_id=model.tenant_id,
            number=model.number,
            origin_invoice_number=model.origin_invoice_number,
            origin_invoice_key=model.origin_invoice_key,
            client=model.client,
            client_identification=model.client_identification,
            client_id_type=model.client_id_type,
            reason=model.reason,
            date=model.date,
            status=model.status,
            items=items,
            environment=model.environment,
            access_key=model.access_key,
            authorization_number=model.authorization_number,
            authorization_date=model.authorization_date,
            signed_xml=model.signed_xml,
            sri_status=model.sri_status,
            sri_message=model.sri_message,
        )

    def save(self, nc: CreditNote) -> CreditNote:
        defaults = {
            'tenant_id': nc.tenant_id,
            'number': nc.number,
            'origin_invoice_number': nc.origin_invoice_number,
            'origin_invoice_key': nc.origin_invoice_key,
            'client': nc.client,
            'client_identification': nc.client_identification,
            'client_id_type': nc.client_id_type,
            'reason': nc.reason,
            'status': nc.status,
            'environment': nc.environment,
            'access_key': nc.access_key,
            'authorization_number': nc.authorization_number,
            'authorization_date': nc.authorization_date,
            'signed_xml': nc.signed_xml,
            'sri_status': nc.sri_status,
            'sri_message': nc.sri_message,
        }
        if nc.id:
            CreditNoteModel.objects.filter(id=nc.id).update(**defaults)
            model = CreditNoteModel.objects.get(id=nc.id)
        else:
            model = CreditNoteModel.objects.create(**defaults)
            for item in nc.items:
                CreditNoteItemModel.objects.create(
                    credit_note=model,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount=item.discount,
                    main_code=item.main_code,
                    vat_rate=getattr(item, 'vat_rate', '15'),
                )
        return self._to_entity(model)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[CreditNote]:
        try:
            return self._to_entity(CreditNoteModel.objects.get(id=id, tenant_id=tenant_id))
        except CreditNoteModel.DoesNotExist:
            return None

    def list_by_tenant(self, tenant_id: int) -> List[CreditNote]:
        return [self._to_entity(m) for m in CreditNoteModel.objects.filter(tenant_id=tenant_id)]

    def next_number(self, tenant_id: int, estab: str = '001', pto_emi: str = '001', document_type: str = '04') -> str:
        prefix = f"{estab}-{pto_emi}-"
        last_nc = CreditNoteModel.objects.filter(
            tenant_id=tenant_id,
            number__startswith=prefix
        ).order_by('-number').first()
        
        if last_nc:
            try:
                last_seq = int(last_nc.number.split('-')[-1])
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1
            
        return f"{prefix}{str(next_seq).zfill(9)}"


from ...domain.invoice import Withholding, WithholdingItem
from ...domain.repositories import WithholdingRepository
from .django_models import WithholdingModel, WithholdingItemModel

class DjangoWithholdingRepository(WithholdingRepository):

    def _to_entity(self, model: WithholdingModel) -> Withholding:
        items = [
            WithholdingItem(
                type_code=i.type_code,
                withholding_code=i.withholding_code,
                tax_base=i.tax_base,
                percentage=i.percentage,
            ) for i in model.items.all()
        ]
        return Withholding(
            id=model.id,
            tenant_id=model.tenant_id,
            number=model.number,
            supplier=model.supplier,
            supplier_identification=model.supplier_identification,
            supplier_id_type=model.supplier_id_type,
            origin_invoice_number=model.origin_invoice_number,
            fiscal_period=model.fiscal_period,
            date=model.date,
            status=model.status,
            items=items,
            environment=model.environment,
            access_key=model.access_key,
            authorization_number=model.authorization_number,
            authorization_date=model.authorization_date,
            signed_xml=model.signed_xml,
            sri_status=model.sri_status,
            sri_message=model.sri_message,
        )

    def save(self, ret: Withholding) -> Withholding:
        defaults = {
            'tenant_id': ret.tenant_id,
            'number': ret.number,
            'supplier': ret.supplier,
            'supplier_identification': ret.supplier_identification,
            'supplier_id_type': ret.supplier_id_type,
            'origin_invoice_number': ret.origin_invoice_number,
            'fiscal_period': ret.fiscal_period,
            'date': ret.date,
            'status': ret.status,
            'environment': ret.environment,
            'access_key': ret.access_key,
            'authorization_number': ret.authorization_number,
            'authorization_date': ret.authorization_date,
            'signed_xml': ret.signed_xml,
            'sri_status': ret.sri_status,
            'sri_message': ret.sri_message,
        }
        if ret.id:
            WithholdingModel.objects.filter(id=ret.id).update(**defaults)
            model = WithholdingModel.objects.get(id=ret.id)
            model.items.all().delete()
        else:
            model = WithholdingModel.objects.create(**defaults)

        for item in ret.items:
            WithholdingItemModel.objects.create(
                withholding=model,
                type_code=item.type_code,
                withholding_code=item.withholding_code,
                tax_base=item.tax_base,
                percentage=item.percentage,
                withheld_value=item.withheld_value,
            )
        return self._to_entity(model)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[Withholding]:
        try:
            return self._to_entity(WithholdingModel.objects.get(id=id, tenant_id=tenant_id))
        except WithholdingModel.DoesNotExist:
            return None

    def list_by_tenant(self, tenant_id: int) -> List[Withholding]:
        return [self._to_entity(m) for m in WithholdingModel.objects.filter(tenant_id=tenant_id).order_by('-date', '-id')]

    def next_number(self, tenant_id: int, estab: str = '001', pto_emi: str = '001', document_type: str = '07') -> str:
        prefix = f"{estab}-{pto_emi}-"
        last_ret = WithholdingModel.objects.filter(
            tenant_id=tenant_id,
            number__startswith=prefix
        ).order_by('-number').first()
        
        if last_ret:
            try:
                last_seq = int(last_ret.number.split('-')[-1])
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1
            
        return f"{prefix}{str(next_seq).zfill(9)}"


# ── Guía de Remisión (Tipo 06) ────────────────────────────────

class DjangoDispatchGuideRepository(DispatchGuideRepository):

    def _to_entity(self, model: DispatchGuideModel) -> DispatchGuide:
        items = [
            DispatchGuideItem(
                description=i.description,
                quantity=i.quantity,
                internal_code=i.internal_code,
            ) for i in model.items.all()
        ]
        return DispatchGuide(
            id=model.id,
            tenant_id=model.tenant_id,
            number=model.number,
            date_emission=model.date_emission,
            start_date=model.start_date,
            end_date=model.end_date,
            starting_address=model.starting_address,
            carrier_ruc=model.carrier_ruc,
            carrier_name=model.carrier_name,
            carrier_id_type=model.carrier_id_type,
            vehicle_plate=model.vehicle_plate,
            recipient_id=model.recipient_id,
            recipient_id_type=model.recipient_id_type,
            recipient_name=model.recipient_name,
            recipient_address=model.recipient_address,
            transfer_reason=model.transfer_reason,
            route=model.route,
            origin_doc_type=model.origin_doc_type,
            origin_doc_number=model.origin_doc_number,
            origin_doc_auth=model.origin_doc_auth,
            origin_doc_date=model.origin_doc_date,
            status=model.status,
            items=items,
            environment=model.environment,
            access_key=model.access_key,
            authorization_number=model.authorization_number,
            authorization_date=model.authorization_date,
            signed_xml=model.signed_xml,
            sri_status=model.sri_status,
            sri_message=model.sri_message,
        )

    def save(self, guide: DispatchGuide) -> DispatchGuide:
        defaults = {
            'tenant_id': guide.tenant_id,
            'number': guide.number,
            'date_emission': guide.date_emission,
            'start_date': guide.start_date,
            'end_date': guide.end_date,
            'starting_address': guide.starting_address,
            'carrier_ruc': guide.carrier_ruc,
            'carrier_name': guide.carrier_name,
            'carrier_id_type': guide.carrier_id_type,
            'vehicle_plate': guide.vehicle_plate,
            'recipient_id': guide.recipient_id,
            'recipient_id_type': guide.recipient_id_type,
            'recipient_name': guide.recipient_name,
            'recipient_address': guide.recipient_address,
            'transfer_reason': guide.transfer_reason,
            'route': guide.route,
            'origin_doc_type': guide.origin_doc_type,
            'origin_doc_number': guide.origin_doc_number,
            'origin_doc_auth': guide.origin_doc_auth,
            'origin_doc_date': guide.origin_doc_date,
            'status': guide.status,
            'environment': guide.environment,
            'access_key': guide.access_key,
            'authorization_number': guide.authorization_number,
            'authorization_date': guide.authorization_date,
            'signed_xml': guide.signed_xml,
            'sri_status': guide.sri_status,
            'sri_message': guide.sri_message,
        }
        if guide.id:
            DispatchGuideModel.objects.filter(id=guide.id).update(**defaults)
            model = DispatchGuideModel.objects.get(id=guide.id)
            model.items.all().delete()
        else:
            model = DispatchGuideModel.objects.create(**defaults)

        for item in guide.items:
            DispatchGuideItemModel.objects.create(
                guide=model,
                internal_code=item.internal_code,
                description=item.description,
                quantity=item.quantity,
            )
        return self._to_entity(model)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[DispatchGuide]:
        try:
            return self._to_entity(DispatchGuideModel.objects.get(id=id, tenant_id=tenant_id))
        except DispatchGuideModel.DoesNotExist:
            return None

    def list_by_tenant(self, tenant_id: int) -> List[DispatchGuide]:
        return [self._to_entity(m) for m in DispatchGuideModel.objects.filter(tenant_id=tenant_id).order_by('-date_emission', '-id')]

    def next_number(self, tenant_id: int, estab: str = '001', pto_emi: str = '001', document_type: str = '06') -> str:
        prefix = f"{estab}-{pto_emi}-"
        last_g = DispatchGuideModel.objects.filter(
            tenant_id=tenant_id,
            number__startswith=prefix
        ).order_by('-number').first()
        
        if last_g:
            try:
                last_seq = int(last_g.number.split('-')[-1])
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1
            
        return f"{prefix}{str(next_seq).zfill(9)}"


# ── Liquidación de Compra (Tipo 03) ───────────────────────────

class DjangoPurchaseSettlementRepository(PurchaseSettlementRepository):

    def _to_entity(self, model: PurchaseSettlementModel) -> PurchaseSettlement:
        items = [
            PurchaseSettlementItem(
                description=i.description,
                quantity=i.quantity,
                unit_price=i.unit_price,
                discount=i.discount,
                vat_rate=i.vat_rate,
                product_code=i.product_code,
            ) for i in model.items.all()
        ]
        return PurchaseSettlement(
            id=model.id,
            tenant_id=model.tenant_id,
            number=model.number,
            supplier=model.supplier,
            supplier_identification=model.supplier_identification,
            supplier_id_type=model.supplier_id_type,
            supplier_address=model.supplier_address,
            supplier_email=model.supplier_email,
            date=model.date,
            payment_method=model.payment_method,
            status=model.status,
            items=items,
            notes=model.notes,
            environment=model.environment,
            access_key=model.access_key,
            authorization_number=model.authorization_number,
            authorization_date=model.authorization_date,
            signed_xml=model.signed_xml,
            sri_status=model.sri_status,
            sri_message=model.sri_message,
        )

    def save(self, settlement: PurchaseSettlement) -> PurchaseSettlement:
        defaults = {
            'tenant_id': settlement.tenant_id,
            'number': settlement.number,
            'supplier': settlement.supplier,
            'supplier_identification': settlement.supplier_identification,
            'supplier_id_type': settlement.supplier_id_type,
            'supplier_address': settlement.supplier_address,
            'supplier_email': settlement.supplier_email,
            'date': settlement.date,
            'payment_method': settlement.payment_method,
            'subtotal_0': settlement.subtotal_0,
            'subtotal_iva': settlement.subtotal_iva,
            'vat': settlement.vat,
            'total': settlement.total,
            'notes': settlement.notes,
            'status': settlement.status,
            'environment': settlement.environment,
            'access_key': settlement.access_key,
            'authorization_number': settlement.authorization_number,
            'authorization_date': settlement.authorization_date,
            'signed_xml': settlement.signed_xml,
            'sri_status': settlement.sri_status,
            'sri_message': settlement.sri_message,
        }
        if settlement.id:
            PurchaseSettlementModel.objects.filter(id=settlement.id).update(**defaults)
            model = PurchaseSettlementModel.objects.get(id=settlement.id)
            model.items.all().delete()
        else:
            model = PurchaseSettlementModel.objects.create(**defaults)

        for item in settlement.items:
            PurchaseSettlementItemModel.objects.create(
                settlement=model,
                product_code=item.product_code,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                discount=item.discount,
                vat_rate=item.vat_rate,
                subtotal=item.subtotal,
            )
        return self._to_entity(model)

    def find_by_id(self, id: int, tenant_id: int) -> Optional[PurchaseSettlement]:
        try:
            return self._to_entity(PurchaseSettlementModel.objects.get(id=id, tenant_id=tenant_id))
        except PurchaseSettlementModel.DoesNotExist:
            return None

    def list_by_tenant(self, tenant_id: int) -> List[PurchaseSettlement]:
        return [self._to_entity(m) for m in PurchaseSettlementModel.objects.filter(tenant_id=tenant_id).order_by('-date', '-id')]

    def next_number(self, tenant_id: int, estab: str = '001', pto_emi: str = '001', document_type: str = '03') -> str:
        prefix = f"{estab}-{pto_emi}-"
        last_s = PurchaseSettlementModel.objects.filter(
            tenant_id=tenant_id,
            number__startswith=prefix
        ).order_by('-number').first()
        
        if last_s:
            try:
                last_seq = int(last_s.number.split('-')[-1])
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1
            
        return f"{prefix}{str(next_seq).zfill(9)}"

