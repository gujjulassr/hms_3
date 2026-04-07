import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import requests

st.set_page_config(page_title="HMS 3", layout="wide")

API_URL = "http://localhost:8000"


def main():
    # Handle Google OAuth callback (token in URL params)
    params = st.query_params
    if "token" in params and "token" not in st.session_state:
        st.session_state.token = params["token"]
        st.session_state.role = params.get("role", "patient")
        st.session_state.user_name = params.get("name", "User")
        st.query_params.clear()
        st.rerun()

    if "token" not in st.session_state:
        login_page()
    else:
        dashboard()


def login_page():
    st.title("HMS 3 — Hospital Management System")

    # Google Login button
    r = requests.get(f"{API_URL}/api/auth/google/login")
    if r.status_code == 200:
        google_url = r.json()["auth_url"]
        st.link_button("Login with Google", google_url, use_container_width=True)
        st.divider()

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True, type="primary")
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
        with st.form("register_form"):
            name = st.text_input("Full Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone")
            password = st.text_input("Password", type="password")
            role = st.selectbox("Role", ["patient", "doctor", "nurse", "admin", "staff"])
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            blood_group = st.selectbox("Blood Group", ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
            specialization = st.text_input("Specialization (for doctors only)")

            if st.form_submit_button("Register", use_container_width=True):
                payload = {"email": email, "password": password, "full_name": name,
                           "phone": phone, "role": role, "gender": gender,
                           "blood_group": blood_group, "specialization": specialization}
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

    # Change password in sidebar
    with st.sidebar.expander("Change Password"):
        with st.form("change_pwd_form"):
            cur_pwd = st.text_input("Current Password", type="password", key="cur_pwd")
            new_pwd = st.text_input("New Password", type="password", key="new_pwd")
            if st.form_submit_button("Change", use_container_width=True):
                if cur_pwd and new_pwd:
                    # Get email from token
                    import jwt
                    token_data = jwt.decode(st.session_state.token, options={"verify_signature": False})
                    email = token_data.get("email", "")
                    r = requests.post(f"{API_URL}/api/auth/change-password/{email}",
                                      json={"current_password": cur_pwd, "new_password": new_pwd})
                    if r.status_code == 200:
                        st.success("Password changed!")
                    else:
                        try:
                            st.error(r.json().get("detail", "Failed"))
                        except Exception:
                            st.error("Failed")

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
        from streamlit_app.views import admin_dashboard
        admin_dashboard.render(API_URL, headers, role=role)
    else:
        st.info("Dashboard not available for your role.")


if __name__ == "__main__":
    main()
