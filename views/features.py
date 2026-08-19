import streamlit as st
from styles import coming_soon_page, inject_css, nav_bar
from views import appointment as book_appointment
from views.risk_alert import show_risk_alert_page
import joblib
import os
import json
import io
import re
from datetime import datetime
from xml.sax.saxutils import escape

from google import genai
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from database import (
    save_medical_record,
    get_records_by_doctor_and_status,
    delete_medical_record,
)

FEATURE_ROUTES = {
    "feature_book_appointment": ("Book an Appointment", "patient_dashboard"),
    "feature_active_cases": ("Active Cases and AI Triage", "doctor_dashboard"),
    "feature_archived_records": ("Archived Records", "doctor_dashboard"),
    "feature_complication_risk": ("Complication Risk Alert", "doctor_dashboard"),
}

client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


# ==========================================
# PDF helpers
# ==========================================

def _safe_filename(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", (value or "patient").strip())
    return cleaned.strip("_") or "patient"


def _paragraph_text(value) -> str:
    if value is None:
        return "Not provided"
    text = str(value).strip()
    if not text:
        return "Not provided"
    return escape(text).replace("\n", "<br/>")


def _clean_ai_text(value: str) -> str:
    """Remove lightweight markdown that Gemini may return."""
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("**", "")
    text = text.replace("__", "")
    text = text.replace("```", "")
    text = re.sub(r"^\s*#+\s*", "", text, flags=re.MULTILINE)
    return text.strip()


def _split_instruction_sections(value: str):
    """
    Convert plain/markdown-ish treatment output into simple printable sections.
    Returns a list of (section_title, [lines]).
    """
    text = _clean_ai_text(value)
    if not text:
        return []

    sections = []
    current_title = "Care Instructions"
    current_lines = []

    known_titles = {
        "clinical rationale": "Clinical Summary",
        "treatment plan": "Treatment Plan",
        "non-pharmacological management": "Home Care",
        "non pharmacological management": "Home Care",
        "medication instructions": "Medication Instructions",
        "pharmacological management": "Medication Instructions",
        "monitoring and follow-up": "Monitoring and Follow-up",
        "monitoring and follow up": "Monitoring and Follow-up",
        "parental education": "Caregiver Advice",
        "patient education": "Patient Advice",
    }

    def flush():
        nonlocal current_lines
        if current_lines:
            sections.append((current_title, current_lines))
            current_lines = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        line = re.sub(r"^[*•\-]+\s*", "", line).strip()
        if not line:
            continue

        if ":" in line:
            first, rest = line.split(":", 1)
            key = first.strip().lower()
            if key in known_titles and not rest.strip():
                flush()
                current_title = known_titles[key]
                continue

        lowered = line.lower().rstrip(":")
        if lowered in known_titles:
            flush()
            current_title = known_titles[lowered]
            continue

        current_lines.append(line)

    flush()
    return sections


def _split_prescription_lines(value: str):
    text = _clean_ai_text(value)
    if not text:
        return []
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"^[*•\-]+\s*", "", raw_line.strip()).strip()
        if line:
            lines.append(line)
    return lines


def _pdf_styles():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ClinicalTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=17,
        leading=21,
        alignment=TA_CENTER,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "ClinicalSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        spaceAfter=12,
    )

    heading_style = ParagraphStyle(
        "ClinicalHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        spaceBefore=8,
        spaceAfter=5,
        textColor=colors.HexColor("#1F3A5F"),
    )

    body_style = ParagraphStyle(
        "ClinicalBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        spaceAfter=5,
    )

    small_style = ParagraphStyle(
        "ClinicalSmall",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#666666"),
    )

    return title_style, subtitle_style, heading_style, body_style, small_style


def _add_pdf_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#666666"))
    canvas.drawString(
        18 * mm,
        12 * mm,
        "AI-assisted clinical documentation - clinician review required",
    )
    canvas.drawRightString(
        A4[0] - 18 * mm,
        12 * mm,
        f"Page {doc.page}",
    )
    canvas.restoreState()


