"""
ReportLab PDF Generation Service for Lab Reports and Payment Receipts.
"""

from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from sqlalchemy.orm import Session

from app.models import Order, Payment, FlagEnum
from app.repositories import SettingRepository
from app.config import get_reports_dir, get_assets_dir


class NumberedCanvas:
    """Two-pass canvas for adding dynamic 'Page X of Y' page numbers."""
    def __init__(self, *args, **kwargs):
        self._saved_page_states = []

    def __call__(self, *args, **kwargs):
        from reportlab.pdfgen import canvas
        class PageNumCanvas(canvas.Canvas):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.pages = []

            def showPage(self):
                self.pages.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                num_pages = len(self.pages)
                for page in self.pages:
                    self.__dict__.update(page)
                    self.draw_page_number(num_pages)
                    super().showPage()
                super().save()

            def draw_page_number(self, page_count):
                self.saveState()
                self.setFont("Helvetica", 8)
                self.setFillColor(colors.HexColor("#555555"))
                page_text = f"Page {self._pageNumber} of {page_count}"
                self.drawRightString(565, 20, page_text)
                self.drawString(30, 20, "Confidential Medical Diagnostic Report - Smart Clinical Lab")
                self.setStrokeColor(colors.HexColor("#CCCCCC"))
                self.setLineWidth(0.5)
                self.line(30, 32, 565, 32)
                self.restoreState()

        return PageNumCanvas(*args, **kwargs)


