import streamlit as st

from pipeline import (
    preprocess_input,
    predict_risk,
    generate_alert,
    get_valid_diagnoses,
)

from styles import (
    inject_css,
    nav_bar,
    footer,
)


def show_risk_alert_page(back_page="doctor_dashboard"):
    inject_css()
    
    if "risk_result" not in st.session_state:
        st.session_state.risk_result = None
    
    def reset_risk_form():
        st.session_state.risk_result = None
    
        st.session_state.risk_age_group = "0 to 17"
        st.session_state.risk_admission_type = "Emergency"
        st.session_state.risk_ed_indicator = "Y"
        st.session_state.risk_gender = "M"
        st.session_state.risk_race = "White"
        st.session_state.risk_med_surg = "Medical"
        st.session_state.risk_diagnosis = "Select a diagnosis"

    user = st.session_state.get("user")
    user_name = f"Dr. {user['name']}" if user else "Healthcare Staff"

    nav_bar(user_name=user_name)

    # Header
    col1, col2 = st.columns([5, 1])

    with col1:
        st.title("Complication Risk Alert")
        st.caption(
            "Predict complication risk and generate a nurse-facing alert."
        )

    with col2:
        if st.button("BACK"):
            reset_risk_form()
            st.session_state.page = back_page
            st.rerun()

    st.divider()

    # Form
    with st.form("risk_form"):
        st.subheader("Patient Information")

        left, right = st.columns(2)

        with left:
            age_group = st.selectbox(
                "Age Group",
                [
                    "0 to 17",
                    "18 to 29",
                    "30 to 49",
                    "50 to 69",
                    "70 or Older",
                ],
                key="risk_age_group",
            )

            admission_type = st.selectbox(
                "Type of Admission",
                [
                    "Emergency",
                    "Urgent",
                    "Elective",
                    "Newborn",
                    "Trauma",
                    "Not Available",
                ],
                key="risk_admission_type",
            )

            ed_indicator = st.selectbox(
                "Emergency Department Indicator",
                ["Y", "N"],
                key="risk_ed_indicator",   
            )

            gender = st.selectbox(
                "Gender",
                ["M", "F", "U"],
                key="risk_gender",
            )

        with right:
            race = st.selectbox(
                "Race",
                [
                    "White",
                    "Black/African American",
                    "Other Race",
                    "Multi-racial",
                ],
                key="risk_race",
            )

            apr_med_surg = st.selectbox(
                "Medical/Surgical Classification",
                [
                    "Medical",
                    "Surgical",
                    "Not Applicable",
                ],
                key="risk_med_surg",
            )

        valid_diagnoses = get_valid_diagnoses()

        diagnosis = st.selectbox(
            "CCSR Diagnosis Description",
            options=["Select a diagnosis"] + valid_diagnoses,
            key="risk_diagnosis",
        )

        submit = st.form_submit_button(
            "Predict Risk",
            use_container_width=True,
        )

    # Prediction
    if submit:
        if diagnosis == "Select a diagnosis":
            st.error("Please select a diagnosis.")
            return

        # Input validation
        if not diagnosis:
            st.error("Please enter a diagnosis.")
            return

        if len(diagnosis) < 3:
            st.error("Diagnosis must contain at least 3 characters.")
            return

        if len(diagnosis) > 150:
            st.error("Diagnosis is too long. Please enter a shorter diagnosis description.")
            return

        if diagnosis.isnumeric():
            st.error("Diagnosis cannot contain only numbers.")
            return

        try:
            patient_df = preprocess_input(
                age_group,
                diagnosis,
                admission_type,
                ed_indicator,
                gender,
                race,
                apr_med_surg,
            )

            risk_level = predict_risk(patient_df)

            patient_data = {
                "age_group": age_group,
                "diagnosis": diagnosis,
                "admission_type": admission_type,
                "ed_indicator": ed_indicator,
                "gender": gender,
                "race": race,
                "apr_med_surg": apr_med_surg,
            }

            alert = generate_alert(
                risk_level,
                patient_data,
            )
            st.session_state.risk_result = {
                "risk_level": risk_level,
                "alert": alert,
            }

        except Exception as e:
            st.error("Risk assessment failed.")
            st.caption(str(e))
        
    # This must be OUTSIDE the if submit block
    if st.session_state.risk_result is not None:
        result = st.session_state.risk_result
        

        st.divider()
        st.subheader("Assessment Results")

        if result["risk_level"] == "Low Risk":
            st.success("🟢 Low Risk")

        elif result["risk_level"] == "Major":
            st.warning("🟠 Major Risk")

        elif result["risk_level"] == "Extreme":
            st.error("🔴 Extreme Risk")

        else:
            st.info(result["risk_level"])

        st.subheader("Nurse-facing Alert")
        st.info(result["alert"])

        st.caption(
            "Decision-support only. "
            "This is not a medical diagnosis. "
            "Clinical judgement is required."
        )
    
        st.button(
            "New Assessment",
            use_container_width=True,
            on_click=reset_risk_form,
        )
    
    footer()