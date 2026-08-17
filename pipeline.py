from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import streamlit as st
from google import genai


MODEL_PATH = Path("models/xgboost_complication_model.pkl")

FEATURES = [
    "Age Group",
    "CCSR Diagnosis Description",
    "Type of Admission",
    "Emergency Department Indicator",
    "Gender",
    "Race",
    "APR Medical Surgical Description",
]


@st.cache_resource
def load_model_bundle():
    return joblib.load(MODEL_PATH)


def preprocess_input(
    age_group,
    diagnosis,
    admission_type,
    ed_indicator,
    gender,
    race,
    apr_med_surg,
):
    return pd.DataFrame([{
        "Age Group": age_group,
        "CCSR Diagnosis Description": diagnosis,
        "Type of Admission": admission_type,
        "Emergency Department Indicator": ed_indicator,
        "Gender": gender,
        "Race": race,
        "APR Medical Surgical Description": apr_med_surg,
    }])[FEATURES].astype(str)


def predict_risk(patient_df):
    bundle = load_model_bundle()

    encoder = bundle["encoder"]
    model = bundle["model"]
    id_to_class = bundle["id_to_class"]

    encoded = encoder.transform(patient_df)

    probabilities = model.predict_proba(encoded)[0]
    pred_id = int(np.argmax(probabilities))

    risk_label = id_to_class.get(
        pred_id,
        id_to_class.get(str(pred_id), str(pred_id))
    )

    return str(risk_label)

def get_valid_diagnoses():
    bundle = load_model_bundle()
    encoder = bundle["encoder"]

    diagnosis_column = "CCSR Diagnosis Description"

    for _, transformer, columns in encoder.transformers_:
        if transformer == "drop":
            continue

        columns = list(columns)

        if diagnosis_column not in columns:
            continue

        # In case the transformer is inside a Pipeline
        if hasattr(transformer, "named_steps"):
            one_hot_encoder = None

            for step in transformer.named_steps.values():
                if hasattr(step, "categories_"):
                    one_hot_encoder = step
                    break
        else:
            one_hot_encoder = transformer

        if one_hot_encoder is None or not hasattr(
            one_hot_encoder, "categories_"
        ):
            raise ValueError(
                "Could not locate diagnosis categories in the model encoder."
            )

        diagnosis_index = columns.index(diagnosis_column)

        return sorted(
            str(value)
            for value in one_hot_encoder.categories_[diagnosis_index]
        )

    raise ValueError(
        "CCSR Diagnosis Description was not found in the model encoder."
    )


def generate_alert(risk_level, patient_data):
    api_key = st.secrets["GEMINI_API_KEY"]

    client = genai.Client(api_key=api_key)

    prompt = f"""
You are generating a nurse-facing clinical decision-support alert.

Predicted complication risk: {risk_level}

Patient information:
Age Group: {patient_data['age_group']}
Diagnosis: {patient_data['diagnosis']}
Admission Type: {patient_data['admission_type']}
ED Indicator: {patient_data['ed_indicator']}
Gender: {patient_data['gender']}
Race: {patient_data['race']}
Medical/Surgical: {patient_data['apr_med_surg']}

Use these headings:

Risk summary:
Monitoring considerations:
Escalation consideration:

Keep the response under 120 words.
Do not diagnose the patient.
Do not recommend medication or dosage.
Do not invent symptoms, vital signs, or medical history.
Mention that clinical judgement is required.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    return response.text