def build_patient_instructions_pdf(
    patient_name,
    diagnosis,
    treatment,
    prescription,
    doctor_name="",
):
    """
    Patient-facing care sheet with clean headings and bullet points.
    It intentionally excludes NRIC, SML internals, and the full clinical record.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=20 * mm,
    )

    title_style, subtitle_style, heading_style, body_style, small_style = _pdf_styles()

    section_style = ParagraphStyle(
        "PatientSection",
        parent=heading_style,
        fontSize=11,
        leading=14,
        spaceBefore=10,
        spaceAfter=5,
        textColor=colors.HexColor("#17365D"),
    )

    bullet_style = ParagraphStyle(
        "PatientBullet",
        parent=body_style,
        leftIndent=12,
        firstLineIndent=-7,
        bulletIndent=4,
        spaceAfter=4,
    )

    label_style = ParagraphStyle(
        "PatientLabel",
        parent=body_style,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#17365D"),
        spaceAfter=2,
    )

    story = [
        Paragraph("Patient Care Instructions", title_style),
        Paragraph(
            f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
            subtitle_style,
        ),
    ]

    info_data = [
        [
            Paragraph("<b>Patient</b>", body_style),
            Paragraph(_paragraph_text(patient_name), body_style),
        ],
        [
            Paragraph("<b>Diagnosis</b>", body_style),
            Paragraph(_paragraph_text(diagnosis), body_style),
        ],
    ]

    if doctor_name:
        info_data.append(
            [
                Paragraph("<b>Clinician</b>", body_style),
                Paragraph(_paragraph_text(doctor_name), body_style),
            ]
        )

    info_table = Table(info_data, colWidths=[35 * mm, 120 * mm])
    info_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF3F8")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B8C6D4")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E0E7")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([info_table, Spacer(1, 6)])

    treatment_sections = _split_instruction_sections(treatment)

    # Patient copy should prioritize practical instructions and avoid dumping
    # an internal clinical rationale as a large raw paragraph.
    for section_title, lines in treatment_sections:
        if section_title == "Clinical Summary":
            continue

        story.append(Paragraph(section_title, section_style))
        for line in lines:
            story.append(
                Paragraph(
                    f"• {escape(line)}",
                    bullet_style,
                )
            )

    prescription_lines = _split_prescription_lines(prescription)
    if prescription_lines:
        story.append(Paragraph("Medication / Prescription", section_style))
        for line in prescription_lines:
            story.append(
                Paragraph(
                    f"• {escape(line)}",
                    bullet_style,
                )
            )

    story.extend(
        [
            Spacer(1, 8),
            Table(
                [
                    [
                        Paragraph(
                            "<b>Important</b><br/>"
                            "Follow the clinician's instructions. If symptoms worsen, "
                            "new concerning symptoms appear, or you are unsure about a medicine, "
                            "contact the clinic or seek appropriate medical care.",
                            small_style,
                        )
                    ]
                ],
                colWidths=[155 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7E8")),
                        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#E2BE75")),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                ),
            ),
            Spacer(1, 6),
            Paragraph(
                "Educational prototype: the attending clinician must review this document before it is given to the patient.",
                small_style,
            ),
        ]
    )

    doc.build(story, onFirstPage=_add_pdf_footer, onLaterPages=_add_pdf_footer)
    return buffer.getvalue()


def build_medical_record_pdf(record: dict):
    """
    Full internal clinical record PDF for archive/download.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
    )

    title_style, subtitle_style, heading_style, body_style, small_style = _pdf_styles()

    story = [
        Paragraph("Polyclinic Clinical Record", title_style),
        Paragraph(
            f"Generated on {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
            subtitle_style,
        ),
    ]

    patient_data = [
        ["Name", record.get("patient_name") or "Not provided"],
        ["NRIC / ID", record.get("patient_nric") or "Not provided"],
        ["Age", record.get("patient_age") or "Not provided"],
        ["Gender", record.get("patient_gender") or "Not provided"],
    ]

    table_rows = []
    for label, value in patient_data:
        table_rows.append(
            [
                Paragraph(f"<b>{escape(label)}</b>", body_style),
                Paragraph(_paragraph_text(value), body_style),
            ]
        )

    patient_table = Table(table_rows, colWidths=[35 * mm, 120 * mm])
    patient_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F6FA")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#C9D2DC")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D9E0E7")),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([Paragraph("Patient Information", heading_style), patient_table])

    vitals = (
        f"Temperature: {record.get('temp') or 'Not provided'} °C<br/>"
        f"Blood Pressure: {record.get('bp') or 'Not provided'}<br/>"
        f"Heart Rate: {record.get('hr') or 'Not provided'} bpm<br/>"
        f"SpO2: {record.get('spo2') or 'Not provided'}%"
    )
    story.extend(
        [
            Paragraph("Vitals and Collected Information", heading_style),
            Paragraph(vitals, body_style),
            Paragraph("Consultation Notes / Patient Complaint", heading_style),
            Paragraph(
                _paragraph_text(
                    record.get("patient_complaint")
                    or record.get("symptoms")
                    or ""
                ),
                body_style,
            ),
            Paragraph("AI-Assisted Triage and Assessment", heading_style),
            Paragraph(
                f"<b>Recommended Department:</b> "
                f"{_paragraph_text(record.get('prediction'))}<br/>"
                f"<b>ICD-10 Category:</b> "
                f"{_paragraph_text(record.get('icd10'))}<br/>"
                f"<b>Reviewed Diagnosis:</b> "
                f"{_paragraph_text(record.get('ai_diagnosis'))}",
                body_style,
            ),
        ]
    )

    findings = [
        item.strip()
        for item in str(record.get("confirmed_findings") or "").split("||")
        if item.strip()
    ]
    if findings:
        findings_html = "<br/>".join(f"- {escape(item)}" for item in findings)
        story.extend(
            [
                Paragraph("Doctor-Confirmed Findings", heading_style),
                Paragraph(findings_html, body_style),
            ]
        )

    story.extend(
        [
            Paragraph("Final Clinical Record", heading_style),
            Paragraph(_paragraph_text(record.get("final_clinical_record")), body_style),
            Paragraph("Treatment Plan and Patient Advice", heading_style),
            Paragraph(_paragraph_text(record.get("treatment")), body_style),
            Paragraph("Prescription", heading_style),
            Paragraph(_paragraph_text(record.get("prescription")), body_style),
        ]
    )

    referral = str(record.get("referral_letter") or "").strip()
    if referral:
        story.extend(
            [
                Paragraph("Referral Letter", heading_style),
                Paragraph(_paragraph_text(referral), body_style),
            ]
        )

    story.extend(
        [
            Spacer(1, 10),
            Paragraph(
                "Archived clinical records are read-only in the application. "
                "This PDF is generated from the archived database record.",
                small_style,
            ),
        ]
    )

    doc.build(story, onFirstPage=_add_pdf_footer, onLaterPages=_add_pdf_footer)
    return buffer.getvalue()


def save_medical_record_pdf_to_disk(pdf_bytes: bytes, patient_name: str) -> str:
    """
    Save a copy automatically when a record is archived.
    When Streamlit is run locally, this folder is on the user's computer.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, "generated_pdfs", "medical_records")
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{_safe_filename(patient_name)}_{timestamp}_medical_record.pdf"
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "wb") as file:
        file.write(pdf_bytes)

    return output_path


# ==========================================
# GenAI 核心功能库 
# ==========================================

def generate_referral_letter(patient, age, gender, vitals_context, symptoms, prediction, icd10, treatment, prescription):
    prompt = f"""
    You are a professional medical assistant. Write a formal, comprehensive clinical referral letter to the {prediction} department.
    
    Patient Demographics:
    - Name: {patient}
    - Age: {age}
    - Gender: {gender}
    
    Vitals & Objective Data:
    {vitals_context}
    
    Clinical Information:
    - History of Present Illness / Symptoms: {symptoms}
    - Triage Department: {prediction} (ICD-10: {icd10})
    - Initial Treatment & Prescriptions: {treatment}. Medication: {prescription}
    
    Requirements:
    1. Use standard formal medical letter formatting (e.g., Dear Colleague).
    2. Synthesize the provided notes into a cohesive, professional narrative structured in distinct paragraphs.
    3. Output ONLY the letter content.
    4. Do not use markdown symbols such as **, *, #, _, backticks, or markdown bullet syntax.
    5. Use normal plain-text headings and paragraphs only when needed.
    """
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return _clean_ai_text(response.text)

def generate_clinical_assessment(
    department,
    consultation_notes,
    demographics_context,
    vitals_context,
    confirmed_findings=None,
    current_diagnosis="",
):
    """
    Suggest one likely diagnosis and concrete symptoms/findings for doctor verification.
    When confirmed_findings are supplied, the same function can re-evaluate the diagnosis.
    """
    confirmed_findings = confirmed_findings or []
    confirmed_text = ", ".join(confirmed_findings) if confirmed_findings else "None selected yet"

    prompt = f"""
    You are a clinical decision-support assistant for a polyclinic doctor.

    The supervised-learning triage model has already recommended this department:
    {department}

    Patient demographics:
    {demographics_context}

    Vitals:
    {vitals_context}

    Consultation notes / patient complaint:
    {consultation_notes}

    Current diagnosis suggestion, if any:
    {current_diagnosis or 'None'}

    Doctor-confirmed findings, if any:
    {confirmed_text}

    TASK:
    1. Suggest ONE most likely concise clinical diagnosis that is appropriate for the given department.
    2. Generate 10 to 12 concrete symptoms or clinical findings that are useful for verifying that diagnosis.
    3. The list must contain actual symptoms/signs such as cough, runny nose, nasal congestion,
       sore throat, fever, headache, fatigue, body aches, nausea, rash, wheezing, etc. when relevant.
    4. Do NOT include questions or history items such as:
       - duration of symptoms
       - recent contact with sick people
       - travel history
       - smoking history
       - age
       - severity as a standalone item
    5. Do NOT claim the generated findings are present. They are checkbox options for the doctor to verify.
    6. If confirmed findings were provided, use them to refine the suggested diagnosis.
    7. Return ONLY valid JSON. Do not use markdown.
    8. The diagnosis and every finding must be plain text without markdown symbols such as **, *, #, _, or backticks.

    Required JSON format:
    {{
      "suggested_diagnosis": "diagnosis name",
      "findings": [
        "finding 1",
        "finding 2",
        "finding 3"
      ]
    }}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    raw = response.text.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()

    data = json.loads(raw)

    diagnosis = _clean_ai_text(str(data.get("suggested_diagnosis", "")))
    findings = data.get("findings", [])

    if not isinstance(findings, list):
        findings = []

    cleaned_findings = []
    for item in findings:
        text = _clean_ai_text(str(item))
        if text and text not in cleaned_findings:
            cleaned_findings.append(text)

    return diagnosis, cleaned_findings[:12]


