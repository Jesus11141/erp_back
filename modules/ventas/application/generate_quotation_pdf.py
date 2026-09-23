import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from ..domain.entities import Quotation
from modules.tenants.infrastructure.django_models import TenantModel

class GenerateQuotationPdf:
    def execute(self, quotation: Quotation) -> bytes:
        # Recuperar datos del Tenant para membrete
        tenant = TenantModel.objects.get(id=quotation.tenant_id)
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Estilo de impresión (corporativo, ejecutivo, etc.)
        style = quotation.print_style

        # DIBUJAR CABECERA
        if style == 'corporativo':
            c.setFillColor(HexColor('#2c3e50'))
            c.rect(0, height - 100, width, 100, fill=1)
            c.setFillColor(HexColor('#ffffff'))
            c.setFont("Helvetica-Bold", 24)
            c.drawString(40, height - 50, tenant.name.upper())
            c.setFont("Helvetica", 12)
            c.drawString(40, height - 70, f"COTIZACIÓN #{quotation.id}")
            # Color para el texto siguiente
            c.setFillColor(HexColor('#333333'))
            y_start = height - 130
        elif style == 'ejecutivo':
            c.setFillColor(HexColor('#333333'))
            c.setFont("Times-Bold", 24)
            c.drawString(40, height - 60, tenant.name)
            c.setStrokeColor(HexColor('#333333'))
            c.line(40, height - 70, width - 40, height - 70)
            c.setFont("Times-Roman", 14)
            c.drawString(40, height - 90, f"Propuesta Comercial - Cotización N° {quotation.id}")
            y_start = height - 130
        else:
            # Simple por defecto
            c.setFont("Helvetica-Bold", 20)
            c.drawString(40, height - 50, tenant.name)
            c.setFont("Helvetica", 14)
            c.drawString(40, height - 70, f"Cotización #{quotation.id}")
            y_start = height - 110
            c.setFillColor(HexColor('#000000'))

        # DATOS DEL CLIENTE
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40, y_start, "Datos del Cliente:")
        c.setFont("Helvetica", 11)
        c.drawString(40, y_start - 20, f"Nombre: {quotation.customer_name}")
        c.drawString(40, y_start - 35, f"Fecha: {quotation.date.strftime('%Y-%m-%d')}")
        
        if quotation.validity_days:
            c.drawString(40, y_start - 50, f"Validez de la oferta: {quotation.validity_days} días")

        y = y_start - 90

        # CABECERA DE TABLA DE PRODUCTOS
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(HexColor('#ecf0f1') if style == 'corporativo' else HexColor('#f9f9f9'))
        c.rect(40, y - 5, width - 80, 20, fill=1)
        c.setFillColor(HexColor('#333333'))
        c.drawString(45, y, "Descripción")
        c.drawString(300, y, "Cant.")
        c.drawString(380, y, "P. Unit")
        c.drawString(480, y, "Total")
        
        y -= 25

        # ITEMS
        c.setFont("Helvetica", 10)
        for item in quotation.items:
            c.drawString(45, y, str(item.description)[:40])
            c.drawString(300, y, str(item.quantity))
            c.drawString(380, y, f"${item.unit_price:.2f}")
            c.drawString(480, y, f"${item.subtotal:.2f}")
            y -= 20
            if y < 150:
                c.showPage()
                y = height - 50

        # TOTALES
        y -= 20
        c.setFont("Helvetica-Bold", 11)
        c.drawString(380, y, "Subtotal:")
        c.drawString(480, y, f"${quotation.subtotal:.2f}")
        y -= 20
        c.drawString(380, y, "IVA:")
        c.drawString(480, y, f"${quotation.vat_amount:.2f}")
        y -= 20
        c.drawString(380, y, "TOTAL:")
        c.drawString(480, y, f"${quotation.total:.2f}")

        y -= 50

        # TÉRMINOS Y CONDICIONES (Si existen)
        if quotation.payment_terms or quotation.delivery_time or quotation.notes:
            c.setFont("Helvetica-Bold", 11)
            c.drawString(40, y, "Términos y Condiciones:")
            y -= 20
            c.setFont("Helvetica", 10)
            if quotation.payment_terms:
                c.drawString(40, y, f"• Forma de Pago: {quotation.payment_terms}")
                y -= 15
            if quotation.delivery_time:
                c.drawString(40, y, f"• Tiempo de Entrega: {quotation.delivery_time}")
                y -= 15
            if quotation.notes:
                c.drawString(40, y, f"• Notas Adicionales: {quotation.notes}")
                y -= 15

        # FIRMAS (Estilo Ejecutivo)
        if style == 'ejecutivo':
            y -= 60
            c.setStrokeColor(HexColor('#666666'))
            c.line(40, y, 200, y)
            c.line(width - 240, y, width - 80, y)
            y -= 15
            c.setFont("Helvetica", 10)
            c.drawString(70, y, "Firma Empresa")
            c.drawString(width - 200, y, "Firma Cliente (Aceptación)")

        # PIE DE PÁGINA
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColor(HexColor('#7f8c8d'))
        c.drawString(40, 30, f"Documento generado por {tenant.name} - ERP System")

        c.save()
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
