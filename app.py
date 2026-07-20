import streamlit as st
from database import init_db
from pages_auth import show_login, show_signup
from pages_dashboards import show_patient_dashboard, show_doctor_dashboard
from pages_admin import show_admin_dashboard
from pages_features import show_feature_page, FEATURE_ROUTES

st.set_page_config(
    page_title="Healthify",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

init_db()

if "page" not in st.session_state:
    st.session_state.page = "login"
if "user" not in st.session_state:
    st.session_state.user = None

protected_pages = {
    "patient_dashboard", "doctor_dashboard", "admin_dashboard",
    "feature_ai_symptom_patient"
} | set(FEATURE_ROUTES.keys())

if st.session_state.user is None and st.session_state.page in protected_pages:
    st.session_state.page = "login"

page = st.session_state.page

if page == "login":
    show_login()
elif page == "signup":
    show_signup()
elif page == "patient_dashboard":
    show_patient_dashboard()
elif page == "doctor_dashboard":
    show_doctor_dashboard()
elif page == "admin_dashboard":
    show_admin_dashboard()
elif page == "feature_ai_symptom_patient":
    from pages_chatbot import show_ai_symptom_diagnoser
    show_ai_symptom_diagnoser()
elif page in FEATURE_ROUTES:
    show_feature_page(page)
else:
    st.session_state.page = "login"
    st.rerun()
