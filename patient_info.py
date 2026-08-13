import streamlit as st
import database
from styles import inject_css, nav_bar, footer


def show():
    user = st.session_state.user
    inject_css()
    nav_bar(user_name=user["name"])

    st.markdown(
        """
        <style>
        .patient-info-shell {
            background: linear-gradient(180deg, rgba(17,17,17,0.98), rgba(10,10,10,0.98));
            border: 1px solid #2D2D2D;
            border-radius: 24px;
            padding: 24px;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
            margin-bottom: 20px;
        }
        .patient-info-title {
            font-size: 22px;
            font-weight: 600;
            letter-spacing: -0.4px;
            margin: 0 0 8px 0;
            color: #FFFFFF;
        }
        .patient-info-subtitle {
            color: #A0A0A0 !important;
            font-size: 14px;
            margin: 0;
        }
        .stButton > button {
            background: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #FFFFFF !important;
            border-radius: 12px !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="patient-info-shell">
            <h2 class="patient-info-title">Patient Information</h2>
            <p class="patient-info-subtitle">Optional details you can fill in anytime to improve appointment reminders and health tracking.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    patient = database.get_patient_by_user_id(user["id"])
    if patient is None:
        patient = database.get_patient_by_id(user["id"])
    if patient is None:
        st.error("Patient profile not found.")
        if st.button("Back to Dashboard"):
            st.session_state.page = "patient_dashboard"
            st.rerun()
        footer()
        return

    patient = dict(patient)

    with st.form("patient_info_form", clear_on_submit=False):
        age = st.number_input(
            "Age",
            min_value=0,
            max_value=120,
            step=1,
            value=int(patient.get("age") or 0),
        )

        gender = st.selectbox(
            "Gender",
            options=["Male", "Female"],
            index=0 if str(patient.get("gender", "Male")) == "Male" else 1,
        )

        hypertension = st.checkbox(
            "Hypertension",
            value=bool(patient.get("hypertension", 0)),
        )

        diabetes = st.checkbox(
            "Diabetes",
            value=bool(patient.get("diabetes", 0)),
        )

        handicap = st.checkbox(
            "Handicap",
            value=bool(patient.get("handicap", 0)),
        )

        submitted = st.form_submit_button("Save Patient Information", use_container_width=True)

    if submitted:
        database.update_patient_profile(
            user_id=user["id"],
            age=age,
            gender=gender,
            hypertension=hypertension,
            diabetes=diabetes,
            handicap=handicap,
        )
        st.success("Patient information saved successfully.")
        st.session_state.page = "patient_dashboard"
        st.rerun()

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Back to Dashboard", use_container_width=True):
            st.session_state.page = "patient_dashboard"
            st.rerun()

    footer()
