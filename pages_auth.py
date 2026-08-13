import streamlit as st
from database import authenticate_user, create_user
from styles import inject_css, footer, toast, alert


def show_login():
    inject_css()

    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    col1, col2 = st.columns([1.2, 1], gap="large")
    with col1:
        st.markdown(
            """
            <div class="auth-hero">
                <div>
                    <div class="eyebrow">Your Health, simplified</div>
                    <h1>One place for patients and providers.</h1>
                    <p>Healthify keeps registration, appointments, and follow-up actions organized in a clean workflow that ferrans fast and efficient.</p>
                    <div class="auth-points">
                        <div class="auth-point"><span class="dot"></span><span>Track patient profiles and appointment history in one system.</span></div>
                        <div class="auth-point"><span class="dot"></span><span>Separates patient, doctor, and admin access without extra clutter.</span></div>
                        <div class="auth-point"><span class="dot"></span><span>Move from sign-in to dashboard with fewer clicks and less noise.</span></div>
                    </div>
                </div>
                <div class="auth-footer-note">Secure access for every role.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("""
        <div class="auth-card">
            <div class="brand"><h1>Healthify</h1></div>
            <div class="tagline">Viva Espana!!!!</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
        st.markdown('<h4 class="form-heading">Sign In</h42>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            role = st.selectbox("Role", ["Patient", "Doctor", "Admin"]).lower()
            submitted = st.form_submit_button("LOGIN", use_container_width=True)

        if submitted:
            if not email or not password:
                alert("Please fill in all fields.", "error")
            else:
                user = authenticate_user(email, password, role)
                if user is None:
                    alert("Invalid email, password, or role.", "error")
                elif user["status"] == "pending":
                    alert("Your account is pending admin approval. Please check back later.", "warning")
                elif user["status"] == "rejected":
                    alert("Your account has been rejected. Please contact support.", "error")
                else:
                    st.session_state.user = user
                    st.session_state.page = f"{role}_dashboard"
                    st.rerun()

        st.markdown("""
        <div class="divider-with-text"><span>or</span></div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<p class="auth-helper-text">Don\'t have an account?</p>',
            unsafe_allow_html=True
        )
        if st.button("SIGN UP", use_container_width=True, key="goto_signup"):
            st.session_state.page = "signup"
            st.rerun()

    footer()
    st.markdown('</div>', unsafe_allow_html=True)


def show_signup():
    inject_css()

    st.markdown('<div class="auth-shell">', unsafe_allow_html=True)
    col1, col2 = st.columns([1.2, 1], gap="large")
    with col1:
        st.markdown(
            """
            <div class="auth-hero">
                <div>
                    <div class="eyebrow">Start here</div>
                    <h1>Create the right account in seconds.</h1>
                    <p>Patients can book appointments online and view previous appointment history, while doctors and admins can keep their workflow lighter.</p>
                    <div class="auth-points">
                        <div class="auth-point"><span class="dot"></span><span>Patient accounts capture the information needed for reminders and predictions.</span></div>
                        <div class="auth-point"><span class="dot"></span><span>Doctor and admin accounts stay simple and quick to create.</span></div>
                        <div class="auth-point"><span class="dot"></span><span>The form adapts to the role you choose, so only relevant fields appear.</span></div>
                    </div>
                </div>
                <div class="auth-footer-note">Built for a clean clinical workflow.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        st.markdown("""
        <div class="auth-card">
            <div class="brand"><h1>Healthify</h1></div>
            <div class="tagline">Create Your Account</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
        st.markdown('<p class="form-heading">Create Account</p>', unsafe_allow_html=True)

        role = st.selectbox(
        "Register as:",
        ["Patient", "Doctor"]
    ).lower()

        with st.form("signup_form", clear_on_submit=False):
            name = st.text_input("Full Name", placeholder="Jane Smith")
            email = st.text_input("Email", placeholder="you@example.com")
            age = 0
            phone_number = ""
            gender = None
            hypertension = 0
            diabetes = 0
            handicap = 0

            if role == "patient":
                gender = st.selectbox(
                    "Gender",
                    ["Male", "Female"]
                )
                phone_number = st.text_input(
                    "Phone Number",
                    placeholder="e.g. +65 1234 5678"
                )
                st.caption("You can add age and health information later from the Patient Info page.")
                age = 0
                hypertension = 0
                diabetes = 0
                handicap = 0

            password = st.text_input("Password", type="password", placeholder="Min. 8 characters")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
            submitted = st.form_submit_button("CREATE ACCOUNT", use_container_width=True)

        if submitted:
            errors = []
            if not name.strip():
                errors.append("Full name is required.")
            if not email.strip():
                errors.append("Email is required.")
            elif "@" not in email or "." not in email:
                errors.append("Please enter a valid email address.")
            if len(password) < 8:
                errors.append("Password must be at least 8 characters.")
            if role == "patient" and not phone_number.strip():
                errors.append("Phone number is required for patient accounts.")
            if password != confirm_password:
                errors.append("Passwords do not match.")

            if errors:
                for e in errors:
                    alert(e, "error")
            else:
                success, message = create_user(name.strip(), email.strip().lower(), password, role, age, phone_number, gender, hypertension, diabetes, handicap)
                if success:
                    if role == "doctor":
                        alert("Account created. Pending admin approval.", "success")
                    else:
                        toast("Account created successfully. You can now log in.", "success")
                else:
                    alert(message, "error")

        st.markdown("""
        <div class="divider-with-text"><span>or</span></div>
        """, unsafe_allow_html=True)

        st.markdown(
            '<p class="auth-helper-text">Already have an account?</p>',
            unsafe_allow_html=True
        )
        if st.button("SIGN IN", use_container_width=True, key="goto_login"):
            st.session_state.page = "login"
            st.rerun()

    footer()
    st.markdown('</div>', unsafe_allow_html=True)
