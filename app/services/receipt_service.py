"""Bonus feature: PDF rent receipt generation using reportlab."""
import io

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.models.rent import RentInvoice


def build_receipt_pdf(invoice: RentInvoice, tenant_name: str, unit_number: str) -> bytes:
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, height - 25 * mm, "Rent Payment Receipt")

    c.setFont("Helvetica", 11)
    y = height - 40 * mm
    lines = [
        f"Invoice ID: {invoice.id}",
        f"Lease ID: {invoice.lease_id}",
        f"Tenant: {tenant_name}",
        f"Unit: {unit_number}",
        f"Billing Month: {invoice.billing_month}",
        f"Rent Amount: {invoice.rent_amount:.2f}",
        f"Late Fee: {invoice.late_fee:.2f}",
        f"Discount: {invoice.discount:.2f}",
        f"Total Amount: {invoice.total_amount:.2f}",
        f"Due Date: {invoice.due_date}",
        f"Status: {invoice.status.value}",
    ]
    for line in lines:
        c.drawString(20 * mm, y, line)
        y -= 8 * mm

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(20 * mm, 15 * mm, "This is a system-generated receipt.")
    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer.read()
