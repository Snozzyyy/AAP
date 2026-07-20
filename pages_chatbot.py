import streamlit as st
import numpy as np
import json
import pickle
import os

# ─── Prevent TensorFlow Metal/GPU segfault on macOS ──────────────────────────
# These MUST be set before TensorFlow is imported anywhere
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["TF_METAL_DEVICE_SUPPORT"] = "0"
os.environ["MLCOMPUTE_DEVICE"] = "cpu"

from styles import inject_css, nav_bar, footer

# ─── Constants ────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_PATH_PRIMARY = os.path.join(BASE_DIR, "models", "optimised_model.keras")
MODEL_PATH_FALLBACK = os.path.join(BASE_DIR, "models", "best_model.keras")
MODEL_PATH_SAVED = os.path.join(BASE_DIR, "models", "disease_classifier_savedmodel")
FEATURE_NAMES_PATH = os.path.join(BASE_DIR, "artifacts", "feature_names.json")
LABEL_ENCODER_PATH = os.path.join(BASE_DIR, "artifacts", "label_encoder.pkl")

GEMINI_MODEL = "gemini-2.5-flash"


# ─── Model & Artifact Loading ────────────────────────────────────────────────
@st.cache_resource
def load_model():
    """Load the TensorFlow model, label encoder, and feature names."""
    try:
        import tensorflow as tf
        tf.config.set_visible_devices([], "GPU")

        model = None
        if os.path.exists(MODEL_PATH_PRIMARY):
            model = tf.keras.models.load_model(MODEL_PATH_PRIMARY)
        elif os.path.exists(MODEL_PATH_FALLBACK):
            model = tf.keras.models.load_model(MODEL_PATH_FALLBACK)
        elif os.path.exists(MODEL_PATH_SAVED):
            model = tf.keras.models.load_model(MODEL_PATH_SAVED)

        if model is None:
            return None, None, None, "Model files not found."

        with open(FEATURE_NAMES_PATH, "r") as f:
            feature_names = json.load(f)

        with open(LABEL_ENCODER_PATH, "rb") as f:
            label_encoder = pickle.load(f)

        return model, label_encoder, feature_names, None

    except Exception as e:
        return None, None, None, str(e)


def get_gemini_client(api_key):
    """Configure and return Gemini client instance."""
    from google import genai
    return genai.Client(api_key=api_key)


# ─── Core Functions ───────────────────────────────────────────────────────────

def extract_symptoms(patient_text, client, feature_names):
    """Use Gemini to extract symptoms from patient text and map to feature names."""
    from google.genai import types

    symptom_list = ", ".join(feature_names)

    prompt = f"""You are a medical symptom extraction assistant. Your job is to identify symptoms
from a patient's natural language description and map them ONLY to symptoms from the provided list.

VALID SYMPTOMS LIST:
{symptom_list}

PATIENT DESCRIPTION:
"{patient_text}"

INSTRUCTIONS:
- Identify all symptoms mentioned or implied in the patient's description.
- Map them ONLY to symptoms from the valid list above. Do not invent new symptoms.
- Handle informal language, misspellings, and abbreviations (e.g., "can't breathe" -> "shortness of breath").
- If a described symptom doesn't closely match anything in the list, skip it.
- If no valid symptoms are detected, return an empty list.

Respond in JSON format:
{{"matched_symptoms": ["symptom1", "symptom2", ...], "reasoning": "brief explanation of mapping"}}"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        result = json.loads(response.text)
        matched = [s for s in result.get("matched_symptoms", []) if s in feature_names]
        return matched, result.get("reasoning", "")
    except Exception as e:
        return [], f"Error: {str(e)}"


def create_feature_vector(symptoms, feature_names):
    """Convert list of symptom names to binary numpy array."""
    vector = np.zeros((1, len(feature_names)), dtype=np.float32)
    for symptom in symptoms:
        if symptom in feature_names:
            idx = feature_names.index(symptom)
            vector[0, idx] = 1.0
    return vector


def predict_diseases(feature_vector, model, label_encoder, top_k=5):
    """Run model prediction, return top-k diseases with confidence scores."""
    probabilities = model.predict(feature_vector, verbose=0)[0]
    top_indices = np.argsort(probabilities)[::-1][:top_k]

    predictions = []
    for idx in top_indices:
        disease = label_encoder.inverse_transform([idx])[0]
        confidence = float(probabilities[idx])
        predictions.append({"disease": disease, "confidence": confidence})

    return predictions


def assess_urgency_and_advise(predictions, symptoms, client):
    """Use Gemini to assess urgency level and provide health advice."""
    from google.genai import types

    pred_text = "\n".join(
        [f"- {p['disease']} ({p['confidence']*100:.1f}%)" for p in predictions]
    )
    symptom_text = ", ".join(symptoms)

    prompt = f"""You are a medical triage assistant. Based on the following AI-predicted conditions
