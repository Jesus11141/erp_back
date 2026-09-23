"""
Utilidades de cifrado simétrico para datos sensibles (ej: contraseñas de certificados).
Usa Fernet (AES-128-CBC + HMAC-SHA256) derivado de la SECRET_KEY de Django.
"""
import base64
import hashlib
from django.conf import settings


def _get_fernet():
    from cryptography.fernet import Fernet
    # Derivar una clave Fernet de 32 bytes desde SECRET_KEY
    clave = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(clave))


def cifrar(texto: str) -> str:
    """Cifra un texto plano y retorna el token cifrado como string."""
    return _get_fernet().encrypt(texto.encode()).decode()


def descifrar(token: str) -> str:
    """Descifra un token y retorna el texto plano original."""
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except Exception:
        # Si el token no es válido (ej: dato legacy sin cifrar), retornarlo tal cual
        return token
