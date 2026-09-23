from ..domain.repositories import InvoiceRepository

class ListInvoices:
    def __init__(self, repo: InvoiceRepository):
        self.repo = repo

    def execute(self, tenant_id: int, page: int = 1, limit: int = 10) -> dict:
        return self.repo.list_by_tenant(tenant_id, page, limit)
