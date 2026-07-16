import streamlit as st
from database import get_all_users, get_pending_doctors, update_user_status, delete_user, create_user
from styles import inject_css, nav_bar, footer, alert, toast


def logout():
    st.session_state.user = None
    st.session_state.page = "login"
    st.rerun()


def status_badge(status: str) -> str:
    badges = {
        "active": '<span class="badge-active">Active</span>',
        "pending": '<span class="badge-pending">Pending</span>',
        "rejected": '<span class="badge-rejected">Rejected</span>',
    }
    return badges.get(status, status)


def show_admin_dashboard():
    inject_css()
    nav_bar(user_name="Admin", is_admin=True)

    col_main, col_logout = st.columns([5, 1])
    with col_logout:
        if st.button("LOGOUT", key="admin_logout"):
            logout()

    # Pending approvals section
    pending = get_pending_doctors()
    count = len(pending)

    st.markdown(f"""
    <h2 style="font-size:18px;font-weight:600;margin-bottom:24px;">
        Pending Approvals <span class="count-pill">{count}</span>
    </h2>
    """, unsafe_allow_html=True)

    if not pending:
        st.markdown('<div class="empty-state">No pending approvals</div>', unsafe_allow_html=True)
    else:
        for doc in pending:
            st.markdown(f"""
            <div class="pending-row">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <div style="font-size:14px;font-weight:600;color:#FFFFFF;">{doc['name']}</div>
                        <div style="font-size:13px;color:#A0A0A0;margin-top:2px;">{doc['email']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            col_spacer, col_approve, col_reject = st.columns([4, 1.5, 1.5])
            with col_approve:
                if st.button("APPROVE", key=f"approve_{doc['id']}", use_container_width=True):
                    update_user_status(doc["id"], "active")
                    st.rerun()
            with col_reject:
                st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                if st.button("REJECT", key=f"reject_{doc['id']}", use_container_width=True):
                    delete_user(doc["id"])
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

    # Divider
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # Create Account section
    st.markdown('<h2 style="font-size:18px;font-weight:600;margin-bottom:24px;">Create Account</h2>', unsafe_allow_html=True)

    with st.form("admin_create_user_form", clear_on_submit=True):
        ac_col1, ac_col2 = st.columns(2, gap="medium")
        with ac_col1:
            new_name = st.text_input("Full Name", placeholder="Jane Smith", key="admin_new_name")
            new_password = st.text_input("Password", type="password", placeholder="Min. 8 characters", key="admin_new_password")
        with ac_col2:
            new_email = st.text_input("Email", placeholder="you@example.com", key="admin_new_email")
            new_role = st.selectbox("Role", ["Patient", "Doctor"], key="admin_new_role")

        create_submitted = st.form_submit_button("CREATE ACCOUNT", use_container_width=True)

    if create_submitted:
        errors = []
        if not new_name.strip():
            errors.append("Full name is required.")
        if not new_email.strip():
            errors.append("Email is required.")
        elif "@" not in new_email or "." not in new_email:
            errors.append("Please enter a valid email address.")
        if len(new_password) < 8:
            errors.append("Password must be at least 8 characters.")

        if errors:
            for e in errors:
                alert(e, "error")
        else:
            success, message = create_user(new_name.strip(), new_email.strip(), new_password, new_role.lower())
            if success:
                toast("Account created successfully.", "success")
                st.rerun()
            else:
                alert(message, "error")

    # Divider
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # All users section
    st.markdown('<h2 style="font-size:18px;font-weight:600;margin-bottom:24px;">All Users</h2>', unsafe_allow_html=True)

    users = get_all_users()

    if not users:
        st.markdown('<div class="empty-state">No registered users yet</div>', unsafe_allow_html=True)
    else:
        # Table header
        header_cols = st.columns([2.5, 3, 1.5, 1.5, 1.5])
        header_cols[0].markdown('<span class="table-header">NAME</span>', unsafe_allow_html=True)
        header_cols[1].markdown('<span class="table-header">EMAIL</span>', unsafe_allow_html=True)
        header_cols[2].markdown('<span class="table-header">ROLE</span>', unsafe_allow_html=True)
        header_cols[3].markdown('<span class="table-header">STATUS</span>', unsafe_allow_html=True)
        header_cols[4].markdown('<span class="table-header">ACTION</span>', unsafe_allow_html=True)

        st.markdown('<div style="border-bottom:1px solid #2D2D2D;margin-bottom:8px;"></div>', unsafe_allow_html=True)

        # Table rows
        for u in users:
            row = st.columns([2.5, 3, 1.5, 1.5, 1.5])
            row[0].markdown(f'<span style="font-size:14px;">{u["name"]}</span>', unsafe_allow_html=True)
            row[1].markdown(f'<span style="font-size:14px;color:#A0A0A0;">{u["email"]}</span>', unsafe_allow_html=True)
            row[2].markdown(f'<span style="font-size:14px;">{u["role"].capitalize()}</span>', unsafe_allow_html=True)
            row[3].markdown(status_badge(u["status"]), unsafe_allow_html=True)
            with row[4]:
                confirm_key = f"confirm_delete_{u['id']}"
                if st.session_state.get(confirm_key, False):
                    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("YES", key=f"yes_{u['id']}", use_container_width=True):
                            delete_user(u["id"])
                            st.session_state[confirm_key] = False
                            st.rerun()
                    with col_no:
                        if st.button("NO", key=f"no_{u['id']}", use_container_width=True):
                            st.session_state[confirm_key] = False
                            st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="danger-btn">', unsafe_allow_html=True)
                    if st.button("DELETE", key=f"delete_{u['id']}", use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    footer()
