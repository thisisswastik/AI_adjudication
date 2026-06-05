import os
import json
import logging
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEST_DATA_DIR = "c:/Users/swastik/Desktop/plum/test_data"
os.makedirs(TEST_DATA_DIR, exist_ok=True)

def generate_prescription_pdf(case_id: str, patient_name: str, date_str: str, rx_data: dict, output_path: str):
    """Generates a professional mock doctor's prescription PDF."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'ClinicTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1E3A8A'),
        alignment=1 # Center
    )
    
    doctor_style = ParagraphStyle(
        'DoctorMeta',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#374151')
    )
    
    meta_style = ParagraphStyle(
        'ClinicMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#6B7280'),
        alignment=1
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=12,
        spaceAfter=6
    )
    
    body_style = ParagraphStyle(
        'RxBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1E293B')
    )

    # 1. Clinic Header
    clinic_name = rx_data.get("hospital_clinic_name", "TechCorp Wellness Clinic & Hospital")
    story.append(Paragraph(clinic_name, title_style))
    
    doc_name = rx_data.get("doctor_name", "Dr. Sharma")
    doc_reg = rx_data.get("doctor_reg", "KA/45678/2015")
    story.append(Spacer(1, 4))
    
    # Doctor info table (Doctor Name on Left, Reg No on Right)
    hdr_data = [
        [Paragraph(f"<b>Physician:</b> {doc_name}", doctor_style), Paragraph(f"<b>Reg No:</b> {doc_reg}", doctor_style)],
        [Paragraph("12, Richmond Road, Bangalore - 560025", meta_style), Paragraph("Phone: +91 80 4918 2000", meta_style)]
    ]
    hdr_table = Table(hdr_data, colWidths=[3.5*inch, 3.5*inch])
    hdr_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LINEBELOW', (0,1), (1,1), 1, colors.HexColor('#CBD5E1'))
    ]))
    story.append(hdr_table)
    story.append(Spacer(1, 15))

    # 2. Patient Details Table
    pat_data = [
        [Paragraph(f"<b>Patient Name:</b> {patient_name}", body_style), Paragraph(f"<b>Date:</b> {date_str}", body_style)],
        [Paragraph("<b>Age / Sex:</b> 32 / Male", body_style), Paragraph("<b>Ref:</b> Direct Walk-in", body_style)]
    ]
    pat_table = Table(pat_data, colWidths=[3.5*inch, 3.5*inch])
    pat_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LINEBELOW', (0,1), (1,1), 0.5, colors.HexColor('#E2E8F0'))
    ]))
    story.append(pat_table)
    story.append(Spacer(1, 15))

    # 3. Diagnosis Section
    diagnosis = rx_data.get("diagnosis", "Viral fever")
    story.append(Paragraph("Chief Complaints & Diagnosis", section_heading))
    story.append(Paragraph(f"Patient presented with complaints of acute symptoms. <br/><b>Diagnosis:</b> {diagnosis}", body_style))
    story.append(Spacer(1, 12))

    # 4. Rx (Prescription) Section
    story.append(Paragraph("Rx (Prescribed Medications & Treatment)", section_heading))
    
    rx_items = rx_data.get("medicines_prescribed", [])
    procedures = rx_data.get("procedures", [])
    
    rx_list_html = ""
    if rx_items:
        for idx, med in enumerate(rx_items, 1):
            rx_list_html += f"{idx}. Tab. {med} - 1 tablet three times daily x 5 days<br/>"
    elif procedures:
        for idx, proc in enumerate(procedures, 1):
            rx_list_html += f"{idx}. Recommended Procedure: {proc}<br/>"
    else:
        rx_list_html = "No medicines or procedures listed."
        
    story.append(Paragraph(rx_list_html, body_style))
    story.append(Spacer(1, 15))

    # 5. Investigations Section
    tests = rx_data.get("tests_prescribed", []) or rx_data.get("tests_recommended", [])
    if tests:
        story.append(Paragraph("Investigations / Diagnostic Tests Advised", section_heading))
        test_html = ""
        for t in tests:
            test_html += f"- {t}<br/>"
        story.append(Paragraph(test_html, body_style))
        story.append(Spacer(1, 20))

    # 6. Sign-off
    story.append(Spacer(1, 30))
    sig_data = [
        ["", Paragraph("______________________", doctor_style)],
        ["", Paragraph("Authorized Signature & Stamp", meta_style)]
    ]
    sig_table = Table(sig_data, colWidths=[4.5*inch, 2.5*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(sig_table)

    doc.build(story)


def generate_bill_pdf(case_id: str, patient_name: str, date_str: str, bill_data: dict, output_path: str):
    """Generates a professional mock medical billing invoice PDF."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'BillTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#111827')
    )
    
    meta_style = ParagraphStyle(
        'BillMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#4B5563')
    )
    
    table_hdr = ParagraphStyle(
        'TableHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.white
    )
    
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1F2937')
    )

    # 1. Header
    story.append(Paragraph("INVOICE / BILL RECEIPT", title_style))
    story.append(Spacer(1, 4))
    
    # Clinic details & invoice metadata
    inv_no = f"INV-2024-{case_id}"
    hdr_data = [
        [Paragraph("<b>TechCorp Wellness Center</b><br/>Bangalore, India", meta_style), 
         Paragraph(f"<b>Invoice No:</b> {inv_no}<br/><b>Date:</b> {date_str}", meta_style)]
    ]
    hdr_table = Table(hdr_data, colWidths=[4.0*inch, 3.0*inch])
    hdr_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LINEBELOW', (0,0), (-1,0), 1, colors.HexColor('#E5E7EB'))
    ]))
    story.append(hdr_table)
    story.append(Spacer(1, 15))

    # 2. Patient Details
    pat_data = [
        [Paragraph(f"<b>Bill To Patient:</b> {patient_name}", meta_style), Paragraph(f"<b>Referred By:</b> Dr. Sharma", meta_style)]
    ]
    pat_table = Table(pat_data, colWidths=[4.0*inch, 3.0*inch])
    pat_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10)
    ]))
    story.append(pat_table)
    story.append(Spacer(1, 10))

    # 3. Particulars Table
    grid_data = [[Paragraph("<b>S.No</b>", table_hdr), Paragraph("<b>Particulars / Service</b>", table_hdr), Paragraph("<b>Amount (₹)</b>", table_hdr)]]
    
    s_no = 1
    total_calc = 0.0
    
    for item_key, val in bill_data.items():
        if item_key in ["claim_amount", "cashless_approved", "network_discount", "test_names"]:
            continue
        description = item_key.replace("_", " ").title()
        amount = float(val)
        total_calc += amount
        grid_data.append([
            Paragraph(str(s_no), table_cell),
            Paragraph(description, table_cell),
            Paragraph(f"₹ {amount:,.2f}", table_cell)
        ])
        s_no += 1
        
    # Append Total row
    grid_data.append([
        "",
        Paragraph("<b>TOTAL AMOUNT DUE</b>", table_cell),
        Paragraph(f"<b>₹ {total_calc:,.2f}</b>", table_cell)
    ])
    
    t = Table(grid_data, colWidths=[0.8*inch, 4.2*inch, 2.0*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E3A8A')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-2), 0.5, colors.HexColor('#E5E7EB')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#F3F4F6')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # 4. Signature block
    story.append(Spacer(1, 30))
    sig_data = [
        [Paragraph("Thank you for choosing TechCorp Wellness.", meta_style), Paragraph("______________________", table_cell)],
        ["", Paragraph("Billing Department Sign", meta_style)]
    ]
    sig_table = Table(sig_data, colWidths=[4.0*inch, 3.0*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
    ]))
    story.append(sig_table)

    doc.build(story)


def generate_all_mock_documents():
    """Reads test_cases.json and creates mock files for all cases in workspace."""
    test_cases_path = "c:/Users/swastik/Desktop/plum/test_cases.json"
    if not os.path.exists(test_cases_path):
        logger.error(f"Cannot generate mock documents - test_cases.json not found at {test_cases_path}")
        return
        
    with open(test_cases_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    test_cases = data.get("test_cases", [])
    logger.info(f"Generating mock PDFs for {len(test_cases)} test cases...")
    
    for tc in test_cases:
        case_id = tc["case_id"]
        patient_name = tc["input_data"]["member_name"]
        date_str = tc["input_data"]["treatment_date"]
        docs = tc["input_data"].get("documents", {})
        
        case_dir = os.path.join(TEST_DATA_DIR, case_id)
        os.makedirs(case_dir, exist_ok=True)
        
        # 1. Prescription PDF
        rx_data = docs.get("prescription")
        if rx_data:
            # Inject hospital name/details from test case if available
            rx_data["hospital_clinic_name"] = tc["input_data"].get("hospital", "TechCorp Wellness Clinic")
            rx_path = os.path.join(case_dir, f"{case_id}_prescription.pdf")
            generate_prescription_pdf(case_id, patient_name, date_str, rx_data, rx_path)
            logger.info(f"Generated prescription: {rx_path}")
            
        # 2. Bill PDF
        bill_data = docs.get("bill")
        if bill_data:
            bill_path = os.path.join(case_dir, f"{case_id}_bill.pdf")
            generate_bill_pdf(case_id, patient_name, date_str, bill_data, bill_path)
            logger.info(f"Generated bill: {bill_path}")
            
    logger.info("Mock document generation completed.")

if __name__ == "__main__":
    generate_all_mock_documents()