and reported symptoms, assess the urgency and provide advice.

PREDICTED CONDITIONS (with confidence):
{pred_text}

REPORTED SYMPTOMS:
{symptom_text}

Provide your assessment in JSON format:
{{
    "urgency_level": "Low" or "Medium" or "High" or "Emergency",
    "explanation": "Brief 1-2 sentence explanation of urgency level",
    "advice": ["advice point 1", "advice point 2", "advice point 3"]
}}

RULES:
- Be conservative: if uncertain, lean toward higher urgency.
- Always include "Consult a healthcare professional for proper diagnosis" as one advice point.
- Keep advice actionable and concise.
- "Emergency" means seek immediate medical attention.
- "High" means see a doctor within 24 hours.
- "Medium" means schedule an appointment soon.
- "Low" means monitor and practice self-care."""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)
    except Exception as e:
        return {
            "urgency_level": "Medium",
            "explanation": "Unable to assess urgency automatically.",
            "advice": [
                "Consult a healthcare professional for proper diagnosis.",
                f"Error: {str(e)}"
            ]
        }


# ─── Main Page ────────────────────────────────────────────────────────────────

def show_ai_symptom_diagnoser():
    """Render the full AI Symptom Diagnoser chatbot page."""
    inject_css()

    user = st.session_state.user
    nav_bar(user_name=user["name"])

    col_back, col_spacer, col_logout = st.columns([1, 3, 1])
    with col_back:
        if st.button("< BACK", key="chatbot_back_btn"):
            if "chatbot_messages" in st.session_state:
                del st.session_state["chatbot_messages"]
            st.session_state.page = "patient_dashboard"
            st.rerun()
    with col_logout:
        if st.button("LOGOUT", key="chatbot_logout_btn"):
            if "chatbot_messages" in st.session_state:
                del st.session_state["chatbot_messages"]
            st.session_state.user = None
            st.session_state.page = "login"
            st.rerun()

    st.markdown("""
    <div style="margin-bottom: 8px;">
        <h2 style="font-size: 22px; font-weight: 600; margin-bottom: 4px;">
            AI Symptom Diagnoser
        </h2>
        <p style="color: #A0A0A0; font-size: 14px; margin-top: 0;">
            Describe your symptoms in plain English and get an AI-powered preliminary diagnosis
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="background: #111111; border-left: 4px solid #E53E3E; border-radius: 8px;
                padding: 12px 16px; margin-bottom: 24px;">
        <p style="color: #E53E3E !important; font-size: 13px; margin: 0;">
            <strong>Disclaimer:</strong> This tool is for educational purposes only.
            It does not provide medical diagnosis. Always consult a healthcare professional.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div style="display: flex; gap: 32px; margin-bottom: 24px; padding: 12px 16px;
                background: #111111; border: 1px solid #2D2D2D; border-radius: 8px;">
        <div>
            <span style="color: #A0A0A0; font-size: 11px; text-transform: uppercase;
                         letter-spacing: 1px;">Diseases</span>
            <div style="font-size: 18px; font-weight: 600;">175</div>
        </div>
        <div>
            <span style="color: #A0A0A0; font-size: 11px; text-transform: uppercase;
                         letter-spacing: 1px;">Symptoms</span>
            <div style="font-size: 18px; font-weight: 600;">252</div>
        </div>
        <div>
            <span style="color: #A0A0A0; font-size: 11px; text-transform: uppercase;
                         letter-spacing: 1px;">Accuracy</span>
            <div style="font-size: 18px; font-weight: 600;">~90%</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── API Key Input ────────────────────────────────────────────────────
    api_key = ""
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "")

    if api_key:
        st.session_state["chatbot_api_key"] = api_key
    elif "chatbot_api_key" not in st.session_state or not st.session_state["chatbot_api_key"]:
        st.markdown("""
        <div style="background: #111111; border: 1px solid #2D2D2D; border-radius: 8px;
                    padding: 16px; margin-bottom: 24px;">
            <p style="color: #A0A0A0; font-size: 13px; margin: 0 0 8px 0;">
                Enter your Google Gemini API key to enable AI-powered analysis
            </p>
        </div>
        """, unsafe_allow_html=True)
        key_input = st.text_input(
            "Gemini API Key",
            type="password",
            placeholder="Enter your API key...",
            key="chatbot_api_key_input",
            label_visibility="collapsed"
        )
        if key_input:
            st.session_state["chatbot_api_key"] = key_input
            st.rerun()
        footer()
        return

    # ── Load Model ───────────────────────────────────────────────────────
    model, label_encoder, feature_names, load_error = load_model()
    if model is None:
        error_msg = load_error or "Model files not found."
        st.markdown(f"""
        <div style="background: #111111; border-left: 4px solid #D69E2E; border-radius: 8px;
                    padding: 16px; margin-bottom: 24px;">
            <p style="color: #D69E2E !important; font-size: 13px; margin: 0;">
                Could not load the model: {error_msg}<br>
                Please ensure the model files are in the models/ directory.
            </p>
        </div>
        """, unsafe_allow_html=True)
        footer()
        return

    # ── Initialize Chat Messages ─────────────────────────────────────────
    if "chatbot_messages" not in st.session_state:
        st.session_state["chatbot_messages"] = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I'm your AI Health Pre-Triage Assistant. "
                    "Describe your symptoms in detail, and I'll help identify possible conditions.\n\n"
                    "For example: *\"I've been having a headache for 3 days, "
                    "with some nausea and sensitivity to light.\"*"
                )
            }
        ]

    # ── Render Chat History ──────────────────────────────────────────────
    for msg in st.session_state["chatbot_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg["role"] == "assistant" and isinstance(msg.get("data"), dict):
                data = msg["data"]

                with st.expander(
                    f"Detected Symptoms ({len(data['symptoms'])})",
                    expanded=False
                ):
                    for s in data["symptoms"]:
                        st.markdown(f"- {s}")

                for i, pred in enumerate(data["predictions"]):
                    col_name, col_bar = st.columns([2, 3])
                    with col_name:
                        st.markdown(
                            f"**{i+1}. {pred['disease'].replace('_', ' ').title()}**"
                        )
                    with col_bar:
                        st.progress(
                            min(pred["confidence"], 1.0),
                            text=f"{pred['confidence']*100:.1f}%"
                        )

    # ── Chat Input ───────────────────────────────────────────────────────
    user_input = st.chat_input("Describe your symptoms...")

    if user_input:
        st.session_state["chatbot_messages"].append(
            {"role": "user", "content": user_input}
        )
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing your symptoms..."):
                gemini_client = get_gemini_client(
                    st.session_state["chatbot_api_key"]
                )

                symptoms_detected, reasoning = extract_symptoms(
                    user_input, gemini_client, feature_names
                )

                if not symptoms_detected:
                    response_text = (
                        "I couldn't identify any specific symptoms from your description. "
                        "Could you try describing your symptoms more specifically? "
                        "For example, mention pain location, duration, or severity."
                    )
                    st.markdown(response_text)
                    st.session_state["chatbot_messages"].append(
                        {"role": "assistant", "content": response_text}
                    )
                else:
                    feature_vector = create_feature_vector(
                        symptoms_detected, feature_names
                    )
                    predictions = predict_diseases(
                        feature_vector, model, label_encoder
                    )

                    urgency_info = assess_urgency_and_advise(
                        predictions, symptoms_detected, gemini_client
                    )

                    with st.expander(
                        f"Detected Symptoms ({len(symptoms_detected)})",
                        expanded=False
                    ):
                        for s in symptoms_detected:
                            st.markdown(f"- {s}")
                        if reasoning:
                            st.caption(f"Reasoning: {reasoning}")

                    st.markdown("### Top Predictions")
                    for i, pred in enumerate(predictions):
                        col_name, col_bar = st.columns([2, 3])
                        with col_name:
                            st.markdown(
                                f"**{i+1}. "
                                f"{pred['disease'].replace('_', ' ').title()}**"
                            )
                        with col_bar:
                            st.progress(
                                min(pred["confidence"], 1.0),
                                text=f"{pred['confidence']*100:.1f}%"
                            )

                    st.markdown("### Urgency Assessment")
                    urgency_level = urgency_info.get("urgency_level", "Medium")

                    urgency_colors = {
                        "Low": "#38A169",
                        "Medium": "#D69E2E",
                        "High": "#E53E3E",
                        "Emergency": "#E53E3E"
                    }
                    u_color = urgency_colors.get(urgency_level, "#D69E2E")
                    st.markdown(f"""
                    <div style="background: #111111; border-left: 4px solid {u_color};
                                border-radius: 8px; padding: 16px; margin: 8px 0;">
                        <div style="font-size: 16px; font-weight: 600; margin-bottom: 4px; color: {u_color}; text-transform: uppercase; letter-spacing: 0.5px;">
                            {urgency_level} URGENCY
                        </div>
                        <p style="color: #A0A0A0; font-size: 13px; margin: 0;">
                            {urgency_info.get("explanation", "")}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("### Recommendations")
                    for advice_point in urgency_info.get("advice", []):
                        st.markdown(f"- {advice_point}")

                    response_data = {
                        "symptoms": symptoms_detected,
                        "predictions": predictions,
                        "urgency": urgency_info
                    }
                    summary = (
                        f"Detected {len(symptoms_detected)} symptom(s). "
                        f"Top prediction: "
                        f"{predictions[0]['disease'].replace('_', ' ').title()} "
                        f"({predictions[0]['confidence']*100:.1f}%). "
                        f"Urgency: {urgency_level}."
                    )
                    st.session_state["chatbot_messages"].append({
                        "role": "assistant",
                        "content": summary,
                        "data": response_data
                    })

    footer()
