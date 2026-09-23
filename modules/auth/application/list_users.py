from ..domain.repositories import UserRepository
from ..domain.entities import User


class ListUsers:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def execute(self, tenant_id: int) -> list:
        return self.repo.list_by_tenant(tenant_id)


