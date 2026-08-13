import streamlit as st


def send_sms(phone_number, message):
    st.subheader("📱 SMS Notification")
    st.success("SMS Sent Successfully!")
    st.write("Recipient:")
    st.write(phone_number)
    st.write("Message:")
    st.info(message)

    return True