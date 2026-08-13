from turtle import st

import google.generativeai as genai

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

model = genai.GenerativeModel("gemini-2.5-flash")


def generate_notification(patient, appointment, prediction):

    prompt = f"""
You are helping a healthcare clinic, called Lamine Yamal Clinic.

Generate a professional SMS reminder.

Patient Name: {patient['name']}
Gender: {patient['gender']}
Appointment Date: {appointment['date']}
Appointment Time: {appointment['time']}
Predicted No-show Risk: {prediction['risk']}

Rules
- Maximum 160 words.
- Friendly and encouraging.
- DO NOT imply that the patient is going to miss the appointment, but rather that they should attend.
- If HIGH risk:
  Encourage the patient to attend or reschedule if necessary, using a persuasive tone. The Clinic's phone number is +65 1234 5678.
- If LOW risk:
  Simply remind them of the appointment.
- Always end with "Vamos!"
"""

    response = model.generate_content(prompt)
    return response.text.strip()