from django.db import models

class ParameterModel(models.Model):
    tenant_id = models.IntegerField()
    module = models.CharField(max_length=50, db_column='modulo')
    key = models.CharField(max_length=100, db_column='clave')
    value = models.TextField(db_column='valor')

    class Meta:
        app_label = 'parametros'
        db_table = 'parametros'
        unique_together = ('tenant_id', 'module', 'key')

    def __str__(self):
        return f"{self.tenant_id} | {self.module}.{self.key} = {self.value}"

