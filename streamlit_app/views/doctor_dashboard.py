import streamlit as st
import requests
from datetime import date, datetime


def render(api_url, headers):
    tab1, tab2, tab3, tab4 = st.tabs(["Queue", "Session", "Patients", "Chat"])

    with tab1:
        render_queue(api_url, headers)
    with tab2:
        render_sessions(api_url, headers)
    with tab3:
        render_patients(api_url, headers)
    with tab4:
        render_chat(api_url, headers)


def render_queue(api_url, headers):
    st.subheader("Live Queue")

    # Auto-refresh every 10 seconds (disable when using Chat tab)
    from streamlit_autorefresh import st_autorefresh
    col_r, col_a = st.columns([1, 3])
    with col_r:
        if st.button("Refresh", key="refresh_q"):
            st.rerun()
    with col_a:
        auto = st.checkbox("Auto-refresh (10s)", value=False, key="auto_refresh_q")
    if auto:
        st_autorefresh(interval=10000, key="queue_autorefresh")

    res = requests.get(f"{api_url}/api/doctor/queue", headers=headers)
    if res.status_code != 200:
        st.warning("No active session. Activate a session first.")
        return

    data = res.json()
    session = data.get("session")
    if not session:
        st.info("No active session today.")
        return

    # Session info bar
    delay = data["delay_minutes"]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Status", session["status"].upper())
    col2.metric("Delay", f"{delay} min")
    col3.metric("Emergency", len(data["emergency"]))
    col4.metric("Waiting", len(data["waiting"]))

    # With Doctor (in_progress) — show emergency tag if applicable
    if data["in_progress"]:
        st.markdown("---")
        st.markdown("### :green[With Doctor]")
        for p in data["in_progress"]:
            col_a, col_b = st.columns([4, 1])
            duration = ""
            if p.get("started_at"):
                try:
                    started = datetime.fromisoformat(p["started_at"])
                    mins = int((datetime.now() - started).total_seconds() / 60)
                    duration = f" | {mins} min"
                except Exception:
                    pass
            emergency_tag = " :red[EMERGENCY]" if p.get("is_emergency") else ""
            col_a.write(f"**{p['uhid']}** — {p['name']}{emergency_tag}{duration}")
            with col_b:
                if st.button("Complete", key=f"comp_{p['uhid']}", use_container_width=True):
                    r = requests.post(f"{api_url}/api/doctor/complete-appointment",
                                     json={"patient_uhid": p["uhid"]}, headers=headers)
                    if r.status_code == 200:
                        st.success(r.json()["message"])
                    else:
                        st.error(r.json().get("detail", "Failed"))
                    st.rerun()

    # Emergency queue (checked_in emergencies waiting to be called)
    if data["emergency"]:
        st.markdown("---")
        st.markdown("### :red[Emergency Queue]")
        for p in data["emergency"]:
            col_a, col_b = st.columns([4, 1])
            wait_info = ""
            if p.get("checked_in_at"):
                try:
                    checked = datetime.fromisoformat(p["checked_in_at"])
                    wait_mins = int((datetime.now() - checked).total_seconds() / 60)
                    wait_info = f" | Waiting: {wait_mins} min"
                except Exception:
                    pass
            col_a.write(f"**{p['uhid']}** — {p['name']} | Priority: {p['priority']}{wait_info}")
            with col_b:
                if p["status"] == "checked_in":
                    if st.button("Call", key=f"call_e_{p['uhid']}", use_container_width=True):
                        r = requests.post(f"{api_url}/api/doctor/call-patient",
                                         json={"patient_uhid": p["uhid"]}, headers=headers)
                        if r.status_code == 200:
                            st.success(r.json()["message"])
                        st.rerun()

    # Waiting queue (checked in)
    if data["waiting"]:
        st.markdown("---")
        st.markdown("### :orange[Waiting]")
        for p in data["waiting"]:
            col_a, col_b = st.columns([3, 1])
            # Calculate wait time since check-in
            wait_info = ""
            if p.get("checked_in_at"):
                try:
                    checked = datetime.fromisoformat(p["checked_in_at"])
                    wait_mins = int((datetime.now() - checked).total_seconds() / 60)
                    wait_info = f" | Waiting: {wait_mins} min"
                except Exception:
                    pass
            col_a.write(f"**{p['uhid']}** — {p['name']} (Slot {p['slot_number']}, Scheduled: {p['slot_time']}, Expected: {p['expected_time']}{wait_info})")
            with col_b:
                if st.button("Call", key=f"call_{p['uhid']}"):
                    r = requests.post(f"{api_url}/api/doctor/call-patient",
                                     json={"patient_uhid": p["uhid"]}, headers=headers)
                    if r.status_code == 200:
                        st.success(r.json()["message"])
                    st.rerun()

    # Booked (not yet checked in)
    if data["booked"]:
        st.markdown("---")
        st.markdown("### :blue[Booked (Not Checked In)]")
        for p in data["booked"]:
            col_a, col_b, col_c = st.columns([3, 1, 1])
            col_a.write(f"**{p['uhid']}** — {p['name']} (Slot {p['slot_number']}, {p['slot_time']})")
            with col_b:
                if st.button("Check In", key=f"checkin_{p['uhid']}", use_container_width=True):
                    r = requests.post(f"{api_url}/api/doctor/checkin-patient",
                                     json={"patient_uhid": p["uhid"]}, headers=headers)
                    if r.status_code == 200:
                        st.success(r.json()["message"])
                    else:
                        try:
                            st.error(r.json().get("detail", "Failed"))
                        except Exception:
                            st.error("Check-in failed")
                    st.rerun()
            with col_c:
                if st.button("Cancel", key=f"cancel_{p['uhid']}", use_container_width=True):
                    r = requests.post(f"{api_url}/api/doctor/cancel-appointment",
                                     json={"patient_uhid": p["uhid"]}, headers=headers)
                    if r.status_code == 200:
                        st.success(r.json()["message"])
                    else:
                        try:
                            st.error(r.json().get("detail", "Failed"))
                        except Exception:
                            st.error("Cancel failed")
                    st.rerun()

    if not data["emergency"] and not data["waiting"] and not data["in_progress"] and not data["booked"]:
        st.info("No patients in queue.")

    # Emergency booking section
    st.divider()
    st.subheader("Emergency Booking")
    st.caption("Add a registered patient to emergency queue (bypasses normal slots)")
    with st.form("emergency_book_form"):
        e_uhid = st.text_input("Patient UHID (e.g. HMS-2026-00001)")
        if st.form_submit_button("Add to Emergency Queue", use_container_width=True):
            if e_uhid:
                r = requests.post(f"{api_url}/api/doctor/emergency-book",
                                 json={"patient_uhid": e_uhid.strip()}, headers=headers)
                if r.status_code == 200:
                    st.success(r.json()["message"])
                    st.rerun()
                else:
                    try:
                        st.error(r.json().get("detail", "Failed"))
                    except Exception:
                        st.error("Emergency booking failed")
            else:
                st.warning("Enter patient UHID")


