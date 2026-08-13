import requests
import streamlit as st
import re


BASE_URL = "https://api.whatsreach.co/api/v1"


def send_sms(phone_number, message):

    api_key = st.secrets["WHATSREACH_API_KEY"]

    recipient = str(phone_number).strip()

    # Remove spaces, dashes, brackets, etc.
    recipient = re.sub(r"[\s\-\(\)]", "", recipient)

    # Singapore number entered as 91234567
    if recipient.startswith("65") and not recipient.startswith("+65"):
        recipient = "+" + recipient

    elif recipient.startswith("9") and len(recipient) == 8:
        recipient = "+65" + recipient

    # Final check
    if not re.fullmatch(r"\+[1-9]\d{7,14}", recipient):
        st.error(
            "Invalid WhatsApp number. "
            "Please enter it in international format, e.g. +6591234567"
        )
        return False

    payload = {
        "to": recipient,
        "message": message,
        "type": "text"
    }

    headers = {
        "X-API-Key": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/send",
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.ok:
            data = response.json()

            st.success("WhatsApp message sent successfully!")
            # st.write("Recipient:", recipient)
            # st.write("Message ID:", data.get("messageId"))
            # st.write("Status:", data.get("status"))

            return True

        st.error(
            f"WhatsApp message failed: {response.status_code}"
        )
        st.code(response.text)

        return False

    except requests.RequestException as e:
        st.error(f"Could not connect to WhatsReach: {e}")
        return False    