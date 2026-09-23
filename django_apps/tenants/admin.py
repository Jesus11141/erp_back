from django.contrib import admin
from .models import TenantModel, TenantModuloModel

class TenantModuloInline(admin.TabularInline):
    model = TenantModuloModel
    extra = 1

@admin.register(TenantModel)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'subdomain', 'is_active', 'created')
    search_fields = ('name', 'subdomain')
    list_filter = ('is_active',)
    inlines = [TenantModuloInline]
