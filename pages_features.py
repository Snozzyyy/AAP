import streamlit as st
import book_appointment
from styles import coming_soon_page


FEATURE_ROUTES = {
    "feature_book_appointment": ("Book an Appointment", "patient_dashboard"),
    "feature_active_cases": ("Active Cases and AI Triage", "doctor_dashboard"),
    "feature_archived_records": ("Archived Records", "doctor_dashboard"),
    "feature_complication_risk": ("Complication Risk Alert", "doctor_dashboard"),
}


def show_feature_page(page_key: str):
    
    if page_key == "feature_book_appointment":
        book_appointment.show()
        return

    # Everything else is Coming Soon
    if page_key not in FEATURE_ROUTES:
        st.error("Page not found.")
        if st.button("Go to Login"):
            st.session_state.page = "login"
            st.rerun()
        return

    feature_name, back_page = FEATURE_ROUTES[page_key]
    coming_soon_page(feature_name, back_page)
