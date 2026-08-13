import streamlit as st
from styles import inject_css, nav_bar, footer, feature_card_html


def logout():
    st.session_state.user = None
    st.session_state.page = "login"
    st.rerun()


def show_patient_dashboard():
    inject_css()
    user = st.session_state.user
    nav_bar(user_name=user["name"])

    col_main, col_logout = st.columns([5, 1])
    with col_logout:
        if st.button("LOGOUT", key="patient_logout"):
            logout()

    st.markdown(f'<h2 style="font-size:22px;font-weight:600;margin-bottom:4px;">Welcome, {user["name"]}</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#A0A0A0;font-size:14px;margin-top:0;">What would you like to do today?</p>', unsafe_allow_html=True)
    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        feature_card_html(
            icon="",
            title="AI Symptom Diagnoser",
            description="Describe your symptoms and get an AI-powered preliminary diagnosis",
            card_id="patient_symptom"
        )
        if st.button("OPEN", key="patient_symptom_btn", use_container_width=True):
            st.session_state.page = "feature_ai_symptom_patient"
            st.rerun()

    with col2:
        feature_card_html(
            icon="",
            title="Book an Appointment",
            description="Schedule and manage your medical appointments with ease",
            card_id="patient_appointment"
        )
        if st.button("OPEN", key="patient_appointment_btn", use_container_width=True):
            st.session_state.page = "feature_book_appointment"
            st.rerun()

    footer()


def show_doctor_dashboard():
    inject_css()
    user = st.session_state.user
    nav_bar(user_name=f"Dr. {user['name']}")

    col_main, col_logout = st.columns([5, 1])
    with col_logout:
        if st.button("LOGOUT", key="doctor_logout"):
            logout()

    st.markdown(f'<h2 style="font-size:22px;font-weight:600;margin-bottom:4px;">Welcome, Dr. {user["name"]}</h2>', unsafe_allow_html=True)
    st.markdown('<p style="color:#A0A0A0;font-size:14px;margin-top:0;">What would you like to do today?</p>', unsafe_allow_html=True)
    st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        feature_card_html(
            icon="",
            title="Active Cases and AI Triage",
            description="View active patient cases with AI-powered triage priority and symptom analysis",
            card_id="doctor_active_cases"
        )
        if st.button("OPEN", key="doctor_active_cases_btn", use_container_width=True):
            st.session_state.page = "feature_active_cases"
            st.rerun()

    with col2:
        feature_card_html(
            icon="",
            title="Archived Records",
            description="Access and review previously closed patient records and case histories",
            card_id="doctor_archived_records"
        )
        if st.button("OPEN", key="doctor_archived_records_btn", use_container_width=True):
            st.session_state.page = "feature_archived_records"
            st.rerun()

    col3, col4 = st.columns(2, gap="medium")

    with col3:
        feature_card_html(
            icon="",
            title="Complication Risk Alert",
            description="Monitor patients flagged for potential complications and elevated risk factors",
            card_id="doctor_complication_risk"
        )
        if st.button("OPEN", key="doctor_complication_risk_btn", use_container_width=True):
            st.session_state.page = "feature_complication_risk"
            st.rerun()

    with col3:
        feature_card_html(
            icon="",
            title="List of Patients",
            description="View and manage your list of patients",
            card_id="doctor_patients"
        )
        if st.button("OPEN", key="doctor_patients_btn", use_container_width=True):
            st.session_state.page = "feature_patient_list"
            st.rerun()

    footer()
