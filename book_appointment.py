import streamlit as st
from datetime import datetime, time
import database
from models.no_show_predictor_xgb import predict_no_show
from services.notification import generate_notification
from services.sms_service import send_sms
from styles import inject_css, nav_bar, footer


def show():
    user = st.session_state.user
    inject_css()
    nav_bar(user_name=user["name"])

    st.markdown(
        """
        <style>
        .appointment-shell {
            background: linear-gradient(180deg, rgba(17,17,17,0.98), rgba(10,10,10,0.98));
            border: 1px solid #2D2D2D;
            border-radius: 24px;
            padding: 24px 24px 18px;
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.35);
        }

        .appointment-header {
            font-size: 22px;
            font-weight: 600;
            letter-spacing: -0.4px;
            margin: 0 0 8px 0;
            color: #FFFFFF;
        }

        .appointment-subtitle {
            color: #A0A0A0 !important;
            font-size: 14px;
            margin: 0 0 20px 0;
        }

        div[data-testid="stDateInput"], div[data-testid="stTimeInput"], div[data-testid="stRadio"], div[data-testid="stTextInput"] {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
        }

        div[data-testid="stDateInput"] label,
        div[data-testid="stTimeInput"] label,
        div[data-testid="stTextInput"] label,
        div[data-testid="stRadio"] label {
            color: #FFFFFF !important;
            font-size: 14px !important;
            font-weight: 600 !important;
            margin-bottom: 8px !important;
            line-height: 1.4 !important;
        }

        div[data-testid="stRadio"] > div {
            padding: 0 !important;
            gap: 10px !important;
        }

        div[data-testid="stRadio"] label {
            background: transparent !important;
            border: none !important;
            border-radius: 0 !important;
            padding: 0 !important;
            margin-bottom: 10px !important;
        }

        button[kind="primary"], .stButton > button {
            background: #D9D9D9 !important;
            color: #111111 !important;
            border: 1px solid #D9D9D9 !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            padding: 0.7rem 1.1rem !important;
            width: auto !important;
            min-width: 180px !important;
            box-shadow: none !important;
        }

        button[kind="primary"]:hover, .stButton > button:hover {
            background: #F0F0F0 !important;
            border-color: #F0F0F0 !important;
            color: #111111 !important;
        }

        button[kind="primary"]:focus, .stButton > button:focus {
            box-shadow: none !important;
            outline: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="appointment-shell">
            <h2 class="appointment-header">Book Appointment</h2>
            <p class="appointment-subtitle">Schedule a reminder and confirm the contact number to receive notifications.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 22px'></div>", unsafe_allow_html=True)
    patient = database.get_patient_by_user_id(
        user["id"]
    )
    if patient is None:
        patient = database.get_patient_by_id(
            user["id"]
        )
    if patient is None:
        st.error(
            "Patient not found"
        )
        return

    patient = dict(patient)
    saved_phone = str(patient.get("phone_number", "") or "").strip()

    st.markdown(
        f"""
        <h3 style="font-size: 1.8rem; font-weight: 600; letter-spacing: -0.5px; margin: 0 0 1rem 0; color: #FFFFFF;">
            Patient: {patient["name"]}
        </h3>
        """,
        unsafe_allow_html=True
    )

    appointment_date = st.date_input(
        "Appointment Date",
        min_value=datetime.today()
    )
    appointment_time = st.time_input(
        "Appointment Time",
        value=time(9, 0)
    )

    # Restrict timing to be between 9AM and 5PM
    if appointment_time < time(9, 0) or appointment_time > time(17, 0):
        st.error(
            "Appointments are only between 9AM and 5PM"
        )
        return

    phone_choice = st.radio(
        "Choose a phone number for the appointment reminder",
        options=["Use saved phone number", "Use a different phone number"],
        index=0 if saved_phone else 1,
    )

    if phone_choice == "Use saved phone number":
        phone_number = saved_phone
        if not phone_number:
            st.warning("No saved phone number was found for this patient. Please choose a different phone number.")
            phone_number = ""
    else:
        phone_number = st.text_input(
            "New Phone Number",
            value="",
            placeholder="e.g. 85052285 or +65 8505 2285"
        )

    col_back, col_submit = st.columns([1, 2])
    with col_back:
        if st.button("< Back to Dashboard", key="book_back_to_dashboard"):
            st.session_state.page = "patient_dashboard"
            st.rerun()

    with col_submit:
        if st.button("Confirm Appointment"):
            if not phone_number.strip():
                st.error("Please provide a valid phone number before confirming the appointment.")
                return

            appointment = {
                "patient_id": patient["id"],
                "date": appointment_date,
                "time": appointment_time
            }

            # Save appointment
            database.create_appointment(
                appointment
            )

            # XGBoost prediction
            prediction = predict_no_show(
                patient,
                appointment
            )

            # Log details to the console instead of showing them in the UI
            print(
                "No-show probability (progress review):",
                prediction["probability"]
            )
            print(
                "Risk level (progress review):",
                prediction["risk"]
            )

            # Generate AI message
            message = generate_notification(
                patient,
                appointment,
                prediction
            )

            recipient = str(phone_number).strip()
            recipient = (
                recipient
                .replace(" ", "")
                .replace("-", "")
                .replace("(", "")
                .replace(")", "")
            )

            if recipient.startswith("+"):
                normalized_recipient = recipient
            elif len(recipient) == 8 and recipient.isdigit():
                normalized_recipient = "+65" + recipient
            elif len(recipient) == 10 and recipient.startswith("65"):
                normalized_recipient = "+" + recipient
            elif len(recipient) == 11 and recipient.startswith("65"):
                normalized_recipient = "+" + recipient
            elif len(recipient) == 9 and recipient.startswith("65"):
                normalized_recipient = "+" + recipient
            else:
                st.error("Please enter a valid phone number in a supported format.")
                return

            sent = send_sms(
                normalized_recipient,
                message
            )

            if sent:
                st.session_state["appointment_success_message"] = "WhatsApp message sent!"
                st.session_state.page = "patient_dashboard"
                st.rerun()

            print(
                "Appointment booked successfully for patient",
                patient["name"],
                "at",
                appointment_date,
                appointment_time,
                "using recipient",
                normalized_recipient
            )

    footer()