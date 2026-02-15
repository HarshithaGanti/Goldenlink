from flask import Flask, render_template, request, jsonify, session, send_file
import re
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfgen import canvas
import os
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

app = Flask(__name__)
app.secret_key = 'your-secret-key-here-change-this'

# Simple AI processing (keyword-based)
def process_transcript_with_ai(transcript, emergency_type):
    text = transcript.lower()
    
    report = {
        'emergency_type': emergency_type,
        'symptoms': [],
        'history': [],
        'procedures': [],
        'cautions': []
    }
    
    # Extract symptoms
    if 'chest pain' in text:
        report['symptoms'].append('Chest pain')
    if 'difficulty breathing' in text or 'breathless' in text or 'short of breath' in text:
        report['symptoms'].append('Difficulty breathing')
    if 'unconscious' in text or 'loss of consciousness' in text:
        report['symptoms'].append('Loss of consciousness')
    if 'bleeding' in text:
        report['symptoms'].append('Bleeding')
    if 'dizzy' in text or 'dizziness' in text:
        report['symptoms'].append('Dizziness')
    if 'nausea' in text or 'vomiting' in text:
        report['symptoms'].append('Nausea/Vomiting')
    if 'pain' in text and 'chest pain' not in text:
        report['symptoms'].append('Pain reported')
    if 'fever' in text:
        report['symptoms'].append('Fever')
    if 'headache' in text:
        report['symptoms'].append('Headache')
    
    # Extract medical history
    if 'diabetes' in text or 'diabetic' in text:
        report['history'].append('Diabetes')
    if 'hypertension' in text or 'high blood pressure' in text or 'bp' in text:
        report['history'].append('Hypertension')
    if 'heart disease' in text or 'cardiac' in text:
        report['history'].append('Heart disease')
    if 'asthma' in text:
        report['history'].append('Asthma')
    if 'stroke' in text and emergency_type != 'Stroke':
        report['history'].append('Previous stroke')
    if 'kidney' in text:
        report['history'].append('Kidney disease')
    if 'liver' in text:
        report['history'].append('Liver disease')
    
    # Extract medications
    if 'aspirin' in text:
        report['history'].append('Taking aspirin')
    if 'insulin' in text:
        report['history'].append('Taking insulin')
    if 'metformin' in text:
        report['history'].append('Taking metformin')
    if 'warfarin' in text or 'blood thinner' in text:
        report['history'].append('Taking blood thinners')
    if 'statin' in text:
        report['history'].append('Taking statins')
    
    # Extract procedures
    if 'oxygen' in text:
        report['procedures'].append('Oxygen administered')
    if 'cpr' in text or 'chest compression' in text:
        report['procedures'].append('CPR performed')
    if 'bandage' in text or 'dressing' in text or 'wound care' in text:
        report['procedures'].append('Wound dressing applied')
    if 'iv' in text or 'intravenous' in text or 'drip' in text:
        report['procedures'].append('IV line established')
    if 'aed' in text or 'defibrillator' in text:
        report['procedures'].append('AED/Defibrillator used')
    if 'splint' in text or 'immobiliz' in text:
        report['procedures'].append('Limb immobilization')
    
    # Generate AI cautions
    if 'chest pain' in [s.lower() for s in report['symptoms']]:
        report['cautions'].append('Possible cardiac event - prepare ECG and cardiac monitoring')
    
    if 'Taking aspirin' in report['history'] or 'Taking blood thinners' in report['history']:
        report['cautions'].append('Patient on anticoagulants - monitor for bleeding, avoid additional blood thinners')
    
    if 'Difficulty breathing' in report['symptoms'] and 'Asthma' in report['history']:
        report['cautions'].append('Asthma exacerbation - have bronchodilators and nebulizer ready')
    
    if 'Diabetes' in report['history']:
        report['cautions'].append('Check blood glucose levels immediately')
    
    if emergency_type == 'Stroke' or 'stroke' in text:
        report['cautions'].append('Time-sensitive condition - note exact symptom onset time')
    
    if 'Loss of consciousness' in report['symptoms']:
        report['cautions'].append('Airway management priority - prepare for intubation if needed')
    
    if emergency_type == 'Trauma/Accident':
        report['cautions'].append('Check for internal injuries, maintain spinal precautions')
    
    # Add default messages if empty
    if not report['symptoms']:
        report['symptoms'].append('No specific symptoms identified from transcript')
    if not report['history']:
        report['history'].append('No medical history mentioned')
    if not report['procedures']:
        report['procedures'].append('No procedures documented')
    if not report['cautions']:
        report['cautions'].append('No specific cautions generated')
    
    return report

