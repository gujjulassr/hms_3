import streamlit as st
import requests


def render(api_url, headers, role="admin"):
    if role == "admin":
        tab1, tab2, tab_sess, tab4, tab5, tab6 = st.tabs(
            ["Overview", "Doctors", "Sessions", "Users", "Audit Logs", "Chat"]
        )
    else:
        tab1, tab2, tab_sess, tab5, tab6 = st.tabs(
            ["Overview", "Doctors", "Sessions", "Audit Logs", "Chat"]
        )

    # ── TAB 1: Overview ─────────────────────────────────────────────────
    with tab1:
        if st.button("Refresh", key="refresh_overview"):
            st.rerun()

        r = requests.get(f"{api_url}/api/admin/stats", headers=headers)
        if r.status_code == 200:
            stats = r.json()

            st.subheader("System Overview")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Users", stats["total_users"])
            col2.metric("Total Patients", stats["total_patients"])
            col3.metric("Total Doctors", stats["total_doctors"])
            col4.metric("Total Appointments", stats["total_appointments"])

            st.divider()

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Today's Appointments", stats["today_appointments"])
            col2.metric("Active Sessions", stats["active_sessions"])
            col3.metric("Upcoming Sessions", stats["upcoming_sessions"])
            col4.metric("Completed", stats["completed"])

            st.divider()

            col1, col2 = st.columns(2)
            col1.metric("No-Shows", stats["no_shows"])
            col2.metric("Cancellations", stats["cancellations"])
        else:
            st.error("Failed to load stats.")

    # ── TAB 2: Doctors ──────────────────────────────────────────────────
    with tab2:
        if st.button("Refresh", key="refresh_docs"):
            st.rerun()

        st.subheader("All Doctors")
        r = requests.get(f"{api_url}/api/admin/doctors", headers=headers)
        if r.status_code == 200:
            doctors = r.json()["doctors"]
            if doctors:
                specs = sorted(set(d["specialization"] for d in doctors if d["specialization"]))
                dept_filter = st.selectbox("Filter by Department", ["All"] + specs, key="doc_dept_filter")
                if dept_filter != "All":
                    doctors = [d for d in doctors if d["specialization"] == dept_filter]
                for d in doctors:
                    with st.expander(f"{d['name']} — {d['specialization']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Email:** {d['email']}")
                            st.write(f"**Max Patients/Day:** {d['max_patients_per_day']}")
                            st.write(f"**Status:** {'Active' if d['is_active'] else 'Inactive'}")
                        with col2:
                            st.write(f"**Total Sessions:** {d['total_sessions']}")
                            st.write(f"**Total Appointments:** {d['total_appointments']}")
                            st.write(f"**Completed:** {d['completed_appointments']}")
            else:
                st.info("No doctors registered.")

    # ── TAB 3: Sessions ────────────────────────────────────────────────
    with tab_sess:
        if st.button("Refresh", key="refresh_sessions_admin"):
            st.rerun()

        if "sess_msg" in st.session_state:
            st.success(st.session_state.pop("sess_msg"))

        st.subheader("All Sessions")

        # Filters
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            from datetime import date as dt_date
            show_all_dates = st.checkbox("All dates", value=False, key="all_dates")
            if not show_all_dates:
                sess_date = st.date_input("Date", value=dt_date.today(), key="sess_date_filter")
        with col2:
            sess_status = st.selectbox("Status", ["All", "scheduled", "active", "completed", "cancelled"], key="sess_status_filter")
        with col3:
            dr = requests.get(f"{api_url}/api/admin/doctors", headers=headers)
            depts = ["All"]
            doc_names = ["All"]
            if dr.status_code == 200:
                docs = dr.json()["doctors"]
                depts += sorted(set(d["specialization"] for d in docs if d["specialization"]))
                doc_names += sorted(set(d["name"] for d in docs))
            sess_dept = st.selectbox("Department", depts, key="sess_dept_filter")
        with col4:
            sess_doc = st.selectbox("Doctor", doc_names, key="sess_doc_filter")

        params = {}
        if sess_status != "All":
            params["status"] = sess_status
        if sess_doc != "All":
            params["doctor_name"] = sess_doc

        r = requests.get(f"{api_url}/api/admin/sessions", params=params, headers=headers)
        if r.status_code == 200:
            sessions = r.json()["sessions"]

            # Apply date and department filters client-side
            if not show_all_dates:
                sessions = [s for s in sessions if s["date"] == str(sess_date)]
            if sess_dept != "All":
                sessions = [s for s in sessions if s["specialization"] == sess_dept]

            if sessions:
                for s in sessions:
                    status_color = {"scheduled": "blue", "active": "green", "completed": "gray", "cancelled": "red"}
                    color = status_color.get(s["status"], "gray")

                    with st.expander(f"{s['doctor']} ({s['specialization']}) | {s['date']} | {s['start_time'][:5]}-{s['end_time'][:5]} | :{color}[{s['status'].upper()}]"):
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Booked", f"{s['booked']}/{s['total_slots']}")
                        col2.metric("Delay", f"{s['delay_minutes']} min")
                        col3.metric("Overtime", f"{s['overtime_minutes']} min")

                        # Action buttons based on status
                        if s["status"] == "scheduled":
                            col_a, col_c = st.columns(2)
                            with col_a:
                                if st.button("Activate", key=f"act_sess_{s['id']}", use_container_width=True):
                                    ar = requests.post(f"{api_url}/api/admin/sessions/{s['id']}/activate", headers=headers)
                                    if ar.status_code == 200:
                                        st.session_state["sess_msg"] = ar.json()["message"]
                                    else:
                                        try:
                                            st.session_state["sess_msg"] = ar.json().get("detail", "Failed")
                                        except Exception:
                                            st.session_state["sess_msg"] = "Failed"
                                    st.rerun()
                            with col_c:
                                if st.button("Cancel", key=f"can_sess_{s['id']}", use_container_width=True):
                                    cr = requests.post(f"{api_url}/api/admin/sessions/{s['id']}/cancel", headers=headers)
                                    if cr.status_code == 200:
                                        st.session_state["sess_msg"] = cr.json()["message"]
                                    else:
                                        try:
                                            st.session_state["sess_msg"] = cr.json().get("detail", "Failed")
                                        except Exception:
                                            st.session_state["sess_msg"] = "Failed"
                                    st.rerun()
                        elif s["status"] == "active":
                            col_a, col_c = st.columns(2)
                            with col_a:
                                if st.button("Complete", key=f"comp_sess_{s['id']}", use_container_width=True):
                                    cr = requests.post(f"{api_url}/api/admin/sessions/{s['id']}/complete", headers=headers)
                                    if cr.status_code == 200:
                                        st.session_state["sess_msg"] = cr.json()["message"]
                                    else:
                                        try:
                                            st.session_state["sess_msg"] = cr.json().get("detail", "Failed")
                                        except Exception:
                                            st.session_state["sess_msg"] = "Failed"
                                    st.rerun()
                            with col_c:
                                if st.button("Cancel", key=f"can_act_sess_{s['id']}", use_container_width=True):
                                    cr = requests.post(f"{api_url}/api/admin/sessions/{s['id']}/cancel", headers=headers)
                                    if cr.status_code == 200:
                                        st.session_state["sess_msg"] = cr.json()["message"]
                                    st.rerun()
            else:
                st.info("No sessions found for the selected filters.")

    # ── TAB 4: Users (admin only) ──────────────────────────────────────
    if role == "admin":
      with tab4:
        if st.button("Refresh", key="refresh_users"):
            st.rerun()

        st.subheader("User Management")
        role_filter = st.selectbox("Filter by role", ["All", "patient", "doctor", "nurse", "staff", "admin"])
        r = requests.get(f"{api_url}/api/admin/users",
                         params={"role": role_filter if role_filter != "All" else ""},
                         headers=headers)
        if "user_msg" in st.session_state:
            st.success(st.session_state.pop("user_msg"))

        if r.status_code == 200:
            users = r.json()["users"]
            if users:
                for u in users:
                    status_icon = ":green[Active]" if u["is_active"] else ":red[Inactive]"
                    with st.expander(f"{u['full_name']} — {u['role'].upper()} {status_icon}"):
                        with st.form(f"edit_user_{u['id']}"):
                            st.caption("Basic Info")
                            col1, col2 = st.columns(2)
                            with col1:
                                eu_name = st.text_input("Name", value=u["full_name"], key=f"un_{u['id']}")
                                eu_email = st.text_input("Email", value=u["email"], key=f"ue_{u['id']}")
                                eu_phone = st.text_input("Phone", value=u["phone"], key=f"up_{u['id']}")
                            with col2:
                                eu_role = st.selectbox("Role", ["patient", "doctor", "nurse", "staff", "admin"],
                                                       index=["patient", "doctor", "nurse", "staff", "admin"].index(u["role"]),
                                                       key=f"ur_{u['id']}")
                                if u["role"] == "patient":
                                    gender_opts = ["", "Male", "Female", "Other"]
                                    eu_gender = st.selectbox("Gender", gender_opts,
                                                             index=gender_opts.index(u["gender"]) if u["gender"] in gender_opts else 0,
                                                             key=f"ug_{u['id']}")
                                    blood_opts = ["", "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
                                    eu_blood = st.selectbox("Blood Group", blood_opts,
                                                            index=blood_opts.index(u["blood_group"]) if u["blood_group"] in blood_opts else 0,
                                                            key=f"ub_{u['id']}")
                                if u["role"] == "doctor":
                                    eu_spec = st.text_input("Specialization", value=u["specialization"], key=f"us_{u['id']}")
                                    eu_max = st.number_input("Max Patients/Day", value=u["max_patients_per_day"], key=f"um_{u['id']}")

                            if u["role"] == "patient":
                                st.caption("Patient Details")
                                col3, col4 = st.columns(2)
                                with col3:
                                    eu_dob = st.text_input("Date of Birth (YYYY-MM-DD)", value=u["date_of_birth"], key=f"ud_{u['id']}")
                                    eu_address = st.text_input("Address", value=u["address"], key=f"ua_{u['id']}")
                                with col4:
                                    eu_ec_name = st.text_input("Emergency Contact Name", value=u["emergency_contact_name"], key=f"ucn_{u['id']}")
                                    eu_ec_phone = st.text_input("Emergency Contact Phone", value=u["emergency_contact_phone"], key=f"ucp_{u['id']}")

                            if st.form_submit_button("Save Changes", use_container_width=True):
                                payload = {"full_name": eu_name, "email": eu_email,
                                           "phone": eu_phone, "role": eu_role}
                                if u["role"] == "patient":
                                    payload.update({"gender": eu_gender, "blood_group": eu_blood,
                                                    "date_of_birth": eu_dob, "address": eu_address,
                                                    "emergency_contact_name": eu_ec_name,
                                                    "emergency_contact_phone": eu_ec_phone})
                                if u["role"] == "doctor":
                                    payload.update({"specialization": eu_spec,
                                                    "max_patients_per_day": eu_max})
                                er = requests.put(f"{api_url}/api/admin/users/{u['id']}",
                                                  json=payload, headers=headers)
                                if er.status_code == 200:
                                    st.session_state["user_msg"] = er.json()["message"]
                                else:
                                    st.session_state["user_msg"] = "Failed to update"
                                st.rerun()
                        col_toggle, _ = st.columns(2)
                        with col_toggle:
                            label = "Deactivate" if u["is_active"] else "Activate"
                            if st.button(label, key=f"toggle_{u['id']}", use_container_width=True):
                                tr = requests.post(f"{api_url}/api/admin/toggle-user/{u['id']}", headers=headers)
                                if tr.status_code == 200:
                                    st.session_state["user_msg"] = tr.json()["message"]
                                st.rerun()
            else:
                st.info("No users found.")

        st.divider()
        st.subheader("Add New User")
        with st.form("admin_add_user_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_name = st.text_input("Full Name *")
                new_email = st.text_input("Email *")
                new_phone = st.text_input("Phone *")
                new_password = st.text_input("Password", value="password123")
            with col2:
                new_role = st.selectbox("Role *", ["patient", "doctor", "nurse", "staff", "admin"])
                new_gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                new_blood = st.selectbox("Blood Group", ["", "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
                new_spec = st.text_input("Specialization (doctors only)")

            if st.form_submit_button("Register User", use_container_width=True):
                if new_name and new_email and new_phone:
                    payload = {
                        "email": new_email, "password": new_password,
                        "full_name": new_name, "phone": new_phone,
                        "role": new_role, "gender": new_gender,
                        "blood_group": new_blood, "specialization": new_spec
                    }
                    rr = requests.post(f"{api_url}/api/auth/register", json=payload)
                    if rr.status_code == 200:
                        st.session_state["user_msg"] = rr.json().get("message", "User registered!")
                    else:
                        try:
                            st.session_state["user_msg"] = rr.json().get("detail", "Registration failed")
                        except Exception:
                            st.session_state["user_msg"] = "Registration failed"
                    st.rerun()
                else:
                    st.warning("Name, Email, and Phone are required.")

    # ── TAB 5: Audit Logs ───────────────────────────────────────────────
    with tab5:
        if st.button("Refresh", key="refresh_audit"):
            st.rerun()

        st.subheader("Audit Trail")
        col1, col2 = st.columns(2)
        with col1:
            action_filter = st.selectbox("Filter by action",
                ["All", "BOOK", "CANCEL", "RESCHEDULE", "CHECKIN", "CALL", "COMPLETE", "EMERGENCY",
                 "CREATE_SESSION", "CANCEL_SESSION",
                 "UPDATE_PROFILE", "ADD_BENEFICIARY", "UPDATE_BENEFICIARY", "DELETE_BENEFICIARY",
                 "REGISTER"])
        with col2:
            log_limit = st.selectbox("Show last", [25, 50, 100], index=1)

        r = requests.get(f"{api_url}/api/admin/audit-logs",
                         params={"limit": log_limit,
                                 "action": action_filter if action_filter != "All" else ""},
                         headers=headers)
        if r.status_code == 200:
            logs = r.json()["logs"]
            if logs:
                for log in logs:
                    d = log.get("details") or {}
                    timestamp = log["created_at"][:16] if log["created_at"] else ""
                    actor = log["user"]
                    action = log["action"]

                    # Get patient name (resolved from UHID by API)
                    patient = d.get("patient_name") or d.get("uhid", "")
                    doctor_name = d.get("doctor", "")

                    # Build human-readable description
                    if action == "BOOK":
                        desc = f"**{actor}** booked appointment for **{patient}** with **{doctor_name}**"
                        if d.get("time"):
                            desc += f" at {d['time']}"
                    elif action == "CANCEL":
                        desc = f"**{actor}** cancelled appointment for **{patient}**"
                        if doctor_name:
                            desc += f" with {doctor_name}"
                    elif action == "RESCHEDULE":
                        old_info = f"{d.get('old_date', '')} {d.get('old_time', '')[:5]}" if d.get('old_time') else ""
                        new_info = f"{d.get('new_date', '')} {d.get('new_time', '')[:5]}" if d.get('new_time') else ""
                        desc = f"**{actor}** rescheduled **{patient}** with **{doctor_name}**: {old_info} → {new_info}"
                    elif action == "CHECKIN":
                        desc = f"**{actor}** checked in **{patient}**"
                    elif action == "CALL":
                        desc = f"**{actor}** called **{patient}** into consultation"
                    elif action == "COMPLETE":
                        desc = f"**{actor}** completed appointment for **{patient}**"
                    elif action == "EMERGENCY":
                        desc = f"**{actor}** emergency booked **{patient}** with **{doctor_name}**"
                    elif action == "CREATE_SESSION":
                        desc = f"**{actor}** created session for **{doctor_name}**"
                    elif action == "CANCEL_SESSION":
                        desc = f"**{actor}** cancelled session for **{doctor_name}**"
                    elif action == "UPDATE_PROFILE":
                        desc = f"**{actor}** updated profile for **{patient}**"
                    elif action == "ADD_BENEFICIARY":
                        ben_name = d.get("name", "")
                        desc = f"**{actor}** added beneficiary **{ben_name}**"
                    elif action == "UPDATE_BENEFICIARY":
                        desc = f"**{actor}** updated beneficiary **{d.get('name', '')}**"
                    elif action == "DELETE_BENEFICIARY":
                        desc = f"**{actor}** removed beneficiary **{d.get('name', '')}**"
                    elif action == "REGISTER":
                        desc = f"**{actor}** registered"
                    else:
                        desc = f"**{actor}** {action}"

                    st.write(f"`{timestamp}` {desc}")
            else:
                st.info("No audit logs found.")

    # ── TAB 6: Chat ─────────────────────────────────────────────────────
    with tab6:
        history_key = "admin_chat_history"
        col_r, col_tts, col_clear = st.columns([1, 2, 1])
        with col_r:
            if st.button("Refresh", key="refresh_admin_chat"):
                st.session_state.pop(history_key, None)
                st.rerun()
        with col_tts:
            speak_replies = st.toggle("Speak Replies", key="admin_tts_toggle")
        with col_clear:
            if st.button("Clear Chat", key="clear_admin_chat"):
                requests.delete(f"{api_url}/api/chat/history", headers=headers)
                st.session_state[history_key] = []
                st.rerun()

        if history_key not in st.session_state:
            hr = requests.get(f"{api_url}/api/chat/history", headers=headers)
            if hr.status_code == 200:
                st.session_state[history_key] = hr.json()["messages"]
            else:
                st.session_state[history_key] = []

        for msg in st.session_state[history_key]:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["text"])
            else:
                st.chat_message("assistant").write(msg["text"])

        # TTS playback
        if "_admin_tts_audio" in st.session_state:
            st.audio(st.session_state.pop("_admin_tts_audio"), format="audio/mp3", autoplay=True)

        # Voice mode
        if speak_replies:
            from streamlit_app.components.voice_chat import voice_input
            is_processing = st.session_state.get("_admin_voice_processing", False)

            if not is_processing:
                voice_result = voice_input(auto_start=True, resume=True, key="admin_voice")
                if voice_result and isinstance(voice_result, dict) and voice_result.get("transcript"):
                    vts = voice_result.get("ts", 0)
                    if vts != st.session_state.get("_admin_last_voice_ts"):
                        st.session_state._admin_last_voice_ts = vts
                        st.session_state._admin_voice_processing = True
                        st.session_state._admin_pending_voice = voice_result["transcript"].strip()
                        st.rerun()
            else:
                st.caption("Processing your voice message...")
                voice_text = st.session_state.pop("_admin_pending_voice", "")
                if voice_text:
                    st.session_state[history_key].append({"role": "user", "text": voice_text})
                    with st.spinner("Thinking..."):
                        cr = requests.post(f"{api_url}/api/chat/message",
                                           json={"message": voice_text}, headers=headers)
                        reply = cr.json()["response"] if cr.status_code == 200 else "Something went wrong."
                    st.session_state[history_key].append({"role": "assistant", "text": reply})
                    import re
                    clean = re.sub(r'[*#_`\[\]()]', '', reply)
                    if clean.strip():
                        tts = requests.post(f"{api_url}/api/chat/speak",
                                            json={"message": clean[:4000]}, headers=headers)
                        if tts.status_code == 200:
                            st.session_state["_admin_tts_audio"] = tts.content
                st.session_state._admin_voice_processing = False
                st.rerun()

        # Text input
        chat_msg = st.chat_input("Type your message...", key="admin_chat_input")
        if chat_msg:
            st.chat_message("user").write(chat_msg)
            st.session_state[history_key].append({"role": "user", "text": chat_msg})
            with st.chat_message("assistant"):
                with st.spinner(""):
                    cr = requests.post(f"{api_url}/api/chat/message",
                                       json={"message": chat_msg}, headers=headers)
                    reply = cr.json()["response"] if cr.status_code == 200 else "Something went wrong."
                st.write(reply)
                if speak_replies:
                    import re
                    clean = re.sub(r'[*#_`\[\]()]', '', reply)
                    tts = requests.post(f"{api_url}/api/chat/speak",
                                        json={"message": clean[:4000]}, headers=headers)
                    if tts.status_code == 200:
                        st.audio(tts.content, format="audio/mp3", autoplay=True)
            st.session_state[history_key].append({"role": "assistant", "text": reply})
