"""
Firmado de XML con certificado P12 (XAdES-BES) para SRI Ecuador
Requiere: pip install xades lxml cryptography
"""
from lxml import etree

def sign_xml(xml_str: str, p12_path: str, p12_password: str) -> str:
    """
    Firma el XML con el certificado P12 usando XAdES-BES
    Retorna el XML firmado como string
    """
    try:
        from xades import XAdESContext, template
        from xades.policy import GenericPolicyId
        from OpenSSL.crypto import load_pkcs12, FILETYPE_ASN1
        import base64
        from cryptography.hazmat.primitives.serialization import pkcs12 as crypto_pkcs12
        from cryptography.hazmat.backends import default_backend

        with open(p12_path, 'rb') as f:
            p12_data = f.read()

        password = p12_password.encode() if isinstance(p12_password, str) else p12_password

        private_key, certificate, chain = crypto_pkcs12.load_key_and_certificates(
            p12_data, password, default_backend()
        )

        root = etree.fromstring(xml_str.encode('utf-8'))
        ctx = XAdESContext()
        ctx.load_pkcs12_from_data(p12_data, password)
        ctx.sign(root)

        return etree.tostring(root, encoding='unicode', xml_declaration=False)

    except ImportError as e:
        raise ValueError(
            f'Librerías de firma no instaladas: {e}. '
            'Ejecuta: pip install xades lxml cryptography pyOpenSSL'
        )
    except Exception as e:
        raise ValueError(f'Error al firmar XML: {str(e)}')


def firmar_xml_simple(xml_str: str, p12_path: str, p12_password: str) -> str:
    """
    Firmado simplificado usando subprocess con la herramienta sri-firma
    Alternativa si xades no está disponible
    """
    import subprocess
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
        f.write(xml_str)
        xml_tmp = f.name

    out_tmp = xml_tmp.replace('.xml', '_firmado.xml')

    try:
        result = subprocess.run(
            ['java', '-jar', 'sri-firma.jar', xml_tmp, p12_path, p12_password, out_tmp],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and os.path.exists(out_tmp):
            with open(out_tmp, 'r', encoding='utf-8') as f:
                return f.read()
        raise ValueError(f'Error en firma: {result.stderr}')
    finally:
        for f in [xml_tmp, out_tmp]:
            if os.path.exists(f):
                os.unlink(f)