def generate_final_clinical_record(
    patient_name,
    age,
    gender,
    vitals_context,
    consultation_notes,
    department,
    icd10,
    diagnosis,
    confirmed_findings,
):
    """
    Generate a fuller archive-ready clinical record from all collected information.
    NRIC is intentionally excluded from the GenAI prompt.
    """
    findings_text = (
        ", ".join(confirmed_findings)
        if confirmed_findings
        else "No additional findings explicitly confirmed"
    )

    prompt = f"""
    You are a professional medical scribe assisting a polyclinic doctor.

    Create a detailed but concise clinical encounter record using ONLY the information provided below.

    PATIENT INFORMATION
    Name: {patient_name}
    Age: {age}
    Gender: {gender}

    COLLECTED VITALS
    {vitals_context}

    CONSULTATION NOTES / PATIENT COMPLAINT
    {consultation_notes}

    SML TRIAGE RESULT
    Department: {department or 'Not available'}
    ICD-10 category: {icd10 or 'Not available'}

    AI-SUGGESTED DIAGNOSIS REVIEWED/EDITED BY DOCTOR
    {diagnosis or 'Not confirmed'}

    DOCTOR-CONFIRMED FINDINGS
    {findings_text}

    REQUIREMENTS:
    1. Use ONLY the supplied information. Do not invent duration, examination results,
       tests, medications, medical history, diagnoses, or symptoms.
    2. Produce a fuller clinical record than a short summary.
    3. Separate collected information from symptom description clearly.
    4. Use the following plain-text sections exactly. Do NOT use markdown symbols such as ** or #.

    PATIENT INFORMATION
    Include age and gender in one concise sentence. Do not include NRIC.

    VITALS AND COLLECTED INFORMATION
    Summarize all supplied vital signs. If a vital was not provided, do not invent it.

    PRESENTING SYMPTOMS AND CONSULTATION NOTES
    Turn the consultation input and doctor-confirmed findings into a coherent clinical narrative.
    Mention which symptoms were explicitly confirmed.

    CLINICAL ASSESSMENT
    State the reviewed diagnosis, the SML-recommended department, and the supplied ICD-10 category.
    Present them as clinical decision-support information reviewed by the doctor.

    CLINICAL RECORD SUMMARY
    End with a concise integrated summary suitable for archiving.

    5. Keep the writing professional and readable.
    6. Output ONLY the clinical record.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return _clean_ai_text(response.text)


def ai_enhance_treatment(content, demographics_context="", vitals_context=""):
    prompt = f"""
    You are a clinical decision-support assistant helping a doctor prepare a treatment plan.

    IMPORTANT:
    - This is for clinician review. Do not claim the plan is final.
    - Use only the supplied patient information and clinical record.
    - Do not output markdown symbols such as **, #, or code fences.
    - Keep the wording practical and readable.

    Return EXACTLY these two tagged sections:

    [TREATMENT_PLAN]
    Use these plain-text headings when relevant:

    Non-Pharmacological Management:
    - practical home-care or supportive-care instructions

    Medication Instructions:
    - medication name and clinician-facing instructions only when appropriate

    Monitoring and Follow-up:
    - relevant monitoring, precautions, and follow-up advice

    Do NOT include an internal "Clinical Rationale" section in the patient-facing plan.

    [PRESCRIPTION_LIST]
    Provide a simple list of medication names / formulations intended for the pharmacy or billing workflow.
    Do not add markdown formatting.

    Patient Demographics: {demographics_context}
    Patient Vitals: {vitals_context}
    Clinical Notes & Symptoms: {content}
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    text = response.text.strip()

    plan_text = text
    prescription_text = ""

    if "[PRESCRIPTION_LIST]" in text:
        parts = text.split("[PRESCRIPTION_LIST]", 1)
        plan_text = parts[0].replace("[TREATMENT_PLAN]", "").strip()
        prescription_text = parts[1].strip()
    else:
        plan_text = text.replace("[TREATMENT_PLAN]", "").strip()

    return _clean_ai_text(plan_text), _clean_ai_text(prescription_text)


# ==========================================
# 2. AI 模型缓存与加载逻辑
# ==========================================
@st.cache_resource
def load_sml_models():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    vectorizer_path = os.path.join(project_root, "models", "tfidf_vectorizer.pkl")
    model_path = os.path.join(project_root, "models", "best_svc_model.pkl")

    vectorizer = joblib.load(vectorizer_path)
    model = joblib.load(model_path)
    return vectorizer, model

