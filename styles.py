import streamlit as st

GLOBAL_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global Reset */
    html, body, .stApp, .main, .block-container,
    [data-testid="stAppViewContainer"], [data-testid="stHeader"],
    [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stStatusWidget"], section[data-testid="stSidebar"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        background-color: #000000 !important;
        color: #FFFFFF !important;
    }

    .material-symbols-outlined, [class*="material-symbols"], [data-testid="stIcon"] {
        font-family: 'Material Symbols Outlined', 'Material Icons' !important;
    }

    .stApp {
        background-color: #000000 !important;
    }

    /* Hide Streamlit defaults */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header[data-testid="stHeader"] {visibility: hidden !important; height: 0 !important;}
    [data-testid="stToolbar"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    [data-testid="manage-app-button"] {display: none !important;}
    .viewerBadge_container__r5tak {display: none !important;}
    .styles_viewerBadge__CvC9N {display: none !important;}
    ._profileContainer_gzau3_53 {display: none !important;}
    [data-testid="stActionButton"] {display: none !important;}
    .stDeployButton {display: none !important;}
    [class*="viewerBadge"] {display: none !important;}
    [data-testid="baseButton-header"] {display: none !important;}
    button[kind="header"] {display: none !important;}
    [data-testid="stSource"] {display: none !important;}
    .reportview-container .main .block-container iframe {display: none !important;}

    /* Block container */
    .block-container {
        max-width: 900px !important;
        padding-top: 48px !important;
        padding-left: 24px !important;
        padding-right: 24px !important;
    }

    /* Typography */
    h1, h2, h3, h4, h5, h6, p, label, div {
        color: #FFFFFF !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }

    .muted {
        color: #A0A0A0 !important;
        font-size: 13px;
        font-weight: 400;
    }

    /* Nav bar */
    .nav-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        height: 64px;
        padding: 0 24px;
        border-bottom: 1px solid #2D2D2D;
        margin-bottom: 40px;
        margin-left: -24px;
        margin-right: -24px;
        margin-top: -24px;
    }

    .nav-bar .app-name {
        font-size: 28px;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.5px;
    }

    .nav-bar .nav-right {
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .nav-bar .user-name {
        color: #A0A0A0;
        font-size: 14px;
        font-weight: 400;
    }

    .nav-bar .admin-badge {
        background: #2D2D2D;
        color: #FFFFFF;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 500;
    }

    /* Auth Card */
    .auth-card {
        background: #111111;
        border: 1px solid #2D2D2D;
        border-radius: 12px;
        padding: 32px;
        max-width: 420px;
        margin: 0 auto;
    }

    .auth-card .brand {
        text-align: center;
        margin-bottom: 8px;
    }

    .auth-card .brand h1 {
        font-size: 28px;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: -0.5px;
        margin: 0;
    }

    .auth-card .tagline {
        text-align: center;
        color: #A0A0A0;
        font-size: 13px;
        font-weight: 400;
        margin-bottom: 32px;
    }

    .auth-card .form-heading {
        font-size: 18px;
        font-weight: 600;
        color: #FFFFFF;
        margin-bottom: 16px;
    }

    /* Form inputs */
    div[data-testid="stForm"] {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        box-shadow: none !important;
    }

    .stTextInput > div > div > input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        caret-color: #000000 !important;
        border: 1px solid #2D2D2D !important;
        border-radius: 8px !important;
        height: 44px !important;
        font-size: 14px !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #FFFFFF !important;
        box-shadow: 0 0 0 2px rgba(255,255,255,0.2) !important;
    }

    .stTextInput > div > div > input::placeholder {
        color: #999999 !important;
        font-size: 14px !important;
    }

    .stTextInput label {
        color: #FFFFFF !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }

    /* Select box */
    .stSelectbox label {
        color: #FFFFFF !important;
        font-size: 13px !important;
        font-weight: 500 !important;
    }

    .stSelectbox > div > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #2D2D2D !important;
        border-radius: 8px !important;
    }

    .stSelectbox [data-baseweb="select"] span {
        color: #000000 !important;
    }

    .stSelectbox [data-baseweb="select"] div {
        color: #000000 !important;
    }

    .stSelectbox [data-baseweb="select"] [data-testid="stMarkdownContainer"] {
        color: #000000 !important;
    }

    .stSelectbox svg {
        fill: #000000 !important;
    }

    /* Buttons - Primary (black bg, white text, grey border) */
    .stButton > button {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border: 1px solid #2D2D2D !important;
        border-radius: 8px !important;
        height: 44px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        font-family: 'Inter', sans-serif !important;
    }

    .stButton > button:hover {
        background-color: #111111 !important;
        color: #FFFFFF !important;
        border-color: #3D3D3D !important;
        transform: translateY(-1px);
    }

    .stButton > button:active {
        transform: translateY(0px);
    }

    .stButton > button:disabled {
        opacity: 0.6 !important;
        cursor: not-allowed !important;
    }

    /* Danger button override */
    .danger-btn button {
        background-color: #E53E3E !important;
        color: #FFFFFF !important;
    }

    .danger-btn button:hover {
        background-color: rgba(229,62,62,0.85) !important;
        color: #FFFFFF !important;
    }

    /* Equalize card columns */
    [data-testid="stHorizontalBlock"] {
        align-items: stretch !important;
    }

    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div {
        height: 100%;
        display: flex;
        flex-direction: column;
    }

    /* Feature cards */
    .feature-card {
        background: #111111;
        border: 1px solid #2D2D2D;
        border-radius: 12px;
        padding: 32px;
        cursor: pointer;
        transition: all 0.2s ease;
        display: flex;
        flex-direction: column;
        height: 200px;
        box-sizing: border-box;
    }

    .feature-card:hover {
        border-color: #3D3D3D;
        transform: translateY(-2px);
    }

    .feature-card .card-icon {
        font-size: 32px;
        margin-bottom: 12px;
    }

    .feature-card .card-title {
        font-size: 16px;
        font-weight: 600;
        color: #FFFFFF;
        margin-bottom: 8px;
    }

    .feature-card .card-desc {
        font-size: 13px;
        color: #A0A0A0 !important;
        margin-bottom: 16px;
        line-height: 1.5;
        flex: 1;
    }

    .feature-card .card-link {
        font-size: 13px;
        font-weight: 500;
        color: #FFFFFF;
        text-decoration: none;
        transition: all 0.2s ease;
    }

    .feature-card .card-link:hover {
        text-decoration: underline;
    }

    /* Status badges */
    .badge-active {
        background: rgba(56,161,105,0.1);
        color: #38A169;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 500;
        display: inline-block;
    }

    .badge-pending {
        background: rgba(214,158,46,0.1);
        color: #D69E2E;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 500;
        display: inline-block;
    }

    .badge-rejected {
        background: rgba(229,62,62,0.1);
        color: #E53E3E;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 500;
        display: inline-block;
    }

    /* Count pill */
    .count-pill {
        background: #2D2D2D;
        color: #FFFFFF;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 500;
        margin-left: 8px;
    }

    /* Table headers */
    .table-header {
        color: #A0A0A0 !important;
        font-size: 13px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 500;
        padding-bottom: 12px;
        border-bottom: 1px solid #2D2D2D;
    }

    .table-row {
        padding: 12px 0;
        border-bottom: 1px solid #2D2D2D;
        min-height: 48px;
        display: flex;
        align-items: center;
    }

    /* Coming soon */
    .coming-soon {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        min-height: 50vh;
        text-align: center;
    }

    .coming-soon .cs-title {
        font-size: 22px;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 8px;
    }

    .coming-soon .cs-subtitle {
        font-size: 14px;
        color: #A0A0A0;
    }

    /* Toast */
    .toast {
        position: fixed;
        top: 24px;
        right: 24px;
        background: #1A1A1A;
        border: 1px solid #2D2D2D;
        border-radius: 8px;
        padding: 12px 20px;
        color: #FFFFFF;
        font-size: 14px;
        z-index: 9999;
        animation: fadeInOut 3s ease forwards;
    }

    .toast-success {
        border-left: 3px solid #38A169;
    }

    .toast-error {
        border-left: 3px solid #E53E3E;
    }

    .toast-warning {
        border-left: 3px solid #D69E2E;
    }

    @keyframes fadeInOut {
        0% { opacity: 0; transform: translateY(-10px); }
        10% { opacity: 1; transform: translateY(0); }
        80% { opacity: 1; transform: translateY(0); }
        100% { opacity: 0; transform: translateY(-10px); }
    }

    /* Alert messages (pending approval) */
    .alert-warning {
        background: #111111;
        border-left: 4px solid #D69E2E;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 16px 0;
    }

    .alert-warning p {
        color: #D69E2E !important;
        font-size: 13px;
        margin: 0;
    }

    .alert-success {
        background: #111111;
        border-left: 4px solid #38A169;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 16px 0;
    }

    .alert-success p {
        color: #38A169 !important;
        font-size: 13px;
        margin: 0;
    }

    .alert-error {
        background: #111111;
        border-left: 4px solid #E53E3E;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 16px 0;
    }

    .alert-error p {
        color: #E53E3E !important;
        font-size: 13px;
        margin: 0;
    }

    /* Divider */
    .divider {
        border: none;
        border-top: 1px solid #2D2D2D;
        margin: 24px 0;
    }

    .divider-with-text {
        display: flex;
        align-items: center;
        gap: 16px;
        margin: 24px 0;
    }

    .divider-with-text::before,
    .divider-with-text::after {
        content: '';
        flex: 1;
        height: 1px;
        background: #2D2D2D;
    }

    .divider-with-text span {
        color: #A0A0A0;
        font-size: 13px;
    }

    /* Footer */
    .app-footer {
        text-align: center;
        padding-top: 48px;
        padding-bottom: 24px;
        color: #A0A0A0;
        font-size: 12px;
    }

    /* Link style */
    .link {
        color: #FFFFFF;
        text-decoration: underline;
        cursor: pointer;
        font-weight: 500;
    }

    .link:hover {
        color: rgba(255,255,255,0.85);
    }

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 40px 20px;
        color: #A0A0A0;
        font-size: 14px;
    }

    /* Pending row */
    .pending-row {
        background: #111111;
        border-radius: 12px;
        padding: 16px 24px;
        margin-bottom: 8px;
        border: 1px solid #2D2D2D;
    }

    /* Override streamlit alert colors */
    .stAlert {
        background-color: #111111 !important;
        border: 1px solid #2D2D2D !important;
    }

    [data-testid="stNotification"] {
        background-color: #111111 !important;
    }

    /* Hide streamlit styled dividers */
    hr {
        border-color: #2D2D2D !important;
    }

    /* Role toggle styling */
    .role-toggle {
        display: flex;
        gap: 0;
        margin: 16px 0;
    }

    .role-toggle .toggle-btn {
        flex: 1;
        padding: 10px 16px;
        font-size: 14px;
        font-weight: 500;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s ease;
        border: 1px solid #2D2D2D;
    }

    .role-toggle .toggle-btn:first-child {
        border-radius: 8px 0 0 8px;
    }

    .role-toggle .toggle-btn:last-child {
        border-radius: 0 8px 8px 0;
    }

    .role-toggle .toggle-btn.active {
        background: #FFFFFF;
        color: #000000;
        border-color: #FFFFFF;
    }

    .role-toggle .toggle-btn.inactive {
        background: transparent;
        color: #FFFFFF;
        border-color: #2D2D2D;
    }

    /* Responsive */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 16px !important;
            padding-right: 16px !important;
        }
    }

    /* ─── Selectbox / Dropdown Styles ───────────────────────────────── */

    div[data-baseweb="select"] {
        background-color: #111111 !important;
        border: 1px solid #2D2D2D !important;
        border-radius: 8px !important;
    }

    div[data-baseweb="select"] * {
        color: #FFFFFF !important;
        background-color: transparent !important;
    }

    div[data-baseweb="select"] [data-baseweb="icon"] {
        fill: #FFFFFF !important;
    }

    div[data-baseweb="popover"], div[data-baseweb="menu"], ul[role="listbox"] {
        background-color: #111111 !important;
        border: 1px solid #2D2D2D !important;
    }

    li[role="option"], div[role="option"] {
        background-color: #111111 !important;
        color: #FFFFFF !important;
    }

    li[role="option"]:hover, div[role="option"]:hover,
    li[role="option"][aria-selected="true"], div[role="option"][aria-selected="true"] {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
    }

    /* ─── Chatbot Page Styles ────────────────────────────────────────── */

    [data-testid="stChatMessage"] {
        background: #111111 !important;
        border: 1px solid #2D2D2D !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        margin-bottom: 12px !important;
    }

    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] h1,
    [data-testid="stChatMessage"] h2,
    [data-testid="stChatMessage"] h3 {
        color: #FFFFFF !important;
    }

    /* Chat Avatar Styling - clean badge labels */
    [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"],
    [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"] {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
        border-radius: 6px !important;
        width: auto !important;
        height: auto !important;
        padding: 4px 10px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        overflow: hidden !important;
    }

    [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"] span,
    [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"] span {
        font-size: 0 !important;
        width: 0 !important;
        overflow: hidden !important;
        display: none !important;
    }

    [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"]::after {
        content: "Patient";
        font-family: 'Inter', sans-serif !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        color: #FFFFFF !important;
        white-space: nowrap;
    }

    [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"]::after {
        content: "AI Assistant";
        font-family: 'Inter', sans-serif !important;
        font-size: 11px !important;
        font-weight: 600 !important;
        color: #FFFFFF !important;
        white-space: nowrap;
    }


    /* Streamlit Standard Chat Input - Dark Minimalist Theme */
    [data-testid="stChatInput"] {
        background-color: #000000 !important;
        padding-top: 8px !important;
        padding-bottom: 16px !important;
        border: none !important;
    }

    [data-testid="stChatInput"] > div {
        background-color: #111111 !important;
        border: 1px solid #2D2D2D !important;
        border-radius: 12px !important;
    }

    [data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        color: #FFFFFF !important;
        caret-color: #FFFFFF !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 14px !important;
        border: none !important;
    }

    [data-testid="stChatInput"] textarea::placeholder {
        color: #777777 !important;
    }

    [data-testid="stChatInput"] button {
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
    }

    [data-testid="stChatInput"] button:hover {
        background-color: #444444 !important;
    }

    [data-testid="stChatInput"] button svg {
        fill: #FFFFFF !important;
        color: #FFFFFF !important;
    }

    /* Expander Styling */
    [data-testid="stExpander"] {
        background: #111111 !important;
        border: 1px solid #2D2D2D !important;
        border-radius: 8px !important;
    }

    [data-testid="stExpander"] details {
        background: #111111 !important;
        border: none !important;
    }

    [data-testid="stExpander"] summary span {
        color: #FFFFFF !important;
        font-family: 'Inter', sans-serif !important;
    }

    /* Hide icon text bleeding into expander titles */
    [data-testid="stExpander"] summary span[data-testid="stIconMaterial"],
    [data-testid="stExpander"] summary .material-symbols-outlined {
        font-size: 0 !important;
        width: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        display: none !important;
    }

    /* Progress Bar - track is dark, only filled portion is white */
    [data-testid="stProgress"] > div {
        background-color: transparent !important;
        border-radius: 4px !important;
    }

    [data-testid="stProgress"] > div > div {
        background-color: #2D2D2D !important;
        border-radius: 4px !important;
    }

    [data-testid="stProgress"] > div > div > div {
        background-color: #FFFFFF !important;
        border-radius: 4px !important;
    }

    .stProgress > div > div > div {
        background-color: #FFFFFF !important;
    }

    .stProgress p {
        color: #A0A0A0 !important;
        font-size: 12px !important;
    }

    .stSpinner > div > span {
        color: #A0A0A0 !important;
    }

    .stCaption, [data-testid="stCaptionContainer"] {
        color: #A0A0A0 !important;
    }

</style>
"""


def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.markdown("""
    <script>
    function setupCards() {
        const cards = document.querySelectorAll('.feature-card[data-card-id]');
        cards.forEach(card => {
            // Find the element-container that wraps this card's markdown
            let cardContainer = card.closest('[data-testid="stVerticalBlock"] > div, [data-testid="stVerticalBlockBorderWrapper"] > div > div > div > div, .element-container');
            if (!cardContainer) cardContainer = card.parentElement;
            // Walk siblings to find the next button container(s) and hide them
            let sibling = cardContainer ? cardContainer.nextElementSibling : null;
            while (sibling) {
                const btn = sibling.querySelector('.stButton button');
                if (btn) {
                    sibling.style.position = 'absolute';
                    sibling.style.width = '1px';
                    sibling.style.height = '1px';
                    sibling.style.overflow = 'hidden';
                    sibling.style.clip = 'rect(0,0,0,0)';
                    if (!card.dataset.bound) {
                        card.dataset.bound = 'true';
                        card.addEventListener('click', () => { btn.click(); });
                    }
                    break;
                }
                // Also hide the hidden-card-btn markdown wrappers
                if (sibling.querySelector('.hidden-card-btn')) {
                    sibling.style.display = 'none';
                }
                sibling = sibling.nextElementSibling;
            }
        });
        // Equalize card heights
        if (cards.length === 0) return;
        cards.forEach(c => c.style.height = 'auto');
        let maxH = 0;
        cards.forEach(c => { if (c.offsetHeight > maxH) maxH = c.offsetHeight; });
        if (maxH > 0) cards.forEach(c => c.style.height = maxH + 'px');
    }
    const observer = new MutationObserver(() => { setTimeout(setupCards, 100); });
    observer.observe(document.body, {childList: true, subtree: true});
    setTimeout(setupCards, 300);
    setTimeout(setupCards, 800);
    </script>
    """, unsafe_allow_html=True)


def nav_bar(user_name: str = "", is_admin: bool = False):
    right_content = ""
    if user_name:
        badge = '<span class="admin-badge">Admin</span>' if is_admin else ""
        right_content = f'<div class="nav-right">{badge}<span class="user-name">{user_name}</span></div>'
    st.markdown(f'<div class="nav-bar"><span class="app-name">Healthify</span>{right_content}</div>', unsafe_allow_html=True)


def footer():
    st.markdown("""
    <div class="app-footer">
        &copy; 2026 Healthify. All rights reserved.
    </div>
    """, unsafe_allow_html=True)


def toast(message: str, toast_type: str = "success"):
    st.markdown(f"""
    <div class="toast toast-{toast_type}">
        {message}
    </div>
    """, unsafe_allow_html=True)


def alert(message: str, alert_type: str = "warning"):
    st.markdown(f"""
    <div class="alert-{alert_type}">
        <p>{message}</p>
    </div>
    """, unsafe_allow_html=True)


def feature_card_html(icon: str, title: str, description: str, card_id: str = ""):
    data_attr = f' data-card-id="{card_id}"' if card_id else ""
    st.markdown(f"""<div class="feature-card"{data_attr}><div class="card-icon">{icon}</div><div class="card-title">{title}</div><div class="card-desc">{description}</div><span class="card-link">Open &rarr;</span></div>""", unsafe_allow_html=True)


def coming_soon_page(feature_name: str, back_page: str):
    inject_css()
    nav_bar()
    st.markdown(f"""
    <div class="coming-soon">
        <div class="cs-title">{feature_name}</div>
        <div class="cs-subtitle">Coming Soon</div>
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("< Back to Dashboard", key="back_btn", use_container_width=True):
            st.session_state.page = back_page
            st.rerun()
    footer()