def render_sessions(api_url, headers):
    st.subheader("My Sessions")

    if "session_msg" in st.session_state:
        msg_type, msg_text = st.session_state.session_msg
        if msg_type == "success":
            st.success(msg_text)
        else:
            st.error(msg_text)
        del st.session_state.session_msg

    filter_date = st.date_input("Select date", value=date.today())

    if st.button("Refresh", key="refresh_s"):
        st.rerun()

    st.divider()

    res = requests.get(f"{api_url}/api/doctor/my-sessions", headers=headers)
    if res.status_code != 200:
        st.error("Could not load sessions")
        return

    sessions = [s for s in res.json()["sessions"] if s.get("date") == str(filter_date)]
    is_today = filter_date == date.today()

    if not sessions:
        st.info(f"No sessions on {filter_date}.")
    else:
        for sess in sessions:
            status = sess["status"]

            col1, col2 = st.columns([3, 1])
            with col1:
                # Show actual end time including overtime
                display_end = sess["actual_end_time"] if sess["overtime_minutes"] > 0 else sess["end_time"]
                st.write(f"**{sess['start_time']} - {display_end}**")
                info = f"Slots: {sess['total_slots']} | Booked: {sess['booked']}"
                if sess["overtime_minutes"] > 0:
                    info += f" | Overtime: {sess['overtime_minutes']}min"
                if sess["delay_minutes"] > 0:
                    info += f" | Delay: {sess['delay_minutes']}min"
                st.write(info)
            with col2:
                if status == "scheduled":
                    st.warning("SCHEDULED")
                elif status == "active":
                    st.success("ACTIVE")
                elif status == "completed":
                    st.info("COMPLETED")

            # Actions
            if status == "scheduled":
                if is_today:
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if st.button("Activate", key=f"act_{sess['id']}", use_container_width=True):
                            r = requests.post(f"{api_url}/api/doctor/activate-session", headers=headers)
                            if r.status_code == 200:
                                st.session_state.session_msg = ("success", r.json()["message"])
                            else:
                                st.session_state.session_msg = ("error", r.json().get("detail", "Failed"))
                            st.rerun()
                    with col_b:
                        if st.button("Cancel", key=f"can_{sess['id']}", use_container_width=True):
                            r = requests.post(f"{api_url}/api/doctor/cancel-session",
                                             json={"session_id": sess["id"]}, headers=headers)
                            if r.status_code == 200:
                                st.session_state.session_msg = ("success", r.json()["message"])
                            else:
                                st.session_state.session_msg = ("error", r.json().get("detail", "Failed"))
                            st.rerun()
                else:
                    # Future session — only cancel, no activate
                    if st.button("Cancel Session", key=f"can_future_{sess['id']}", use_container_width=True):
                        r = requests.post(f"{api_url}/api/doctor/cancel-session",
                                         json={"session_id": sess["id"]}, headers=headers)
                        if r.status_code == 200:
                            st.session_state.session_msg = ("success", r.json()["message"])
                        else:
                            st.session_state.session_msg = ("error", r.json().get("detail", "Failed"))
                        st.rerun()

            elif status == "active":
                if st.button("Complete Session", key=f"comp_{sess['id']}", use_container_width=True):
                    r = requests.post(f"{api_url}/api/doctor/complete-session", headers=headers)
                    if r.status_code == 200:
                        st.session_state.session_msg = ("success", r.json()["message"])
                    else:
                        st.session_state.session_msg = ("error", r.json().get("detail", "Failed"))
                    st.rerun()

                # Extend session
                from datetime import datetime as dt, timedelta as td
                original_end_dt = dt.strptime(sess["end_time"], "%H:%M:%S")
                current_end_dt = original_end_dt + td(minutes=sess["overtime_minutes"])
                time_options = []
                max_end = dt(1900, 1, 1, 23, 45)
                t = current_end_dt + td(minutes=15)
                while t <= max_end and t.day == current_end_dt.day:
                    time_options.append(t.strftime("%H:%M"))
                    t += td(minutes=15)

                if time_options:
                    col_e1, col_e2 = st.columns([3, 1])
                    with col_e1:
                        new_end = st.selectbox("Extend to", time_options, key=f"ext_{sess['id']}")
                    with col_e2:
                        if st.button("Extend", key=f"extbtn_{sess['id']}", use_container_width=True):
                            # Calculate TOTAL overtime from original end
                            new_end_dt = dt.strptime(new_end, "%H:%M")
                            ext_min = int((new_end_dt - original_end_dt).total_seconds() / 60)
                            r = requests.post(f"{api_url}/api/doctor/extend-session",
                                             json={"extra_minutes": ext_min}, headers=headers)
                            if r.status_code == 200:
                                st.session_state.session_msg = ("success", r.json()["message"])
                            else:
                                st.session_state.session_msg = ("error", r.json().get("detail", "Failed"))
                            st.rerun()

            st.divider()

    # Create new session
    st.subheader("Create New Session")

    # Date picker outside form so time options react immediately
    sess_date = st.date_input("Session Date", value=date.today(), min_value=date.today(), key="sess_date_pick")

    # Build time options based on selected date
    today_str = str(date.today())
    selected_str = str(sess_date)

    all_start_times = []
    for h in range(6, 24):
        for m in [0, 15, 30, 45]:
            all_start_times.append(f"{h:02d}:{m:02d}")

    # If selected date is today, filter out past times
    if selected_str == today_str:
        now = datetime.now()
        # Round up to next 15-min boundary
        cur_min = now.minute
        cur_hour = now.hour
        next_min = ((cur_min // 15) + 1) * 15
        if next_min >= 60:
            cur_hour += 1
            next_min = 0
        cutoff = f"{cur_hour:02d}:{next_min:02d}"
        all_start_times = [t for t in all_start_times if t >= cutoff]
        if all_start_times:
            st.caption(f"Today: showing times from {cutoff} onwards")

    if not all_start_times:
        st.warning("No available start times left for today. Select a future date.")
    else:
        with st.form("create_session_form"):
            col1, col2 = st.columns(2)
            with col1:
                sess_start = st.selectbox("Start Time", all_start_times)
            with col2:
                # End times must be after the first available start time
                all_end_times = []
                for h in range(6, 24):
                    for m in [0, 15, 30, 45]:
                        all_end_times.append(f"{h:02d}:{m:02d}")
                valid_end_times = [t for t in all_end_times if t > all_start_times[0]]
                sess_end = st.selectbox("End Time", valid_end_times)
                slot_dur = st.selectbox("Slot Duration (min)", [10, 15, 20, 30], index=1)

            if st.form_submit_button("Create Session"):
                r = requests.post(f"{api_url}/api/doctor/create-session",
                                 json={"session_date": selected_str, "start_time": sess_start,
                                       "end_time": sess_end, "slot_duration": slot_dur},
                                 headers=headers)
                if r.status_code == 200:
                    st.session_state.session_msg = ("success", r.json()["message"])
                else:
                    try:
                        detail = r.json().get("detail", "Failed")
                    except Exception:
                        detail = r.text or "Failed"
                    st.session_state.session_msg = ("error", detail)
                st.rerun()


def render_patients(api_url, headers):
    st.subheader("My Patients Today")
    if st.button("Refresh", key="refresh_patients"):
        st.rerun()
    res = requests.get(f"{api_url}/api/doctor/queue", headers=headers)
    if res.status_code != 200:
        st.info("No active session today.")
        return

    data = res.json()
    all_patients = data.get("emergency", []) + data.get("in_progress", []) + data.get("waiting", []) + data.get("booked", [])

    if not all_patients:
        st.info("No patients scheduled today.")
        return

    for p in all_patients:
        col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
        col1.write(f"**{p['uhid']}** — {p['name']}")
        col2.write(f"Slot {p['slot_number']} at {p['slot_time']}")
        col3.write(p["status"].upper())
        with col4:
            if p["status"] == "booked":
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Check In", key=f"pat_checkin_{p['uhid']}", use_container_width=True):
                        r = requests.post(f"{api_url}/api/doctor/checkin-patient",
                                         json={"patient_uhid": p["uhid"]}, headers=headers)
                        if r.status_code == 200:
                            st.success(r.json()["message"])
                        else:
                            try:
                                st.error(r.json().get("detail", "Failed"))
                            except Exception:
                                st.error("Check-in failed")
                        st.rerun()
                with c2:
                    if st.button("Cancel", key=f"pat_cancel_{p['uhid']}", use_container_width=True):
                        r = requests.post(f"{api_url}/api/doctor/cancel-appointment",
                                         json={"patient_uhid": p["uhid"]}, headers=headers)
                        if r.status_code == 200:
                            st.success(r.json()["message"])
                        else:
                            try:
                                st.error(r.json().get("detail", "Failed"))
                            except Exception:
                                st.error("Cancel failed")
                        st.rerun()


def render_chat(api_url, headers):
    history_key = "doc_chat_history"
    col_r, col_tts, col_clear = st.columns([1, 2, 1])
    with col_r:
        if st.button("Refresh", key="refresh_doc_chat"):
            st.session_state.pop(history_key, None)
            st.rerun()
    with col_tts:
        speak_replies = st.toggle("Speak Replies", key="doc_tts_toggle")
    with col_clear:
        if st.button("Clear Chat", key="clear_doc_chat"):
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
    if "_doc_tts_audio" in st.session_state:
        st.audio(st.session_state.pop("_doc_tts_audio"), format="audio/mp3", autoplay=True)

    # Voice mode
    if speak_replies:
        from streamlit_app.components.voice_chat import voice_input
        is_processing = st.session_state.get("_doc_voice_processing", False)

        if not is_processing:
            voice_result = voice_input(auto_start=True, resume=True, key="doc_voice")
            if voice_result and isinstance(voice_result, dict) and voice_result.get("transcript"):
                vts = voice_result.get("ts", 0)
                if vts != st.session_state.get("_doc_last_voice_ts"):
                    st.session_state._doc_last_voice_ts = vts
                    st.session_state._doc_voice_processing = True
                    st.session_state._doc_pending_voice = voice_result["transcript"].strip()
                    st.rerun()
        else:
            st.caption("Processing your voice message...")
            voice_text = st.session_state.pop("_doc_pending_voice", "")
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
                        st.session_state["_doc_tts_audio"] = tts.content
            st.session_state._doc_voice_processing = False
            st.rerun()

    # Text input
    chat_msg = st.chat_input("Type your message...", key="doc_chat_input")
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
