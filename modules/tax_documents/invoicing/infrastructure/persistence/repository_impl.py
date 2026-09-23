from typing import Optional, List
from decimal import Decimal
from django.db import transaction
from ...domain.invoice import Invoice, InvoiceItem
from ...domain.repositories import InvoiceRepository
from .django_models import InvoiceModel, InvoiceItemModel, InvoiceSequentialModel


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

        if invoice.id:
            InvoiceModel.objects.filter(id=invoice.id).update(**defaults)
            model = InvoiceModel.objects.get(id=invoice.id)
        else:
            model = InvoiceModel.objects.create(**defaults)
            for item in invoice.items:
                InvoiceItemModel.objects.create(
                    invoice=model,
                    description=item.description,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    discount=item.discount,
                    main_code=item.main_code,
                    auxiliary_code=item.auxiliary_code,
                    vat_rate=getattr(item, 'vat_rate', '15'),
                )
        return self._to_entity(model)

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
        with transaction.atomic():
            seq, _ = InvoiceSequentialModel.objects.select_for_update().get_or_create(
                tenant_id=tenant_id, estab=estab, pto_emi=pto_emi, document_type=document_type,
                defaults={'ultimo': 0},
            )
            seq.ultimo += 1
            seq.save(update_fields=['ultimo'])
            return f"{estab}-{pto_emi}-{str(seq.ultimo).zfill(9)}"


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