class ReportService:
    def __init__(self, session: Session):
        self.session = session
        self.setting_repo = SettingRepository(session)

    def generate_patient_report(self, order: Order) -> str:
        reports_dir = get_reports_dir()
        filename = f"Report_{order.order_number}.pdf"
        filepath = reports_dir / filename

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            leftMargin=30,
            rightMargin=30,
            topMargin=30,
            bottomMargin=45
        )

        styles = getSampleStyleSheet()
        normal = styles['Normal']

        # Custom Styles
        style_lab_title = ParagraphStyle('LabTitle', parent=normal, fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#003366'), alignment=TA_LEFT)
        style_lab_sub = ParagraphStyle('LabSub', parent=normal, fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#555555'), alignment=TA_LEFT)
        style_report_header = ParagraphStyle('ReportHeader', parent=normal, fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#003366'), alignment=TA_CENTER)

        style_field_label = ParagraphStyle('FieldLabel', parent=normal, fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.HexColor('#333333'))
        style_field_val = ParagraphStyle('FieldVal', parent=normal, fontName='Helvetica', fontSize=9, leading=11, textColor=colors.HexColor('#111111'))

        style_table_hdr = ParagraphStyle('TableHdr', parent=normal, fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.white)
        style_cell = ParagraphStyle('Cell', parent=normal, fontName='Helvetica', fontSize=9, leading=11, textColor=colors.HexColor('#222222'))
        style_cell_bold = ParagraphStyle('CellBold', parent=normal, fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.HexColor('#222222'))
        style_cell_low = ParagraphStyle('CellLow', parent=normal, fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.HexColor('#0000FF'))
        style_cell_high = ParagraphStyle('CellHigh', parent=normal, fontName='Helvetica-Bold', fontSize=9, leading=11, textColor=colors.HexColor('#CC0000'))

        story = []

        # 1. Laboratory Header
        lab_name = self.setting_repo.get("lab_name", "Smart Clinical Laboratory")
        lab_addr = self.setting_repo.get("lab_address", "Kerala, India")
        lab_phone = self.setting_repo.get("lab_phone", "")
        lab_email = self.setting_repo.get("lab_email", "")

        header_text = f"<b>{lab_name}</b><br/>{lab_addr}<br/>Phone: {lab_phone} | Email: {lab_email}"
        header_p = Paragraph(f"<font size=16 color='#003366'><b>{lab_name}</b></font><br/>{lab_addr}<br/>Phone: {lab_phone} | Email: {lab_email}", style_lab_sub)

        logo_path = self.setting_repo.get("lab_logo_path", "")
        logo_img = None
        if logo_path and Path(logo_path).exists():
            try:
                logo_img = Image(logo_path, width=60, height=60)
            except Exception:
                logo_img = None

        if logo_img:
            hdr_table = Table([[logo_img, header_p]], colWidths=[70, 465])
        else:
            hdr_table = Table([[header_p]], colWidths=[535])

        hdr_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(hdr_table)
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#003366'), spaceAfter=8))

        # Report Title
        report_title = self.setting_repo.get("report_header_title", "DIAGNOSTIC LABORATORY REPORT")
        story.append(Paragraph(f"<b>{report_title}</b>", style_report_header))
        story.append(Spacer(1, 8))

        # 2. Patient & Order Metadata Table
        pat = order.patient
        patient_info = [
            [
                Paragraph("Patient ID:", style_field_label), Paragraph(pat.patient_id, style_field_val),
                Paragraph("Order No:", style_field_label), Paragraph(order.order_number, style_field_val)
            ],
            [
                Paragraph("Patient Name:", style_field_label), Paragraph(f"<b>{pat.full_name}</b>", style_field_val),
                Paragraph("Order Date:", style_field_label), Paragraph(order.order_date.strftime("%Y-%m-%d %H:%M"), style_field_val)
            ],
            [
                Paragraph("Age / Gender:", style_field_label), Paragraph(f"{pat.age or 'N/A'} {pat.age_unit or 'Yrs'} / {pat.gender}", style_field_val),
                Paragraph("Report Date:", style_field_label), Paragraph(datetime.now().strftime("%Y-%m-%d %H:%M"), style_field_val)
            ],
            [
                Paragraph("Phone No:", style_field_label), Paragraph(pat.phone or "N/A", style_field_val),
                Paragraph("Status:", style_field_label), Paragraph(order.status, style_field_val)
            ]
        ]
        info_table = Table(patient_info, colWidths=[80, 187, 80, 188])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F4F6F9')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#D0D7DE')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E1E4E8')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 12))

        # 3. Test Results Table
        table_data = [[
            Paragraph("Test / Parameter Name", style_table_hdr),
            Paragraph("Result", style_table_hdr),
            Paragraph("Unit", style_table_hdr),
            Paragraph("Reference Range", style_table_hdr),
            Paragraph("Flag", style_table_hdr)
        ]]

        for item in order.items:
            # Category / Test Section Header
            table_data.append([
                Paragraph(f"<b>{item.test_name_snapshot.upper()}</b>", style_cell_bold),
                Paragraph("", style_cell),
                Paragraph("", style_cell),
                Paragraph("", style_cell),
                Paragraph("", style_cell)
            ])

            for res in item.results:
                f_style = style_cell
                if res.flag == FlagEnum.LOW.value:
                    f_style = style_cell_low
                elif res.flag == FlagEnum.HIGH.value:
                    f_style = style_cell_high

                table_data.append([
                    Paragraph(f"   {res.parameter_name_snapshot}", style_cell),
                    Paragraph(f"<b>{res.result_value or '-'}</b>", f_style),
                    Paragraph(res.unit_snapshot or "", style_cell),
                    Paragraph(res.reference_range_snapshot or "", style_cell),
                    Paragraph(f"<b>{res.flag if res.flag != FlagEnum.NONE.value else ''}</b>", f_style)
                ])

        res_table = Table(table_data, colWidths=[185, 90, 70, 130, 60])
        res_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003366')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E1E4E8')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(res_table)
        story.append(Spacer(1, 15))

        # 4. Verification Details & Signatures
        verifier_name = "Not Verified"
        verified_time = "N/A"
        for item in order.items:
            for res in item.results:
                if res.is_verified and res.verified_by:
                    verifier_name = res.verified_by.display_name
                    verified_time = res.verified_at.strftime("%Y-%m-%d %H:%M") if res.verified_at else "N/A"
                    break

        sig_data = [
            [
                Paragraph(f"<b>Entered By:</b> {order.created_by.display_name if order.created_by else 'Staff'}", style_field_val),
                Paragraph(f"<b>Verified By:</b> {verifier_name} ({verified_time})", style_field_val)
            ]
        ]
        sig_table = Table(sig_data, colWidths=[267, 268])
        sig_table.setStyle(TableStyle([
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('LINEABOVE', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC'))
        ]))

        footer_note = self.setting_repo.get("report_footer_note", "This report is generated electronically.")
        story.append(KeepTogether([
            sig_table,
            Spacer(1, 10),
            Paragraph(f"<font size=8 color='#666666'><i>{footer_note}</i></font>", style_report_header)
        ]))

        doc.build(story, canvasmaker=NumberedCanvas())
        return str(filepath)

    def generate_receipt_pdf(self, payment: Payment) -> str:
        reports_dir = get_reports_dir()
        filename = f"Receipt_{payment.receipt_number}.pdf"
        filepath = reports_dir / filename

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40
        )

        styles = getSampleStyleSheet()
        normal = styles['Normal']

        style_title = ParagraphStyle('RecTitle', parent=normal, fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=colors.HexColor('#003366'), alignment=TA_CENTER)
        style_lbl = ParagraphStyle('RecLbl', parent=normal, fontName='Helvetica-Bold', fontSize=9, leading=12)
        style_val = ParagraphStyle('RecVal', parent=normal, fontName='Helvetica', fontSize=9, leading=12)

        order = payment.order
        pat = order.patient

        lab_name = self.setting_repo.get("lab_name", "Smart Clinical Laboratory")
        lab_addr = self.setting_repo.get("lab_address", "Kerala, India")
        lab_phone = self.setting_repo.get("lab_phone", "")

        story = [
            Paragraph(f"<b>{lab_name}</b>", style_title),
            Paragraph(f"{lab_addr} | Phone: {lab_phone}", ParagraphStyle('Sub', parent=normal, alignment=TA_CENTER, fontSize=9)),
            Spacer(1, 10),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#003366'), spaceAfter=10),
            Paragraph(f"<b>PAYMENT RECEIPT - {payment.receipt_number}</b>", ParagraphStyle('RecSubTitle', parent=normal, fontName='Helvetica-Bold', fontSize=12, alignment=TA_CENTER, textColor=colors.HexColor('#003366'))),
            Spacer(1, 10),
        ]

        # Info Grid
        rec_info = [
            [Paragraph("Receipt No:", style_lbl), Paragraph(payment.receipt_number, style_val), Paragraph("Payment Date:", style_lbl), Paragraph(payment.payment_date.strftime("%Y-%m-%d %H:%M"), style_val)],
            [Paragraph("Patient ID:", style_lbl), Paragraph(pat.patient_id, style_val), Paragraph("Order No:", style_lbl), Paragraph(order.order_number, style_val)],
            [Paragraph("Patient Name:", style_lbl), Paragraph(pat.full_name, style_val), Paragraph("Payment Method:", style_lbl), Paragraph(payment.payment_method, style_val)],
        ]
        info_t = Table(rec_info, colWidths=[90, 160, 90, 165])
        info_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8F9FA')),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CCCCCC')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#EEEEEE')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(info_t)
        story.append(Spacer(1, 12))

        # Items Table
        items_data = [[Paragraph("<b>Description / Test</b>", style_lbl), Paragraph("<b>Amount (INR)</b>", style_lbl)]]
        for item in order.items:
            items_data.append([Paragraph(item.test_name_snapshot, style_val), Paragraph(f"{item.price_snapshot:.2f}", style_val)])

        items_data.append([Paragraph("<b>Total Amount:</b>", style_lbl), Paragraph(f"<b>{order.total_amount:.2f}</b>", style_val)])
        items_data.append([Paragraph("<b>Amount Paid This Receipt:</b>", style_lbl), Paragraph(f"<b>{payment.amount:.2f}</b>", style_val)])
        items_data.append([Paragraph("<b>Total Paid So Far:</b>", style_lbl), Paragraph(f"<b>{order.paid_amount:.2f}</b>", style_val)])
        items_data.append([Paragraph("<b>Balance Remaining:</b>", style_lbl), Paragraph(f"<b>{max(0.0, order.total_amount - order.paid_amount):.2f}</b>", style_val)])

        items_t = Table(items_data, colWidths=[350, 155])
        items_t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E9ECEF')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#DDDDDD')),
            ('TOPPADDING', (0,0), (-1,-1), 4),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(items_t)
        story.append(Spacer(1, 20))

        story.append(Paragraph("Thank you for choosing Smart Clinical Laboratory.", ParagraphStyle('Thx', parent=normal, alignment=TA_CENTER, fontName='Helvetica-Oblique', fontSize=9)))

        doc.build(story)
        return str(filepath)
