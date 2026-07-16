import streamlit as st
from database import authenticate_user, create_user
from styles import inject_css, footer, toast, alert


def show_login():
    inject_css()

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div class="auth-card">
            <div class="brand"><h1>Healthify</h1></div>
            <div class="tagline">Your Health, Simplified</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
        st.markdown('<p class="form-heading" style="font-size:18px;font-weight:600;">Sign In</p>', unsafe_allow_html=True)

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
            '<p style="text-align:center;color:#A0A0A0;font-size:13px;">Don\'t have an account?</p>',
            unsafe_allow_html=True
        )
        if st.button("SIGN UP", use_container_width=True, key="goto_signup"):
            st.session_state.page = "signup"
            st.rerun()

    footer()


def show_signup():
    inject_css()

    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown("""
        <div class="auth-card">
            <div class="brand"><h1>Healthify</h1></div>
            <div class="tagline">Create Your Account</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:32px'></div>", unsafe_allow_html=True)
        st.markdown('<p class="form-heading" style="font-size:18px;font-weight:600;">Create Account</p>', unsafe_allow_html=True)

        with st.form("signup_form", clear_on_submit=False):
            name = st.text_input("Full Name", placeholder="Jane Smith")
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="Min. 8 characters")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Re-enter password")
            role = st.selectbox("Register as", ["Patient", "Doctor"]).lower()
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
            if password != confirm_password:
                errors.append("Passwords do not match.")

            if errors:
                for e in errors:
                    alert(e, "error")
            else:
                success, message = create_user(name.strip(), email.strip().lower(), password, role)
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
            '<p style="text-align:center;color:#A0A0A0;font-size:13px;">Already have an account?</p>',
            unsafe_allow_html=True
        )
        if st.button("SIGN IN", use_container_width=True, key="goto_login"):
            st.session_state.page = "login"
            st.rerun()

    footer()