# ==========================================
# 3. 专属界面 A：Active Cases & SML Triage 
# ==========================================
def show_active_cases():
    inject_css()

    # Local styling override for this clinical page only.
    st.markdown(
        """
        <style>
        /* Fix only the large multi-line text areas on this feature page.
           Small text inputs keep the project's existing global styles. */
        [data-testid="stTextArea"] textarea {
            background-color: #0b1627 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            caret-color: #ffffff !important;
        }

        [data-testid="stTextArea"] textarea::placeholder {
            color: #8fa3bd !important;
            -webkit-text-fill-color: #8fa3bd !important;
            opacity: 1 !important;
        }

        [data-testid="stTextArea"] [data-baseweb="textarea"] {
            background-color: #0b1627 !important;
        }

        /* Local styling only for PDF download buttons on this feature page. */
        [data-testid="stDownloadButton"] > button,
        [data-testid="stDownloadButton"] > button:hover,
        [data-testid="stDownloadButton"] button {
            background-color: #000000 !important;
            color: #FFFFFF !important;
            border: 1px solid #2D2D2D !important;
            border-radius: 8px !important;
            min-height: 44px !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            font-family: 'Inter', sans-serif !important;
        }

        [data-testid="stDownloadButton"] > button:hover {
            background-color: #111111 !important;
            border-color: #3D3D3D !important;
        }

        [data-testid="stDownloadButton"] button *,
        [data-testid="stDownloadButton"] button p,
        [data-testid="stDownloadButton"] button span {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    nav_bar(st.session_state.user.get("name", "Doctor"), is_admin=False)

    st.markdown(
        """
        <div style="margin-bottom:18px;">
            <div style="
                font-size:0.82rem;
                color:#8fa3bd;
                font-weight:700;
                letter-spacing:0.08em;
                text-transform:uppercase;
            ">
                Clinical workspace
            </div>
            <h2 style="margin:5px 0 4px;">Active Cases & AI Triage</h2>
            <p style="margin:0;color:#9fb0c7;">
                Capture the consultation, run SML triage, verify AI-assisted findings and generate an archive-ready clinical record.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button("← Back to Dashboard"):
        st.session_state.page = "doctor_dashboard"
        st.rerun()

    st.markdown("<hr/>", unsafe_allow_html=True)

    doctor_id = st.session_state.user["id"]

    defaults = {
        "current_view": "list",
        "edit_record_id": None,
        "f_patient": "",
        "f_age": "",
        "f_nric": "",
        "f_gender": "Select gender...",
        "f_temp": "",
        "f_bp": "",
        "f_hr": "",
        "f_spo2": "",
        "f_patient_complaint": "",
        "f_prediction": "",
        "f_icd10": "",
        "f_ai_diagnosis": "",
        "f_ai_findings": [],
        "f_selected_findings": [],
        "f_other_finding": "",
        "f_final_record": "",
        "f_treatment": "",
        "f_prescription": "",
        "f_referral_letter": "",
        "f_triage_note": "",
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    icd10_map = {
        "General Medicine": "R69 (Illness, unspecified)",
        "Dermatology": "L98.9 (Disorder of the skin, unspecified)",
        "ENT - Otolaryngology": "H92.0 (Otalgia) / J39.9 (Disease of upper respiratory tract)",
        "Dentistry": "K08.9 (Disorder of teeth and supporting structures)",
        "Pediatrics - Neonatal": "P96.9 (Condition originating in the perinatal period)",
        "Psychiatry / Psychology": "F99 (Mental disorder, not otherwise specified)",
        "Hospital Referral (Surgery/Specialist)": "Z51.89 (Encounter for other specified medical care)",
        "Obstetrics / Gynecology": "N94.9 (Condition associated with female genital organs and menstrual cycle, unspecified)",
        "Ophthalmology": "H57.9 (Disorder of eye and adnexa, unspecified)",
    }

    def reset_case_form():
        st.session_state.edit_record_id = None
        for key, value in defaults.items():
            if key not in ("current_view", "edit_record_id"):
                st.session_state[key] = value

    col_nav1, col_nav2 = st.columns(2)

    with col_nav1:
        if st.button(
            "📋 Draft Cases (Unarchived)",
            use_container_width=True,
            type="primary" if st.session_state.current_view == "list" else "secondary",
        ):
            st.session_state.current_view = "list"
            st.rerun()

    with col_nav2:
        if st.button(
            "✍️ Create New Case",
            use_container_width=True,
            type="primary" if st.session_state.current_view == "form" else "secondary",
        ):
            reset_case_form()
            st.session_state.current_view = "form"
            st.rerun()

    # ==================================================
    # View A: Draft list
    # ==================================================
    if st.session_state.current_view == "list":
        st.subheader("Your Working Drafts")

        if st.session_state.get("last_archived_pdf_path"):
            st.success(
                "Archived medical record PDF saved automatically to:\n"
                f"{st.session_state['last_archived_pdf_path']}"
            )
            st.session_state["last_archived_pdf_path"] = ""

        if st.session_state.get("last_archived_pdf_error"):
            st.warning(
                "The record was archived, but the automatic PDF copy could not be saved: "
                f"{st.session_state['last_archived_pdf_error']}"
            )
            st.session_state["last_archived_pdf_error"] = ""

        drafts_from_db = get_records_by_doctor_and_status(doctor_id, "Draft")

        if not drafts_from_db:
            st.info("No drafts saved in database yet. Click 'Create New Case' to start.")
            return

        with st.container(border=True):
            cols = st.columns([2, 3, 2, 2, 2])
            cols[0].markdown("**Date**")
            cols[1].markdown("**Patient Name**")
            cols[2].markdown("**Status**")
            cols[3].markdown("**Edit**")
            cols[4].markdown("**Delete**")

            for draft in drafts_from_db:
                cols[0].write(str(draft.get("updated_at", ""))[:10])
                cols[1].write(draft.get("patient_name", ""))
                cols[2].write("🟡 Draft")

                if cols[3].button("Edit ✏️", key=f"edit_{draft['id']}"):
                    st.session_state.edit_record_id = draft["id"]
                    st.session_state.f_patient = draft.get("patient_name") or ""
                    st.session_state.f_age = str(draft.get("patient_age") or "")
                    st.session_state.f_nric = draft.get("patient_nric") or ""
                    st.session_state.f_gender = draft.get("patient_gender") or "Select gender..."
                    st.session_state.f_temp = draft.get("temp") or ""
                    st.session_state.f_bp = draft.get("bp") or ""
                    st.session_state.f_hr = draft.get("hr") or ""
                    st.session_state.f_spo2 = draft.get("spo2") or ""
                    saved_complaint = draft.get("patient_complaint") or draft.get("symptoms") or ""
                    saved_doctor_notes = draft.get("doctor_notes") or ""
                    if saved_doctor_notes and saved_doctor_notes not in saved_complaint:
                        saved_complaint = f"{saved_complaint}\n{saved_doctor_notes}".strip()
                    st.session_state.f_patient_complaint = saved_complaint
                    st.session_state.f_prediction = draft.get("prediction") or ""
                    st.session_state.f_icd10 = draft.get("icd10") or ""
                    st.session_state.f_ai_diagnosis = draft.get("ai_diagnosis") or ""
                    stored_findings = draft.get("confirmed_findings") or ""
                    st.session_state.f_selected_findings = [
                        x.strip() for x in stored_findings.split("||") if x.strip()
                    ]
                    st.session_state.f_ai_findings = list(st.session_state.f_selected_findings)
                    st.session_state.f_final_record = draft.get("final_clinical_record") or ""
                    st.session_state.f_treatment = draft.get("treatment") or ""
                    st.session_state.f_prescription = draft.get("prescription") or ""
                    st.session_state.f_referral_letter = draft.get("referral_letter") or ""
                    st.session_state.current_view = "form"
                    st.rerun()

                if cols[4].button("Drop 🗑️", key=f"del_{draft['id']}"):
                    delete_medical_record(draft["id"], doctor_id)
                    st.rerun()

        return

    # ==================================================
    # View B: Clinical form
    # ==================================================
    st.subheader("Clinical Encounter Form")

    if st.session_state.edit_record_id is not None:
        st.warning(f"You are editing a saved draft for **{st.session_state.f_patient}**")

    # --------------------------------------------------
    # 1. Patient information
    # --------------------------------------------------
    st.markdown("#### 1. Patient Information")

    d1, d2 = st.columns(2)

    with d1:
        st.session_state.f_patient = st.text_input(
            "Patient Name",
            value=st.session_state.f_patient,
            placeholder="e.g., Jane Smith",
        )

        st.session_state.f_age = st.text_input(
            "Age",
            value=st.session_state.f_age,
            placeholder="e.g., 31",
        ).strip()

    with d2:
        st.session_state.f_nric = st.text_input(
            "NRIC / ID Number",
            value=st.session_state.f_nric,
            placeholder="e.g., S1234567A",
        ).strip()

        gender_options = [
            "Select gender...",
            "Female",
            "Male",
            "Other / Prefer not to say",
        ]

        try:
            gender_index = gender_options.index(st.session_state.f_gender)
        except ValueError:
            gender_index = 0

        st.session_state.f_gender = st.selectbox(
            "Gender",
            gender_options,
            index=gender_index,
        )

    patient_name = st.session_state.f_patient.strip()
    patient_age = st.session_state.f_age
    patient_nric = st.session_state.f_nric
    patient_gender = st.session_state.f_gender

    demographics_context = (
        f"Name: {patient_name or 'Not provided'}; "
        f"Age: {patient_age or 'Not provided'}; "
        f"Gender: {patient_gender if patient_gender != 'Select gender...' else 'Not provided'}"
    )

    # --------------------------------------------------
    # 2. Vitals
    # --------------------------------------------------
    st.markdown("#### 2. Vitals & Objective Data")

    v1, v2, v3, v4 = st.columns(4)

    st.session_state.f_temp = v1.text_input(
        "Temperature (°C)",
        value=st.session_state.f_temp,
        placeholder="e.g., 37.2",
    )
    st.session_state.f_bp = v2.text_input(
        "Blood Pressure",
        value=st.session_state.f_bp,
        placeholder="e.g., 120/80",
    )
    st.session_state.f_hr = v3.text_input(
        "Heart Rate (bpm)",
        value=st.session_state.f_hr,
        placeholder="e.g., 75",
    )
    st.session_state.f_spo2 = v4.text_input(
        "SpO2 (%)",
        value=st.session_state.f_spo2,
        placeholder="e.g., 98",
    )

    vitals_context = (
        f"Temp: {st.session_state.f_temp or 'Not provided'}°C, "
        f"BP: {st.session_state.f_bp or 'Not provided'}, "
        f"HR: {st.session_state.f_hr or 'Not provided'} bpm, "
        f"SpO2: {st.session_state.f_spo2 or 'Not provided'}%"
    )

    st.divider()

    # --------------------------------------------------
    # 3. Consultation + SML triage (combined)
    # --------------------------------------------------
    st.markdown("#### 3. Consultation & SML Triage")

    st.session_state.f_patient_complaint = st.text_area(
        "Consultation Notes / Patient Complaint",
        value=st.session_state.f_patient_complaint,
        height=240,
        placeholder=(
            "Enter the patient's complaint and your quick consultation notes in one place, "
            "e.g. fever, headache, sore throat, runny nose, body aches."
        ),
    )

    st.caption(
        "The SML triage model uses only this consultation text so that prediction input "
        "remains consistent with the model's training format."
    )

    with st.container(border=True):
        st.markdown("🤖 **SML Triage Engine**")

        if not st.session_state.f_prediction:
            if st.button("Run SML Triage", type="primary", use_container_width=True):
                complaint = st.session_state.f_patient_complaint.strip()

                if not complaint:
                    st.warning("Please enter the Patient Complaint first.")
                else:
                    with st.spinner("Analyzing the Patient Complaint..."):
                        try:
                            tfidf, svc_model = load_sml_models()

                            # IMPORTANT: only Patient Complaint goes into the SML model.
                            sml_input = complaint

                            vectorized_text = tfidf.transform([sml_input])
                            raw_prediction = str(svc_model.predict(vectorized_text)[0])

                            if not patient_age:
                                st.warning("Please enter the patient's age before running triage.")
                                st.stop()

                            if not patient_age.isdigit() or not (0 < int(patient_age) <= 120):
                                st.warning("Please enter a valid age between 1 and 120.")
                                st.stop()

                            prediction = raw_prediction
                            st.session_state.f_triage_note = ""

                            # Keep the NLP model input unchanged, then apply an age-safety rule.
                            # This prevents an adult from being routed to the neonatal category
                            # without changing the TF-IDF/SVC input distribution.
                            if int(patient_age) >= 18 and raw_prediction == "Pediatrics - Neonatal":
                                prediction = "General Medicine"
                                st.session_state.f_triage_note = (
                                    "The raw SML prediction was Pediatrics - Neonatal, but the "
                                    "patient is an adult. The final routing was adjusted to "
                                    "General Medicine using an age validation rule."
                                )

                            st.session_state.f_prediction = prediction
                            st.session_state.f_icd10 = icd10_map.get(
                                prediction,
                                "R00-R99 (Symptoms, signs and abnormal findings)",
                            )

                            # Reset downstream GenAI because the triage result changed.
                            st.session_state.f_ai_diagnosis = ""
                            st.session_state.f_ai_findings = []
                            st.session_state.f_selected_findings = []
                            st.session_state.f_other_finding = ""
                            st.session_state.f_final_record = ""

                            st.rerun()

                        except Exception as e:
                            st.error(f"AI Engine Error: {e}")

        else:
            st.success(f"**Recommended Department:** {st.session_state.f_prediction}")
            st.info(f"**Suggested ICD-10 Category:** {st.session_state.f_icd10}")

            if st.session_state.f_triage_note:
                st.warning(st.session_state.f_triage_note)

            if st.button("Re-run SML Analysis"):
                st.session_state.f_prediction = ""
                st.session_state.f_icd10 = ""
                st.session_state.f_triage_note = ""
                st.session_state.f_ai_diagnosis = ""
                st.session_state.f_ai_findings = []
                st.session_state.f_selected_findings = []
                st.session_state.f_other_finding = ""
                st.session_state.f_final_record = ""
                st.rerun()

    # --------------------------------------------------
    # 4. Automatic GenAI clinical assessment
    # --------------------------------------------------
    if st.session_state.f_prediction:
        st.divider()
        st.markdown("#### 4. AI Clinical Assessment & Finding Verification")

        # Automatically run GenAI once after SML triage.
        if not st.session_state.f_ai_diagnosis:
            with st.spinner("GenAI is preparing a diagnosis suggestion and verification checklist..."):
                try:
                    diagnosis, findings = generate_clinical_assessment(
                        department=st.session_state.f_prediction,
                        consultation_notes=st.session_state.f_patient_complaint,
                        demographics_context=demographics_context,
                        vitals_context=vitals_context,
                    )

                    st.session_state.f_ai_diagnosis = diagnosis
                    st.session_state.f_ai_findings = findings
                    st.session_state.f_selected_findings = []
                    st.rerun()

                except Exception as e:
                    st.error(f"GenAI Assessment Error: {e}")

        if st.session_state.f_ai_diagnosis:
            st.markdown("**AI Suggested Diagnosis (Editable)**")

            diagnosis_col, reanalyse_col = st.columns([4, 1])

            with diagnosis_col:
                st.session_state.f_ai_diagnosis = st.text_input(
                    "AI Suggested Diagnosis",
                    value=_clean_ai_text(st.session_state.f_ai_diagnosis),
                    key="ai_diagnosis_editable",
                    label_visibility="collapsed",
                ).strip()

            with reanalyse_col:
                if st.button(
                    "Re-analyze",
                    use_container_width=True,
                    key="reanalyze_diagnosis_btn",
                ):
                    with st.spinner("Re-evaluating diagnosis using the confirmed findings..."):
                        try:
                            updated_diagnosis, updated_findings = generate_clinical_assessment(
                                department=st.session_state.f_prediction,
                                consultation_notes=st.session_state.f_patient_complaint,
                                demographics_context=demographics_context,
                                vitals_context=vitals_context,
                                confirmed_findings=st.session_state.f_selected_findings,
                                current_diagnosis=st.session_state.f_ai_diagnosis,
                            )

                            st.session_state.f_ai_diagnosis = updated_diagnosis

                            # Keep already-confirmed findings available while refreshing
                            # the checklist for the revised diagnosis.
                            refreshed = list(updated_findings)
                            for item in st.session_state.f_selected_findings:
                                if item and item not in refreshed:
                                    refreshed.append(item)

                            st.session_state.f_ai_findings = refreshed[:12]
                            st.rerun()

                        except Exception as e:
                            st.error(f"GenAI Re-analysis Error: {e}")

            st.markdown("**Verify symptoms/findings that are actually present:**")

            selected_findings = []
            finding_options = st.session_state.f_ai_findings

            left_col, right_col = st.columns(2)

            for idx, finding in enumerate(finding_options):
                target_col = left_col if idx % 2 == 0 else right_col

                with target_col:
                    is_checked = st.checkbox(
                        finding,
                        value=finding in st.session_state.f_selected_findings,
                        key=f"finding_{idx}_{finding}",
                    )

                    if is_checked:
                        selected_findings.append(finding)

            st.session_state.f_other_finding = st.text_input(
                "Other confirmed symptom/finding (optional)",
                value=st.session_state.f_other_finding,
                placeholder="e.g., mild pharyngeal erythema",
            ).strip()

            if st.session_state.f_other_finding:
                selected_findings.append(st.session_state.f_other_finding)

            st.session_state.f_selected_findings = selected_findings

            st.caption(
                "The diagnosis above can be edited directly. Re-analyze uses the checked findings "
                "to update the diagnosis suggestion."
            )

    # --------------------------------------------------
    # 5. Final GenAI clinical record
    # --------------------------------------------------
    if st.session_state.f_ai_diagnosis:
        st.divider()
        st.markdown("#### 5. Final Clinical Record")

        if st.button("✨ Generate Complete Clinical Record", use_container_width=True):
            if not patient_name:
                st.warning("Please enter the patient's name first.")
            elif not patient_age:
                st.warning("Please enter the patient's age first.")
            elif not patient_age.isdigit() or not (0 < int(patient_age) <= 120):
                st.warning("Please enter a valid age between 1 and 120.")
            elif patient_gender == "Select gender...":
                st.warning("Please select the patient's gender first.")
            elif not st.session_state.f_patient_complaint.strip():
                st.warning("Please enter the Patient Complaint first.")
            else:
                with st.spinner("GenAI is synthesizing the consultation into an archive-ready record..."):
                    try:
                        st.session_state.f_final_record = generate_final_clinical_record(
                            patient_name=patient_name,
                            age=patient_age,
                            gender=patient_gender,
                            vitals_context=vitals_context,
                            consultation_notes=st.session_state.f_patient_complaint,
                            department=st.session_state.f_prediction,
                            icd10=st.session_state.f_icd10,
                            diagnosis=st.session_state.f_ai_diagnosis,
                            confirmed_findings=st.session_state.f_selected_findings,
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"GenAI Clinical Record Error: {e}")

        if st.session_state.f_final_record:
            st.session_state.f_final_record = st.text_area(
                "Generated Clinical Record (Editable)",
                value=_clean_ai_text(st.session_state.f_final_record),
                height=330,
            )

    # --------------------------------------------------
    # 6. Treatment and prescriptions
    # --------------------------------------------------
    st.divider()
    st.markdown("#### 6. Treatment Plan & Prescriptions")

    st.session_state.f_treatment = st.text_area(
        "Treatment Rationale & Detailed Instructions:",
        value=_clean_ai_text(st.session_state.f_treatment),
        height=220,
    )

    st.session_state.f_prescription = st.text_area(
        "Required Prescription List (For Billing/Pharmacy):",
        value=_clean_ai_text(st.session_state.f_prescription),
        height=140,
        placeholder="E.g., - Paracetamol 500mg tablet\n- Saline Nasal Spray",
    )

    if st.button("✨ AI Suggest Treatment & Prescriptions"):
        source_text = (
            st.session_state.f_final_record.strip()
            or st.session_state.f_patient_complaint.strip()
        )

        if not source_text:
            st.warning("Please complete the consultation information first.")
        else:
            with st.spinner("AI is organizing the treatment plan and prescription list..."):
                try:
                    plan_text, pres_text = ai_enhance_treatment(
                        source_text,
                        demographics_context,
                        vitals_context,
                    )
                    st.session_state.f_treatment = plan_text
                    st.session_state.f_prescription = pres_text
                    st.rerun()
                except Exception as e:
                    st.error(f"GenAI Error: {e}")


    if st.session_state.f_treatment.strip() or st.session_state.f_prescription.strip():
        try:
            patient_instruction_pdf = build_patient_instructions_pdf(
                patient_name=patient_name or "Patient",
                diagnosis=st.session_state.f_ai_diagnosis or "Not specified",
                treatment=st.session_state.f_treatment,
                prescription=st.session_state.f_prescription,
                doctor_name=st.session_state.user.get("name", ""),
            )

            patient_instruction_filename = (
                f"{_safe_filename(patient_name or 'patient')}_patient_instructions.pdf"
            )

            st.download_button(
                "Download / Print Patient Instructions",
                data=patient_instruction_pdf,
                file_name=patient_instruction_filename,
                mime="application/pdf",
                use_container_width=True,
                key="download_patient_instructions_pdf",
            )

            st.caption(
                "Open the downloaded PDF and use the normal print command to give a paper copy to the patient."
            )

        except Exception as e:
            st.error(f"Patient Instructions PDF Error: {e}")

    # --------------------------------------------------
    # 7. Referral
    # --------------------------------------------------
    st.divider()
    st.markdown("#### 7. GenAI Referral Assistant")

    if not st.session_state.f_prediction:
        st.info("Run the SML Triage Engine first before generating a referral letter.")
    else:
        if st.button("✨ Auto-Generate Referral Letter (GenAI)"):
            if not patient_name:
                st.warning("Please enter the patient's name first.")
            elif not patient_age:
                st.warning("Please enter the patient's age first.")
            elif patient_gender == "Select gender...":
                st.warning("Please select the patient's gender first.")
            else:
                symptoms_for_referral = (
                    st.session_state.f_final_record.strip()
                    or st.session_state.f_patient_complaint.strip()
                )

                with st.spinner("GenAI is drafting the referral letter..."):
                    try:
                        st.session_state.f_referral_letter = generate_referral_letter(
                            patient_name,
                            patient_age,
                            patient_gender,
                            vitals_context,
                            symptoms_for_referral,
                            st.session_state.f_prediction,
                            st.session_state.f_icd10,
                            st.session_state.f_treatment,
                            st.session_state.f_prescription,
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"GenAI Error: {e}")

        if st.session_state.f_referral_letter:
            st.session_state.f_referral_letter = st.text_area(
                "Generated Referral Letter (Editable)",
                value=_clean_ai_text(st.session_state.f_referral_letter),
                height=400,
            )

    # --------------------------------------------------
    # 8. Save / archive
    # --------------------------------------------------
    st.divider()
    st.markdown("#### 8. Actions")

    action_col1, action_col2 = st.columns(2)

    confirmed_findings_text = "||".join(st.session_state.f_selected_findings)

    def validate_for_save(require_final_record=False):
        if not patient_name:
            return "Please enter the patient's name."
        if not patient_age:
            return "Please enter the patient's age."
        if not patient_age.isdigit() or not (0 < int(patient_age) <= 120):
            return "Please enter a valid age between 1 and 120."
        if not patient_nric:
            return "Please enter the patient's NRIC / ID number."
        if patient_gender == "Select gender...":
            return "Please select the patient's gender."
        if not st.session_state.f_patient_complaint.strip():
            return "Patient Complaint cannot be empty."
        if require_final_record and not st.session_state.f_final_record.strip():
            return "Please generate or enter the final clinical record before archiving."
        return None

    with action_col1:
        if st.button("💾 Save as Draft", use_container_width=True):
            error = validate_for_save(require_final_record=False)

            if error:
                st.error(error)
            else:
                save_medical_record(
                    st.session_state.edit_record_id,
                    doctor_id,
                    patient_name,
                    patient_age,
                    patient_nric,
                    patient_gender,
                    st.session_state.f_temp,
                    st.session_state.f_bp,
                    st.session_state.f_hr,
                    st.session_state.f_spo2,
                    st.session_state.f_patient_complaint,
                    "",
                    st.session_state.f_prediction,
                    st.session_state.f_icd10,
                    st.session_state.f_ai_diagnosis,
                    confirmed_findings_text,
                    st.session_state.f_final_record,
                    st.session_state.f_treatment,
                    st.session_state.f_prescription,
                    st.session_state.f_referral_letter,
                    "Draft",
                )

                st.toast("Draft saved successfully.", icon="✅")
                st.session_state.current_view = "list"
                st.rerun()

    with action_col2:
        if st.button("📤 Submit & Archive Record", type="primary", use_container_width=True):
            error = validate_for_save(require_final_record=True)

            if error:
                st.error(error)
            else:
                save_medical_record(
                    st.session_state.edit_record_id,
                    doctor_id,
                    patient_name,
                    patient_age,
                    patient_nric,
                    patient_gender,
                    st.session_state.f_temp,
                    st.session_state.f_bp,
                    st.session_state.f_hr,
                    st.session_state.f_spo2,
                    st.session_state.f_patient_complaint,
                    "",
                    st.session_state.f_prediction,
                    st.session_state.f_icd10,
                    st.session_state.f_ai_diagnosis,
                    confirmed_findings_text,
                    st.session_state.f_final_record,
                    st.session_state.f_treatment,
                    st.session_state.f_prescription,
                    st.session_state.f_referral_letter,
                    "Archived",
                )

                # Automatically create and save an archive PDF.
                archive_record = {
                    "patient_name": patient_name,
                    "patient_nric": patient_nric,
                    "patient_age": patient_age,
                    "patient_gender": patient_gender,
                    "temp": st.session_state.f_temp,
                    "bp": st.session_state.f_bp,
                    "hr": st.session_state.f_hr,
                    "spo2": st.session_state.f_spo2,
                    "patient_complaint": st.session_state.f_patient_complaint,
                    "prediction": st.session_state.f_prediction,
                    "icd10": st.session_state.f_icd10,
                    "ai_diagnosis": st.session_state.f_ai_diagnosis,
                    "confirmed_findings": confirmed_findings_text,
                    "final_clinical_record": st.session_state.f_final_record,
                    "treatment": st.session_state.f_treatment,
                    "prescription": st.session_state.f_prescription,
                    "referral_letter": st.session_state.f_referral_letter,
                }

                try:
                    archive_pdf = build_medical_record_pdf(archive_record)
                    saved_pdf_path = save_medical_record_pdf_to_disk(
                        archive_pdf,
                        patient_name,
                    )
                    st.session_state["last_archived_pdf_path"] = saved_pdf_path
                except Exception as e:
                    st.session_state["last_archived_pdf_path"] = ""
                    st.session_state["last_archived_pdf_error"] = str(e)

                st.success("Record submitted and moved to Archived Records.")
                st.balloons()
                st.session_state.current_view = "list"
                st.rerun()


# ==========================================
# 4. 专属界面 B：真实的 Archived Records 显示
# ==========================================
def show_archived_records():
    inject_css()
    nav_bar(st.session_state.user.get("name", "Doctor"), is_admin=False)

    st.markdown("<h2>Archived Medical Records</h2>", unsafe_allow_html=True)

    if st.button("← Back to Dashboard"):
        st.session_state.page = "doctor_dashboard"
        st.rerun()

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.subheader("Submitted Patients")

    st.warning("🔒 Archived records are read-only in this view.")

    doctor_id = st.session_state.user["id"]
    archived_from_db = get_records_by_doctor_and_status(doctor_id, "Archived")

    if not archived_from_db:
        st.info("You haven't submitted any medical records yet.")
        return

    st.caption(f"{len(archived_from_db)} archived record(s)")

    for record in archived_from_db:
        date_str = str(record.get("updated_at", ""))[:10] or "Unknown date"
        patient_name = record.get("patient_name") or "Unknown patient"
        record_id = record.get("id", "unknown")

        with st.expander(
            f"👤 {patient_name}  •  {date_str}  •  Archived",
            expanded=False,
        ):
            summary_col1, summary_col2, summary_col3 = st.columns([2, 1, 1])

            with summary_col1:
                st.markdown(f"### {patient_name}")
                st.caption("Archived clinical record")

            with summary_col2:
                st.markdown("**Date**")
                st.write(date_str)

            with summary_col3:
                st.markdown("**Status**")
                st.success("Archived")

            st.divider()

            demo1, demo2, demo3 = st.columns(3)
            demo1.markdown("**Age**")
            demo1.write(record.get("patient_age") or "—")
            demo2.markdown("**NRIC / ID**")
            demo2.write(record.get("patient_nric") or "—")
            demo3.markdown("**Gender**")
            demo3.write(record.get("patient_gender") or "—")

            st.divider()

            vital1, vital2, vital3, vital4 = st.columns(4)
            temp_value = record.get("temp") or "—"
            bp_value = record.get("bp") or "—"
            hr_value = record.get("hr") or "—"
            spo2_value = record.get("spo2") or "—"

            vital1.metric("Temperature", f"{temp_value} °C" if temp_value != "—" else "—")
            vital2.metric("Blood Pressure", bp_value)
            vital3.metric("Heart Rate", f"{hr_value} bpm" if hr_value != "—" else "—")
            vital4.metric("SpO₂", f"{spo2_value}%" if spo2_value != "—" else "—")

            st.divider()

            with st.container(border=True):
                st.markdown("#### Consultation Notes / Patient Complaint")
                archived_notes = record.get("patient_complaint") or record.get("symptoms") or ""
                archived_doctor_notes = record.get("doctor_notes") or ""
                if archived_doctor_notes and archived_doctor_notes not in archived_notes:
                    archived_notes = f"{archived_notes}\n{archived_doctor_notes}".strip()
                st.write(archived_notes or "Not recorded")

            triage_col, code_col = st.columns(2)

            with triage_col:
                with st.container(border=True):
                    st.markdown("#### Triage Department")
                    st.write(record.get("prediction") or "Not available")

            with code_col:
                with st.container(border=True):
                    st.markdown("#### ICD-10 Category")
                    st.write(record.get("icd10") or "Not available")

            with st.container(border=True):
                st.markdown("#### AI-Suggested / Doctor-Reviewed Diagnosis")
                st.write(_clean_ai_text(record.get("ai_diagnosis") or "Not available"))

            findings = [
                x.strip()
                for x in (record.get("confirmed_findings") or "").split("||")
                if x.strip()
            ]

            if findings:
                with st.container(border=True):
                    st.markdown("#### Doctor-Confirmed Findings")
                    for finding in findings:
                        st.write(f"• {finding}")

            with st.container(border=True):
                st.markdown("#### Final Clinical Record")
                st.write(_clean_ai_text(record.get("final_clinical_record") or "Not generated"))

            with st.container(border=True):
                st.markdown("#### Treatment Plan & Instructions")
                st.write(_clean_ai_text(record.get("treatment") or "No treatment plan recorded."))

            prescription_text = (record.get("prescription") or "").strip()
            if prescription_text:
                with st.container(border=True):
                    st.markdown("#### Prescription List")
                    st.write(_clean_ai_text(prescription_text))

            referral_text = (record.get("referral_letter") or "").strip()
            if referral_text:
                with st.container(border=True):
                    st.markdown("#### Referral Letter")
                    st.text_area(
                        "Archived referral letter",
                        value=_clean_ai_text(referral_text),
                        height=260,
                        disabled=True,
                        label_visibility="collapsed",
                        key=f"archived_referral_{record_id}",
                    )

            st.write("")

            try:
                archived_pdf = build_medical_record_pdf(record)
                archived_pdf_filename = (
                    f"{_safe_filename(patient_name)}_{date_str}_medical_record.pdf"
                )

                st.download_button(
                    "Download Medical Record PDF",
                    data=archived_pdf,
                    file_name=archived_pdf_filename,
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"download_record_pdf_{record_id}",
                )

            except Exception as e:
                st.error(f"Medical Record PDF Error: {e}")


# ==========================================
# 5. 总路由分配函数 
# ==========================================
def show_feature_page(page_key: str):
    if page_key == "feature_book_appointment":
        book_appointment.show()
        return

    if page_key == "feature_active_cases":
        show_active_cases()
        return

    if page_key == "feature_archived_records":
        show_archived_records()
        return

    if page_key == "feature_complication_risk":
        show_risk_alert_page("doctor_dashboard")
        return

    if page_key not in FEATURE_ROUTES:
        st.error("Page not found.")
        if st.button("Go to Login"):
            st.session_state.page = "login"
            st.rerun()
        return

    feature_name, back_page = FEATURE_ROUTES[page_key]
    coming_soon_page(feature_name, back_page)