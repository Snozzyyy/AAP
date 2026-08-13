from datetime import datetime
from pathlib import Path
import pandas as pd
from xgboost import XGBClassifier

model = XGBClassifier()
MODEL_PATH = Path(__file__).with_name("xgb_no_show_model.json")
model.load_model(MODEL_PATH)


def create_features(patient, appointment):

    #feature engineering to make patient and appointment info match formats used by models
    scheduled = pd.Timestamp.now()
    appointment_datetime = pd.Timestamp(
        datetime.combine(
            appointment["date"],
            appointment["time"]
        )
    )
    appointment_day = appointment_datetime
    lead_time = (appointment_day - scheduled).days
    appointment_day_of_week = appointment_day.dayofweek
    appointment_month = appointment_day.month
    scheduled_day_of_week = scheduled.dayofweek
    is_weekend = 1 if appointment_day_of_week >= 5 else 0
    gender_f = 1 if patient["gender"] == "Female" else 0
    gender_m = 1 if patient["gender"] == "Male" else 0

    return pd.DataFrame([{
        "Age": patient["age"],
        "Hypertension": patient["hypertension"],
        "Diabetes": patient["diabetes"],
        "Handicap": patient["handicap"],
        "SMS_received": patient["sms_sent"],
        "LeadTime": lead_time,
        "AppointmentDayOfWeek": appointment_day_of_week,
        "ScheduledDayOfWeek": scheduled_day_of_week,
        "IsWeekend": is_weekend,
        "AppointmentMonth": appointment_month,
        "Gender_F": gender_f,
        "Gender_M": gender_m
    }])


def predict_no_show(patient, appointment):
    X = create_features(patient, appointment)
    probability = model.predict_proba(X)[0][1]
    risk = "HIGH" if probability >= 0.5 else "LOW"
    return {
        "probability": round(probability, 3),
        "risk": risk
    }