from ..domain.repositories import UserRepository
from ..domain.entities import User


class LoginUser:
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def execute(self, email: str, password: str, tenant_id: int) -> User:
        if not self.repo.verify_password(email, tenant_id, password):
            raise PermissionError("Credenciales incorrectas")
        user = self.repo.find_by_email(email, tenant_id)
        if not user or not user.is_active:
            raise PermissionError("Usuario inactivo o no encontrado")
        return user


