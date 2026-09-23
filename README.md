# ERP Backend — API & Core Services

Backend robusto para ERP multi-empresa (SaaS), desarrollado con **Python**, **Django REST Framework** y arquitectura **DDD / Hexagonal**. Incluye facturación electrónica nativa con el **SRI de Ecuador**, inventario multi-sucursal, punto de venta (POS), contabilidad y bot de sincronización tributaria.

---

## 🚀 Inicio Rápido en GitHub Codespaces / Entorno Local

Al abrir este repositorio en **GitHub Codespaces** o en tu máquina local:

### 1. Crear y activar entorno virtual
```bash
python -m venv venv
# En Linux / Codespaces / MacOS:
source venv/bin/activate
# En Windows PowerShell:
.\venv\Scripts\Activate.ps1
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Copia la plantilla `.env.example` a `.env`:
```bash
cp .env.example .env
```
*(Para desarrollo rápido con SQLite, puedes usar el motor de base de datos por defecto de Django).*

### 4. Ejecutar migraciones
```bash
python manage.py migrate
```

### 5. Iniciar servidor de desarrollo
```bash
python manage.py runserver 0.0.0.0:8000
```

El servidor estará escuchando en `http://localhost:8000/` (o en el puerto 8000 reenviado en Codespaces).

---

## 📁 Estructura del Proyecto

* **`core/`**: Configuración central de Django (settings, urls principales, wsgi/asgi, middlewares de autenticación y multi-tenant).
* **`modules/`**: Módulos de dominio y aplicación (Arquitectura DDD):
  * `accounting/`: Bot del SRI (scraping con Selenium de comprobantes recibidos/emitidos y cliente SOAP).
  * `contabilidad/`: Plan de cuentas, asientos, libro diario, libro mayor, balance general y estado de resultados (P&L).
  * `facturacion/`: Facturación electrónica, notas de crédito, firma `.p12`, XML y autorización SRI.
  * `inventario/`: Catálogo de productos, control de stock por sucursal, kardex y traspasos entre bodegas.
  * `pos/`: Punto de venta, control de cajas físicas/virtuales, arqueo y turnos.
  * `ventas/`: Clientes, cotizaciones/proformas y cuentas por cobrar.
  * `rrhh/`: Nóminas, empleados y cargos.
  * `restaurantes/`: Control de mesas y comandas.
  * `technical_service/`: Órdenes de servicio técnico y reparación.
* **`django_apps/`**: Modelos ORM y migraciones de persistencia.
* **`shared/`**: Utilidades compartidas, decoradores y excepciones de dominio.

---

## 🛠️ Tecnologías Principales
* **Python 3.12+**
* **Django 5.2 & Django REST Framework**
* **SimpleJWT** (Autenticación por Tokens Bearer)
* **PostgreSQL / SQLite**
* **ReportLab** (Generación de RIDE / PDF)
* **Cryptography & LXML** (Firma electrónica XAdES-BES y validación de esquemas XML del SRI)
* **Selenium** (Automatización del portal SRI en línea)
