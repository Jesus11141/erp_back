from ..domain.repositories import UserRepository
from ..domain.entities import User

class CreateUser:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def execute(self, tenant_id: int, name: str, email: str, password: str, role: str) -> User:
        existing = self.repo.find_by_email(email, tenant_id)
        if existing:
            raise ValueError("A user with that email already exists")
        user = User(id=0, tenant_id=tenant_id, name=name, email=email, role=role)
        return self.repo.save(user, password)


