import streamlit as st
import requests


def render(api_url, headers):
    st.title("Staff Dashboard")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Search Patient")
        with st.form("search_patient_form"):
            search_q = st.text_input("Name or UHID")
            if st.form_submit_button("Search", use_container_width=True):
                if search_q:
                    r = requests.get(f"{api_url}/api/appointments",
                                     params={"patient_uhid": search_q}, headers=headers)
                    if r.status_code == 200:
                        appts = r.json().get("appointments", [])
                        if appts:
                            for a in appts:
                                st.write(f"**{a['patient_name']}** ({a['patient_uhid']}) — {a['doctor_name']} on {a['date']} [{a['status']}]")
                        else:
                            st.info("No results found.")

    with col2:
        st.subheader("Check-in")
        with st.form("checkin_form"):
            uhid = st.text_input("Patient UHID")
            if st.form_submit_button("Check In", use_container_width=True):
                if uhid:
                    r = requests.get(f"{api_url}/api/appointments",
                                     params={"patient_uhid": uhid, "status": "booked"}, headers=headers)
                    if r.status_code == 200:
                        appts = r.json().get("appointments", [])
                        if appts:
                            st.success(f"Found {len(appts)} booked appointment(s) for {uhid}")
                            for a in appts:
                                st.write(f"{a['doctor_name']} — {a['date']} at {a['slot_time']}")
                        else:
                            st.warning(f"No booked appointments for {uhid}")

    with col3:
        st.subheader("Emergency")
        with st.form("emergency_form"):
            e_uhid = st.text_input("Patient UHID", key="emerg_uhid")
            e_doc = st.text_input("Doctor Name", key="emerg_doc")
            if st.form_submit_button("Emergency Book", use_container_width=True):
                if e_uhid and e_doc:
                    r = requests.post(f"{api_url}/api/book-appointment",
                                      json={"patient_uhid": e_uhid, "doctor_name": e_doc, "confirm": True},
                                      headers=headers)
                    if r.status_code == 200:
                        st.success("Emergency appointment booked!")
                    else:
                        try:
                            detail = r.json().get("detail", "Failed")
                        except Exception:
                            detail = "Failed"
                        st.error(detail)