def generate_pdf(hospital, patient_data, emergency_type, report_data):
    """Generate PDF report"""
    buffer = io.BytesIO()
    
    # Create PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#DC2626'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#374151'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = styles['Normal']
    
    # Title
    title = Paragraph("<font color='#FFD700'>Golden</font><font color='#000000'>Link</font>", title_style)
    elements.append(title)
    
    subtitle = Paragraph("Emergency Report", styles['Heading2'])
    elements.append(subtitle)
    elements.append(Spacer(1, 12))
    
    # Hospital and timestamp
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    elements.append(Paragraph(f"<b>Hospital:</b> {hospital}", normal_style))
    elements.append(Paragraph(f"<b>Generated:</b> {timestamp}", normal_style))
    elements.append(Spacer(1, 20))
    
    # Patient Information Section
    elements.append(Paragraph("Patient Information", heading_style))
    
    patient_info = [
        ['Field', 'Value'],
        ['Name', patient_data.get('name', 'Not provided')],
        ['Age', patient_data.get('age', 'Not provided')],
        ['Gender', patient_data.get('gender', 'Not provided')],
        ['Blood Group', patient_data.get('bloodGroup', 'Not provided')],
        ['Contact', patient_data.get('contact', 'Not provided')]
    ]
    
    patient_table = Table(patient_info, colWidths=[2*inch, 4*inch])
    patient_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DC2626')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')])
    ]))
    
    elements.append(patient_table)
    elements.append(Spacer(1, 30))
    
    # Emergency Report Section
    elements.append(Paragraph("Emergency Report", heading_style))
    
    report_info = [
        ['Section', 'Details'],
        ['Emergency Type', emergency_type],
        ['Current Symptoms', '\n'.join(['• ' + s for s in report_data['symptoms']])],
        ['History/Medication', '\n'.join(['• ' + h for h in report_data['history']])],
        ['Procedures Followed', '\n'.join(['• ' + p for p in report_data['procedures']])],
        ['AI Cautionary Note', '\n'.join(['⚠️ ' + c for c in report_data['cautions']])]
    ]
    
    report_table = Table(report_info, colWidths=[2*inch, 4*inch])
    report_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#DC2626')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F9FAFB')]),
        ('TEXTCOLOR', (1, 5), (1, 5), colors.HexColor('#DC2626'))
    ]))
    
    elements.append(report_table)
    elements.append(Spacer(1, 30))
    
    # Footer
    footer_text = "This report was generated by GoldenLink Pre-Hospital Emergency Reporting System"
    footer = Paragraph(footer_text, ParagraphStyle('Footer', parent=styles['Normal'], 
                                                   fontSize=8, textColor=colors.grey, 
                                                   alignment=TA_CENTER))
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    return pdf_data

def send_email_with_pdf(recipient_email, hospital, pdf_data, patient_name):
    """Send email with PDF attachment"""
    
    # Email configuration - UPDATE THESE WITH YOUR DETAILS
    sender_email = "your-email@gmail.com"  # Change this
    sender_password = "your-app-password"   # Change this (use App Password for Gmail)
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = f"Emergency Report - {patient_name or 'Patient'} - {hospital}"
    
    # Email body
    body = f"""
    Emergency Report Generated
    
    Hospital: {hospital}
    Patient: {patient_name or 'Not provided'}
    Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
    
    Please find the detailed emergency report attached.
    
    ---
    GoldenLink Pre-Hospital Emergency Reporting System
    """
    
    msg.attach(MIMEText(body, 'plain'))
    
    # Attach PDF
    pdf_attachment = MIMEApplication(pdf_data, _subtype='pdf')
    pdf_attachment.add_header('Content-Disposition', 'attachment', 
                            filename=f'Emergency_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf')
    msg.attach(pdf_attachment)
    
    try:
        # Send email (Gmail example)
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/patient-form')
def patient_form():
    hospital = request.args.get('hospital', 'Hospital')
    session['hospital'] = hospital
    return render_template('patient_form.html', hospital=hospital)

@app.route('/emergency-type', methods=['GET', 'POST'])
def emergency_type():
    if request.method == 'POST':
        data = request.get_json()
        session['patient_data'] = data
    
    hospital = session.get('hospital', 'Hospital')
    return render_template('emergency_type.html', hospital=hospital)

@app.route('/voice-recording')
def voice_recording():
    hospital = session.get('hospital', 'Hospital')
    emergency_type = request.args.get('type', 'Unknown')
    patient_data = session.get('patient_data', {})
    
    return render_template('voice_recording.html', 
                         hospital=hospital, 
                         emergency_type=emergency_type,
                         patient_data=patient_data)

@app.route('/process-transcript', methods=['POST'])
def process_transcript():
    data = request.get_json()
    transcript = data.get('transcript', '')
    emergency_type = data.get('emergency_type', 'Unknown')
    
    report = process_transcript_with_ai(transcript, emergency_type)
    
    # Store report in session for PDF generation
    session['report_data'] = report
    session['emergency_type'] = emergency_type
    
    return jsonify(report)

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf_route():
    """Generate and download PDF"""
    hospital = session.get('hospital', 'Hospital')
    patient_data = session.get('patient_data', {})
    emergency_type = session.get('emergency_type', 'Unknown')
    report_data = session.get('report_data', {})
    
    pdf_data = generate_pdf(hospital, patient_data, emergency_type, report_data)
    
    # Save to temporary buffer
    buffer = io.BytesIO(pdf_data)
    buffer.seek(0)
    
    filename = f"Emergency_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@app.route('/send-email', methods=['POST'])
def send_email_route():
    """Send email with PDF"""
    data = request.get_json()
    recipient_email = data.get('email')
    
    if not recipient_email:
        return jsonify({'success': False, 'message': 'Email address required'})
    
    hospital = session.get('hospital', 'Hospital')
    patient_data = session.get('patient_data', {})
    emergency_type = session.get('emergency_type', 'Unknown')
    report_data = session.get('report_data', {})
    
    # Generate PDF
    pdf_data = generate_pdf(hospital, patient_data, emergency_type, report_data)
    
    # Send email
    success, message = send_email_with_pdf(
        recipient_email, 
        hospital, 
        pdf_data, 
        patient_data.get('name', 'Patient')
    )
    
    return jsonify({'success': success, 'message': message})

if __name__ == '__main__':
    app.run(debug=True, port=5000)