import streamlit as st
from styles import coming_soon_page


FEATURE_ROUTES = {
    "feature_book_appointment": ("Book an Appointment", "patient_dashboard"),
    "feature_appointment_notes": ("Create Appointment Notes", "doctor_dashboard"),
    "feature_billing_assistant": ("Billing Assistant", "doctor_dashboard"),
}


def show_feature_page(page_key: str):
    if page_key not in FEATURE_ROUTES:
        st.error("Page not found.")
        if st.button("Go to Login"):
            st.session_state.page = "login"
            st.rerun()
        return

    feature_name, back_page = FEATURE_ROUTES[page_key]
    coming_soon_page(feature_name, back_page)
