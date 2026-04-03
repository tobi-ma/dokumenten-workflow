"""Authentication module for password protection."""

import logging

import streamlit as st

logger = logging.getLogger(__name__)


def check_password() -> bool:
    """Returns True if the user entered the correct password.
    
    Checks against st.secrets or allows direct access if no password configured.
    """
    # Get password from secrets
    try:
        correct_password = st.secrets.get("auth", {}).get("password", "")
        if not correct_password:
            logger.info("No password configured, allowing direct access")
            return True
    except Exception as e:
        logger.warning(f"Could not access secrets: {e}")
        return True  # No secrets = direct access

    def password_entered() -> None:
        """Callback when password is entered."""
        entered = st.session_state.get("password", "")
        if entered == correct_password:
            st.session_state["password_correct"] = True
            logger.info("Password correct, access granted")
            if "password" in st.session_state:
                del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False
            logger.warning("Incorrect password attempt")

    # Already authenticated
    if st.session_state.get("password_correct", False):
        return True

    # Show password input
    st.text_input(
        "Passwort",
        type="password",
        on_change=password_entered,
        key="password",
    )
    
    if st.session_state.get("password_correct") is False:
        st.error("😕 Falsches Passwort")
    
    return False


def require_auth() -> None:
    """Stop execution if not authenticated."""
    if not check_password():
        st.stop()
    st.success("✅ Passwort korrekt! App lädt...")
