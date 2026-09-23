import json
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from django.db.models.fields.files import FieldFile

from .django_models import AuditLogModel
from core.middleware.current_request import get_current_user_id, get_current_tenant_id, get_current_ip

# Critical models to audit
from modules.inventario.infrastructure.django_models import ProductModel
from modules.pos.infrastructure.django_models import POSSaleModel
from modules.tax_documents.invoicing.infrastructure.persistence.django_models import InvoiceModel
from modules.contabilidad.infrastructure.django_models import JournalEntryModel
from modules.ventas.infrastructure.django_models import CustomerModel

AUDITED_MODELS = [ProductModel, POSSaleModel, InvoiceModel, JournalEntryModel, CustomerModel]

def get_model_name(instance):
    return instance.__class__.__name__

def get_diff(old_dict, new_dict):
    diff = {}
    for key, new_val in new_dict.items():
        old_val = old_dict.get(key)
        if old_val != new_val:
            diff[key] = {'old': old_val, 'new': new_val}
    return diff

def sanitize_for_json(data):
    """Recursively convert non-serializable Django field values (e.g. ImageFieldFile) to safe types."""
    if isinstance(data, dict):
        return {k: sanitize_for_json(v) for k, v in data.items()}
    if isinstance(data, list):
        return [sanitize_for_json(v) for v in data]
    if isinstance(data, FieldFile):
        # Convert ImageFieldFile / FileFieldFile to its name string or None
        return str(data) if data else None
    return data

class AuditEncoder(DjangoJSONEncoder):
    """DjangoJSONEncoder extended to handle FieldFile/ImageFieldFile objects."""
    def default(self, o):
        if isinstance(o, FieldFile):
            return str(o) if o else None
        return super().default(o)

@receiver(pre_save)
def capture_old_state(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            instance._old_state = sanitize_for_json(model_to_dict(old_instance))
        except sender.DoesNotExist:
            instance._old_state = {}
    else:
        instance._old_state = {}

@receiver(post_save)
def audit_post_save(sender, instance, created, **kwargs):
    if sender not in AUDITED_MODELS:
        return
        
    user_id = get_current_user_id()
    tenant_id = get_current_tenant_id()
    ip = get_current_ip()
    
    # Optional: if no user is present, and we only want to audit user actions, we could return.
    # But system actions might also be useful to audit.
    
    new_state = sanitize_for_json(model_to_dict(instance))
    old_state = getattr(instance, '_old_state', {})
    
    if created:
        action = 'CREATE'
        changes = new_state
    else:
        action = 'UPDATE'
        changes = get_diff(old_state, new_state)
        if not changes:
            return # No actual fields changed
            
    # Serialize to clean up Decimals/Dates
    changes_json = json.loads(json.dumps(changes, cls=AuditEncoder))
    
    AuditLogModel.objects.create(
        tenant_id=tenant_id or getattr(instance, 'tenant_id', None),
        user_id=user_id,
        table_name=get_model_name(instance),
        record_id=str(instance.pk),
        action=action,
        changes=changes_json,
        ip_address=ip
    )

@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    if sender not in AUDITED_MODELS:
        return
        
    user_id = get_current_user_id()
    tenant_id = get_current_tenant_id()
    ip = get_current_ip()
    
    old_state = sanitize_for_json(model_to_dict(instance))
    changes_json = json.loads(json.dumps(old_state, cls=AuditEncoder))
    
    AuditLogModel.objects.create(
        tenant_id=tenant_id or getattr(instance, 'tenant_id', None),
        user_id=user_id,
        table_name=get_model_name(instance),
        record_id=str(instance.pk),
        action='DELETE',
        changes=changes_json,
        ip_address=ip
    )
