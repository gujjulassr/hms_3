import streamlit as st
import requests
from datetime import date


def render(api_url, headers):
    # Tabs for navigation
    tab_details, tab_appts, tab_book, tab_reports, tab_beneficiaries, tab_chat = st.tabs(
        ["My Details", "My Appointments", "Book Appointment", "Reports", "Beneficiaries", "Chat"]
    )

    # Fetch profile once (fast, no LLM)
    profile = None
    r = requests.get(f"{api_url}/api/my-profile", headers=headers)
    if r.status_code == 200:
        profile = r.json()

    # ── TAB 0: My Details ─────────────────────────────────────────────
    with tab_details:
        if st.button("Refresh", key="refresh_details"):
            st.rerun()

        if "profile_msg" in st.session_state:
            st.success(st.session_state.pop("profile_msg"))

        if profile:
            st.subheader("Personal Information")
            st.caption(f"UHID: {profile['uhid']} | Email: {profile['email']} (read-only)")

            with st.form("edit_profile_form"):
                col1, col2 = st.columns(2)
                with col1:
                    edit_name = st.text_input("Full Name", value=profile["name"])
                    edit_phone = st.text_input("Phone", value=profile["phone"])
                    edit_gender = st.selectbox("Gender", ["Male", "Female", "Other"],
                                              index=["Male", "Female", "Other"].index(profile["gender"]) if profile["gender"] in ["Male", "Female", "Other"] else 0)
                    edit_blood = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"],
                                             index=["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"].index(profile["blood_group"]) if profile["blood_group"] in ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"] else 0)
                with col2:
                    edit_dob = st.text_input("Date of Birth (YYYY-MM-DD)", value=profile["date_of_birth"])
                    edit_address = st.text_input("Address", value=profile["address"])
                    edit_ec_name = st.text_input("Emergency Contact Name", value=profile["emergency_contact_name"])
                    edit_ec_phone = st.text_input("Emergency Contact Phone", value=profile["emergency_contact_phone"])

                if st.form_submit_button("Save Changes", use_container_width=True):
                    r = requests.put(f"{api_url}/api/my-profile",
                                     json={"full_name": edit_name, "phone": edit_phone,
                                           "gender": edit_gender, "blood_group": edit_blood,
                                           "date_of_birth": edit_dob, "address": edit_address,
                                           "emergency_contact_name": edit_ec_name,
                                           "emergency_contact_phone": edit_ec_phone},
                                     headers=headers)
                    if r.status_code == 200:
                        st.session_state["profile_msg"] = "Profile updated!"
                    else:
                        st.error("Failed to update profile.")
                    st.rerun()

            st.divider()
            st.subheader("My Beneficiaries")
            br = requests.get(f"{api_url}/api/my-beneficiaries", headers=headers)
            if br.status_code == 200:
                bens = br.json()["beneficiaries"]
                if bens:
                    for b in bens:
                        label_parts = [b['name']]
                        if b.get('relationship'):
                            label_parts.append(b['relationship'])
                        with st.expander(" — ".join(label_parts)):
                            col1, col2 = st.columns(2)
                            with col1:
                                st.write(f"**Phone:** {b['phone'] or 'N/A'}")
                                st.write(f"**Gender:** {b['gender'] or 'N/A'}")
                            with col2:
                                st.write(f"**Blood Group:** {b['blood_group'] or 'N/A'}")
                                st.write(f"**DOB:** {b['date_of_birth'] or 'N/A'}")

                            with st.form(f"edit_ben_details_{b['id']}"):
                                st.caption("Edit details:")
                                c1, c2 = st.columns(2)
                                with c1:
                                    d_name = st.text_input("Name", value=b["name"], key=f"dn_{b['id']}")
                                    d_rel = st.text_input("Relationship", value=b["relationship"], key=f"dr_{b['id']}")
                                    d_phone = st.text_input("Phone", value=b["phone"], key=f"dp_{b['id']}")
                                with c2:
                                    gender_opts = ["Male", "Female", "Other"]
                                    d_gender = st.selectbox("Gender", gender_opts,
                                                            index=gender_opts.index(b["gender"]) if b["gender"] in gender_opts else 0,
                                                            key=f"dg_{b['id']}")
                                    blood_opts = ["", "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
                                    d_blood = st.selectbox("Blood Group", blood_opts,
                                                           index=blood_opts.index(b["blood_group"]) if b["blood_group"] in blood_opts else 0,
                                                           key=f"db_{b['id']}")
                                    d_dob = st.text_input("DOB (YYYY-MM-DD)", value=b["date_of_birth"], key=f"dd_{b['id']}")
                                if st.form_submit_button("Save", use_container_width=True):
                                    requests.put(f"{api_url}/api/my-beneficiaries/{b['id']}",
                                                 json={"name": d_name, "relationship": d_rel,
                                                       "phone": d_phone, "gender": d_gender,
                                                       "blood_group": d_blood, "date_of_birth": d_dob},
                                                 headers=headers)
                                    st.session_state["profile_msg"] = f"'{d_name}' updated."
                                    st.rerun()
                else:
                    st.info("No beneficiaries added. Go to 'Beneficiaries' tab to add.")
        else:
            st.warning("Could not load profile.")

    # ── TAB 1: My Appointments ──────────────────────────────────────────
    with tab_appts:
        if st.button("Refresh", key="refresh_appts"):
            st.rerun()
        if profile:
            col1, col2, col3 = st.columns(3)
            col1.metric("UHID", profile["uhid"])
            col2.metric("Blood Group", profile["blood_group"] or "N/A")
            col3.metric("Gender", profile["gender"] or "N/A")
            st.divider()

        r = requests.get(f"{api_url}/api/my-appointments", headers=headers)
        if r.status_code == 200:
            appts = r.json()["appointments"]
            if appts:
                active = [a for a in appts if a["status"] in ("booked", "checked_in", "in_progress")]
                past = [a for a in appts if a["status"] not in ("booked", "checked_in", "in_progress")]

                if active:
                    st.subheader("Active Appointments")
                    for a in active:
                        col1, col2, col3, col4, col5 = st.columns([3, 2, 1, 1, 1])
                        who = "You" if a.get("is_self", True) else a.get("patient_name", "")
                        col1.write(f"**{a['doctor']}** ({a['specialization']}) — for **{who}**")
                        col2.write(f"{a['date']} at {a['time']}")
                        status_color = {"booked": "blue", "checked_in": "orange", "in_progress": "green"}
                        col3.write(f":{status_color.get(a['status'], 'gray')}[{a['status'].upper()}]")
                        if a["status"] == "booked":
                            with col4:
                                if st.button("Reschedule", key=f"resched_{a.get('patient_uhid', '')}_{a['doctor']}_{a['date']}", use_container_width=True):
                                    st.session_state["reschedule_appt"] = {
                                        "doctor": a["doctor"],
                                        "old_date": a["date"],
                                        "old_time": a["time"],
                                    }
                                    st.rerun()
                            with col5:
                                if st.button("Cancel", key=f"cancel_{a.get('patient_uhid', '')}_{a['doctor']}_{a['date']}", use_container_width=True):
                                    cr = requests.post(f"{api_url}/api/cancel-my-appointment",
                                                       json={"doctor_name": a["doctor"]}, headers=headers)
                                    if cr.status_code == 200:
                                        st.success(cr.json()["message"])
                                        st.rerun()
                                    else:
                                        st.error(cr.json().get("detail", "Failed"))

                    # Reschedule form
                    if "reschedule_appt" in st.session_state:
                        rs = st.session_state["reschedule_appt"]
                        st.divider()
                        st.subheader(f"Reschedule: {rs['doctor']} ({rs['old_date']} at {rs['old_time']})")
                        with st.form("reschedule_form"):
                            col1, col2 = st.columns(2)
                            with col1:
                                new_date = st.date_input("New Date", value=date.today(), min_value=date.today(), key="resched_date")
                            with col2:
                                new_time = st.text_input("Preferred Time (HH:MM, leave empty for earliest)", key="resched_time")
                            col_s, col_c = st.columns(2)
                            with col_s:
                                if st.form_submit_button("Confirm Reschedule", use_container_width=True):
                                    rr = requests.post(f"{api_url}/api/reschedule-appointment",
                                                       json={"doctor_name": rs["doctor"],
                                                             "new_date": str(new_date),
                                                             "new_time": new_time},
                                                       headers=headers)
                                    if rr.status_code == 200:
                                        st.success(rr.json()["message"])
                                        del st.session_state["reschedule_appt"]
                                        st.rerun()
                                    else:
                                        try:
                                            st.error(rr.json().get("detail", "Reschedule failed"))
                                        except Exception:
                                            st.error("Reschedule failed")
                        if st.button("Cancel Reschedule"):
                            del st.session_state["reschedule_appt"]
                            st.rerun()

                if past:
                    st.divider()
                    st.subheader("Past Appointments")
                    for a in past:
                        col1, col2, col3 = st.columns([3, 2, 1])
                        who = "You" if a.get("is_self", True) else a.get("patient_name", "")
                        col1.write(f"**{a['doctor']}** ({a['specialization']}) — for **{who}**")
                        col2.write(f"{a['date']} at {a['time']}")
                        col3.write(a["status"].upper())
            else:
                st.info("No appointments yet. Go to 'Book Appointment' to schedule one.")

    # ── TAB 2: Book Appointment ─────────────────────────────────────────
    with tab_book:
        if st.button("Refresh", key="refresh_book"):
            st.rerun()
        if "booking_msg" in st.session_state:
            st.success(st.session_state.pop("booking_msg"))
        if "booking_error" in st.session_state:
            st.error(st.session_state.pop("booking_error"))
        st.subheader("Find a Doctor")

        # Load doctors list
        dr = requests.get(f"{api_url}/api/doctors", headers=headers)
        doctors = []
        specializations = ["All"]
        if dr.status_code == 200:
            doctors = dr.json()["doctors"]
            specs = sorted(set(d["specialization"] for d in doctors if d["specialization"]))
            specializations += specs

        # Filters
        col1, col2 = st.columns(2)
        with col1:
            selected_spec = st.selectbox("Department", specializations)
        with col2:
            book_date = st.date_input("Date", value=date.today(), min_value=date.today())

        # Show filtered doctors
        filtered = doctors
        if selected_spec != "All":
            filtered = [d for d in doctors if d["specialization"] == selected_spec]

        if not filtered:
            st.info("No doctors found for this department.")
        else:
            # Doctor selector
            doc_options = [f"{d['name']} — {d['specialization']}" for d in filtered]
            selected_idx = st.selectbox("Select Doctor", range(len(doc_options)), format_func=lambda i: doc_options[i], key="doc_select")
            d = filtered[selected_idx]

            st.divider()

            # Fetch available slots for selected date
            sr = requests.get(f"{api_url}/api/available-slots",
                              params={"doctor_name": d["name"], "date": str(book_date)},
                              headers=headers)

            if sr.status_code != 200:
                st.info(f"No session on {book_date} for {d['name']}.")
            else:
                slot_data = sr.json()
                slots = slot_data.get("slots", [])
                delay = slot_data.get("delay_minutes", 0)
                total_slots_count = slot_data.get("total_available", len(slots))

                # Summary metrics
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("Available Slots", len(slots))
                col_b.metric("Total Slots", total_slots_count)
                col_c.metric("Delay", f"{delay} min" if delay > 0 else "None")

                # Check if patient already has a booking in this session
                appt_r = requests.get(f"{api_url}/api/my-appointments", headers=headers)
                already_booked = False
                if appt_r.status_code == 200:
                    for a in appt_r.json().get("appointments", []):
                        if a.get("doctor") == d["name"] and a.get("date") == str(book_date) and a.get("status") in ("booked", "checked_in", "in_progress") and a.get("is_self", True):
                            already_booked = True
                            break

                if already_booked:
                    st.warning(f"You already have an appointment with {d['name']} on {book_date}. Cancel or reschedule from My Appointments tab.")
                elif not slots:
                    st.warning("All slots are fully booked for this date.")
                else:
                    # Check for pending confirmation
                    confirm_key = "pending_booking"
                    has_pending = confirm_key in st.session_state and st.session_state[confirm_key].get("doctor") == d["name"]

                    if has_pending:
                        sel = st.session_state[confirm_key]
                        st.info(f"You selected **{sel['time']}** with **{d['name']}** on **{sel['date']}**")
                        col_yes, col_no = st.columns(2)
                        with col_yes:
                            if st.button("Confirm Booking", key="yes_booking", use_container_width=True):
                                br = requests.post(f"{api_url}/api/book-appointment",
                                                   json={"patient_uhid": profile["uhid"],
                                                         "doctor_name": d["name"],
                                                         "preferred_time": sel["time"],
                                                         "preferred_date": sel["date"],
                                                         "confirm": True},
                                                   headers=headers)
                                del st.session_state[confirm_key]
                                if br.status_code == 200:
                                    result = br.json()
                                    if result.get("status") == "booked":
                                        st.session_state["booking_msg"] = f"Booked at {sel['time']} with {d['name']} on {sel['date']}!"
                                    else:
                                        st.session_state["booking_msg"] = result.get("message", "Check details")
                                else:
                                    try:
                                        detail = br.json().get("detail", "Booking failed")
                                    except Exception:
                                        detail = "Booking failed"
                                    st.session_state["booking_error"] = detail
                                st.rerun()
                        with col_no:
                            if st.button("Cancel", key="no_booking", use_container_width=True):
                                del st.session_state[confirm_key]
                                st.rerun()
                    else:
                        # Show slots in a grid
                        st.caption("Click a slot to book (lunch 13:00-13:30 blocked):")
                        cols_per_row = 5
                        for i in range(0, len(slots), cols_per_row):
                            cols = st.columns(cols_per_row)
                            for j, col in enumerate(cols):
                                idx = i + j
                                if idx >= len(slots):
                                    break
                                slot = slots[idx]
                                slot_label = slot["slot_time"][:5]
                                avail = slot["available_positions"]
                                max_p = slot["max_per_slot"]
                                with col:
                                    if avail == max_p:
                                        label = f"{slot_label} ({avail} free)"
                                    else:
                                        label = f"{slot_label} ({avail}/{max_p})"
                                    if st.button(label, key=f"slot_{slot['slot_number']}_{book_date}",
                                                 use_container_width=True):
                                        if profile:
                                            st.session_state["pending_booking"] = {
                                                "doctor": d["name"],
                                                "time": slot_label,
                                                "date": str(book_date)
                                            }
                                            st.rerun()

    # ── TAB: Reports ────────────────────────────────────────────────────
    with tab_reports:
        if st.button("Refresh", key="refresh_reports"):
            st.rerun()

        st.subheader("My Consultation Reports")
        r = requests.get(f"{api_url}/api/my-reports", headers=headers)
        if r.status_code == 200:
            reports = r.json()["reports"]
            if reports:
                for rpt in reports:
                    with st.expander(f"{rpt['doctor']} ({rpt['specialization']}) — {rpt['created_at'][:10]}"):
                        st.markdown(rpt["content"])
                        if rpt.get("doctor_notes"):
                            st.divider()
                            st.write(f"**Doctor's Notes:** {rpt['doctor_notes']}")
                        if rpt.get("drive_link"):
                            st.link_button("View on Google Drive", rpt["drive_link"], use_container_width=True)
            else:
                st.info("No reports yet. Reports are generated after your consultation is completed.")

    # ── TAB 3: Beneficiaries ────────────────────────────────────────────
    with tab_beneficiaries:
        if st.button("Refresh", key="refresh_ben"):
            st.rerun()
        st.subheader("My Beneficiaries")

        if "ben_msg" in st.session_state:
            st.success(st.session_state.pop("ben_msg"))

        # List existing with edit
        br = requests.get(f"{api_url}/api/my-beneficiaries", headers=headers)
        if br.status_code == 200:
            bens = br.json()["beneficiaries"]
            if bens:
                for b in bens:
                    ben_label = b['name']
                    if b.get('relationship'):
                        ben_label += f" — {b['relationship']}"
                    with st.expander(ben_label):
                        with st.form(f"edit_ben_tab_{b['id']}"):
                            col1, col2 = st.columns(2)
                            with col1:
                                eb_name = st.text_input("Name", value=b["name"], key=f"ebn_{b['id']}")
                                eb_rel = st.text_input("Relationship", value=b["relationship"], key=f"ebr_{b['id']}")
                                eb_phone = st.text_input("Phone", value=b["phone"], key=f"ebp_{b['id']}")
                            with col2:
                                gender_opts = ["Male", "Female", "Other"]
                                eb_gender = st.selectbox("Gender", gender_opts,
                                                         index=gender_opts.index(b["gender"]) if b["gender"] in gender_opts else 0,
                                                         key=f"ebg_{b['id']}")
                                blood_opts = ["", "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
                                eb_blood = st.selectbox("Blood Group", blood_opts,
                                                        index=blood_opts.index(b["blood_group"]) if b["blood_group"] in blood_opts else 0,
                                                        key=f"ebb_{b['id']}")
                                eb_dob = st.text_input("Date of Birth (YYYY-MM-DD)", value=b["date_of_birth"], key=f"ebd_{b['id']}")
                            col_s, _ = st.columns(2)
                            with col_s:
                                if st.form_submit_button("Save", use_container_width=True):
                                    requests.put(f"{api_url}/api/my-beneficiaries/{b['id']}",
                                                 json={"name": eb_name, "relationship": eb_rel,
                                                       "phone": eb_phone, "gender": eb_gender,
                                                       "blood_group": eb_blood, "date_of_birth": eb_dob},
                                                 headers=headers)
                                    st.session_state["ben_msg"] = f"'{eb_name}' updated."
                                    st.rerun()
                        if st.button("Remove", key=f"del_ben_{b['id']}", use_container_width=True):
                            requests.delete(f"{api_url}/api/my-beneficiaries/{b['id']}", headers=headers)
                            st.session_state["ben_msg"] = f"'{b['name']}' removed."
                            st.rerun()
            else:
                st.info("No beneficiaries added yet.")

        st.divider()

        # Add new
        st.subheader("Add Beneficiary")
        st.caption("Beneficiary will also be registered as a patient in the system.")
        with st.form("add_ben_form"):
            col1, col2 = st.columns(2)
            with col1:
                ben_name = st.text_input("Full Name *")
                ben_rel = st.text_input("Relationship (e.g. Spouse, Child, Parent)")
                ben_phone = st.text_input("Phone")
                ben_email = st.text_input("Email (optional — auto-generated if empty)")
            with col2:
                ben_gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="add_ben_gender")
                ben_blood = st.selectbox("Blood Group", ["", "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"], key="add_ben_blood")
                ben_dob = st.text_input("Date of Birth (YYYY-MM-DD)")
            if st.form_submit_button("Add Beneficiary", use_container_width=True):
                if ben_name:
                    ar = requests.post(f"{api_url}/api/my-beneficiaries",
                                       json={"name": ben_name, "relationship": ben_rel,
                                             "phone": ben_phone, "email": ben_email,
                                             "gender": ben_gender, "blood_group": ben_blood,
                                             "date_of_birth": ben_dob},
                                       headers=headers)
                    if ar.status_code == 200:
                        st.session_state["ben_msg"] = ar.json()["message"]
                        st.rerun()
                    else:
                        try:
                            st.error(ar.json().get("detail", "Failed to add beneficiary"))
                        except Exception:
                            st.error("Failed to add beneficiary")
                else:
                    st.warning("Name is required.")

    # ── TAB 4: Chat ─────────────────────────────────────────────────────
    with tab_chat:
        col_r, _, col_clear = st.columns([1, 3, 1])
        with col_r:
            if st.button("Refresh", key="refresh_chat"):
                st.session_state.pop("chat_history", None)
                st.rerun()
        with col_clear:
            if st.button("Clear Chat", key="clear_chat"):
                requests.delete(f"{api_url}/api/chat/history", headers=headers)
                st.session_state.chat_history = []
                st.rerun()

        # Load from MongoDB on first load
        if "chat_history" not in st.session_state:
            hr = requests.get(f"{api_url}/api/chat/history", headers=headers)
            if hr.status_code == 200:
                st.session_state.chat_history = hr.json()["messages"]
            else:
                st.session_state.chat_history = []

        # Show all previous messages
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["text"])
            else:
                st.chat_message("assistant").write(msg["text"])

        # Chat input — shows message immediately, then spinner for response
        chat_msg = st.chat_input("Type your message...", key="pat_chat_input")
        if chat_msg:
            st.chat_message("user").write(chat_msg)
            st.session_state.chat_history.append({"role": "user", "text": chat_msg})
            with st.chat_message("assistant"):
                with st.spinner(""):
                    cr = requests.post(f"{api_url}/api/chat/message",
                                       json={"message": chat_msg}, headers=headers)
                    if cr.status_code == 200:
                        reply = cr.json()["response"]
                    else:
                        reply = "Something went wrong. Please try again."
                st.write(reply)
            st.session_state.chat_history.append({"role": "assistant", "text": reply})
