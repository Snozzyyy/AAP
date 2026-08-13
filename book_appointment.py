import streamlit as st
from datetime import datetime, time
import database
from models.no_show_predictor_xgb import predict_no_show
from services.notification import generate_notification
from services.sms_service import send_sms

def show():
    st.title("Book Appointment")
    user = st.session_state.user
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

    st.markdown(
    f"""
    <h3 style="font-size: 1.8rem; font-weight: medium; margin-top: -1rem; margin-bottom: 0rem;">
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
        value=time(9,0)
    )

    # Restrict timing to be between 9AM and 5PM

    if (appointment_time < time(9,0) or appointment_time > time(17,0)):
        st.error(
            "Appointments are only between 9AM and 5PM"
        )
        return

    if st.button("Confirm Appointment"):
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

        st.write(
            "No-show probability(only shown for purposes of progress review):",
            prediction["probability"]
        )
        st.write(
            "Risk level(only shown for purposes of progress review):",
            prediction["risk"]
        )

        # Generate AI message
        message = generate_notification(
            patient,
            appointment,
            prediction
        )
        recipient = patient.get("phone_number") or user.get("email") or patient.get("name")

        # Send SMS
        send_sms(
            recipient,
            message
        )

        st.success(
            "Appointment booked!"
        )