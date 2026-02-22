import streamlit as st
import streamlit_authenticator as stauth


def load_credentials_from_env():
    """Load credentials for Streamlit Authenticator from secrets."""
    username = st.secrets["USERNAME"]
    name = st.secrets["NAME"]
    password_hash = st.secrets["PASSWORD_HASH"]

    if not all([username, name, password_hash]):
        raise ValueError("Missing one or more authentication environment variables.")

    return {"usernames": {username: {"name": name, "password": password_hash}}}


def authenticate():
    """Authenticate user via Streamlit Authenticator."""
    credentials = load_credentials_from_env()
    authenticator = stauth.Authenticate(
        credentials,
        "auth_cookie",
        "auth_signature",
        cookie_expiry_days=1,
    )

    auth_status = st.session_state.get("authentication_status")
    if auth_status:
        authenticator.logout()
        return True

    authenticator.authentication_controller.logout()
    authenticator.cookie_controller.delete_cookie()

    authenticator.login()
    auth_status = st.session_state.get("authentication_status")
    if auth_status is False:
        st.error("Username/password is incorrect.")
    elif auth_status is None:
        st.info("Please enter your username and password.")
    return False
