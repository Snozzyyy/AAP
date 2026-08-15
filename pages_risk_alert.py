import streamlit as st

from pipeline import (
    preprocess_input,
    predict_risk,
    generate_alert,
)

from styles import (
    inject_css,
    nav_bar,
    footer,
)


def show_risk_alert_page(back_page="doctor_dashboard"):
    inject_css()

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
            )

            ed_indicator = st.selectbox(
                "Emergency Department Indicator",
                ["Y", "N"],
            )

            gender = st.selectbox(
                "Gender",
                ["M", "F", "U"],
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
            )

            apr_med_surg = st.selectbox(
                "Medical/Surgical Classification",
                [
                    "Medical",
                    "Surgical",
                    "Not Applicable",
                ],
            )

            diagnosis = st.text_input(
                "CCSR Diagnosis Description"
            )

        submit = st.form_submit_button(
            "Predict Risk",
            use_container_width=True,
        )

    # Prediction
    if submit:
        if not diagnosis.strip():
            st.error("Please enter a diagnosis.")
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

            st.divider()
            st.subheader("Assessment Results")

            if risk_level == "Low Risk":
                st.success("🟢 Low Risk")

            elif risk_level == "Major":
                st.warning("🟠 Major Risk")

            elif risk_level == "Extreme":
                st.error("🔴 Extreme Risk")

            else:
                st.info(risk_level)

            st.subheader("Nurse-facing Alert")
            st.info(alert)

            st.caption(
                "Decision-support only. "
                "This is not a medical diagnosis. "
                "Clinical judgement is required."
            )

        except Exception as e:
            st.error("Risk assessment failed.")
            st.caption(str(e))

    footer()