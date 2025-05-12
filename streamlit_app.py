import streamlit as st
import requests
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Session State
if 'seen_updates' not in st.session_state:
    st.session_state.seen_updates = set()

st.title("📦 Guangzhou → SG Air Freight Tracker")

tracking_number = st.text_input("Enter Tracking Number")

def fetch_tracking_info(tracking_no):
    url = f"https://oms.sn-freight.com/api/kpost/common/track/list1?waybillNo={tracking_no}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["data"].get(tracking_no, {}).get("trackDtos", []), data["data"].get(tracking_no, {}).get("countryName", "")
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return [], ""

def send_email(new_entries):
    sender_email = st.secrets["email"]["sender"]
    sender_password = st.secrets["email"]["password"]
    recipient_email = st.secrets["email"]["recipient"]

    subject = "📦 New Tracking Update(s) Detected"
    body = "\n\n".join(
        [f"{e['happenTime']} - {e['trackComment']} - {e.get('remark', '') or '—'}" for e in new_entries]
    )

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipient_email, msg.as_string())
        st.success("📧 Email notification sent.")
    except Exception as e:
        st.error(f"Failed to send email: {e}")

if tracking_number:
    with st.spinner("Fetching tracking info..."):
        updates, country = fetch_tracking_info(tracking_number)

    if updates:
        st.success(f"Destination: {country}")
        new_entries = []

        for entry in sorted(updates, key=lambda x: x["happenTime"], reverse=True):
            key = (entry["happenTime"], entry["trackComment"])
            is_new = key not in st.session_state.seen_updates

            with st.container():
                st.markdown(
                    f"""
                    **🕒 {entry['happenTime']}**  
                    📌 {entry['trackComment']}  
                    📝 {entry.get('remark', '') or '—'}  
                    {'🆕 **New Update!**' if is_new else ''}
                    """
                )

            if is_new:
                st.session_state.seen_updates.add(key)
                new_entries.append(entry)

        if new_entries:
            send_email(new_entries)
        else:
            st.info("No new updates since last check.")
    else:
        st.warning("No tracking information found.")

# Manual refresh
st.button("🔄 Refresh")
