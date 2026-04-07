import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import requests

st.set_page_config(page_title="HMS 3", layout="wide")

API_URL = "http://localhost:8000"


def main():
    if "token" not in st.session_state:
        login_page()
    else:
        dashboard()


def login_page():
    st.title("HMS 3 — Hospital Management System")
    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")
            if submitted:
                r = requests.post(f"{API_URL}/api/auth/login", json={"email": email.strip(), "password": password.strip()})
                if r.status_code == 200:
                    data = r.json()
                    st.session_state.token = data["token"]
                    st.session_state.role = data["role"]
                    st.session_state.user_name = data["name"]
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Login failed"))

    with tab2:
        name = st.text_input("Full Name", key="reg_name")
        email = st.text_input("Email", key="reg_email")
        phone = st.text_input("Phone", key="reg_phone")
        password = st.text_input("Password", type="password", key="reg_pwd")
        role = st.selectbox("Role", ["patient", "doctor", "nurse", "admin", "staff"])

        extra = {}
        if role == "patient":
            extra["gender"] = st.selectbox("Gender", ["Male", "Female", "Other"])
            extra["blood_group"] = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
        elif role == "doctor":
            extra["specialization"] = st.text_input("Specialization")

        if st.button("Register"):
            payload = {"email": email, "password": password, "full_name": name, "phone": phone, "role": role, **extra}
            r = requests.post(f"{API_URL}/api/auth/register", json=payload)
            if r.status_code == 200:
                st.success(r.json()["message"])
            else:
                st.error(r.json().get("detail", "Registration failed"))


def dashboard():
    role = st.session_state.role
    headers = {"Authorization": f"Bearer {st.session_state.token}"}

    st.sidebar.title(f"HMS 3 — {st.session_state.user_name}")
    st.sidebar.caption(f"Role: {role}")
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    if role == "doctor":
        from streamlit_app.views import doctor_dashboard
        doctor_dashboard.render(API_URL, headers)
    elif role == "patient":
        from streamlit_app.views import patient_dashboard
        patient_dashboard.render(API_URL, headers)
    elif role in ["nurse", "staff", "admin"]:
        from streamlit_app.views import staff_dashboard
        staff_dashboard.render(API_URL, headers)
    else:
        st.info("Dashboard not available for your role.")



if __name__ == "__main__":
    main()
