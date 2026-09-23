from django.db import models

class AuditLogModel(models.Model):
    tenant_id = models.IntegerField(null=True, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    table_name = models.CharField(max_length=100)
    record_id = models.CharField(max_length=100)
    action = models.CharField(max_length=20) # CREATE, UPDATE, DELETE
    changes = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'auditoria'
        db_table = 'audit_logs'
        ordering = ['-created_at']
