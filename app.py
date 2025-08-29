import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from ics import Calendar, Event
import os

st.set_page_config(page_title="Smart Scheduler", page_icon="📅")

st.title("📅 Smart Scheduler")
st.write("Upload intake responses and generate calendar invites automatically.")

# Upload CSV
uploaded_file = st.file_uploader("Upload Intake Responses (CSV)", type=["csv"])

# Example existing bookings (simulate already scheduled events)
existing_bookings = pd.DataFrame([
    {"start": "2025-09-01 10:00", "end": "2025-09-01 11:00", "title": "Team Meeting"},
    {"start": "2025-09-01 13:00", "end": "2025-09-01 14:00", "title": "Doctor Appt"}
])

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    st.write("### Intake Responses")
    st.dataframe(df)

    # Generate calendar
    cal = Calendar()

    for _, row in df.iterrows():
        start_time = datetime.strptime(row["preferred_time"], "%Y-%m-%d %H:%M")
        end_time = start_time + timedelta(hours=1)

        # Check for conflicts
        conflict = False
        for _, booked in existing_bookings.iterrows():
            booked_start = datetime.strptime(booked["start"], "%Y-%m-%d %H:%M")
            booked_end = datetime.strptime(booked["end"], "%Y-%m-%d %H:%M")
            if (start_time < booked_end and end_time > booked_start):
                conflict = True
                break

        if conflict:
            st.warning(f"⚠️ Conflict for {row['name']} at {row['preferred_time']}")
        else:
            event = Event()
            event.name = f"Consultation with {row['name']}"
            event.begin = start_time
            event.end = end_time
            event.description = row.get("email", "")
            cal.events.add(event)
            st.success(f"✅ Scheduled: {row['name']} at {row['preferred_time']}")

    # Save and offer download
    out_path = "out/scheduled_meetings.ics"
    os.makedirs("out", exist_ok=True)
    with open(out_path, "w") as f:
        f.writelines(cal.serialize_iter())

    with open(out_path, "rb") as f:
        st.download_button(
            label="📥 Download Calendar File (.ics)",
            data=f,
            file_name="scheduled_meetings.ics",
            mime="text/calendar"
        )

else:
    st.info("👆 Upload a CSV with columns: name, email, preferred_time (YYYY-MM-DD HH:MM)")

