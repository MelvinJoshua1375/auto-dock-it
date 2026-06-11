"""Streamlit Cloud entry point.

Wrapped in a try/except so that if anything fails at import or run time, the
actual traceback is rendered in the browser instead of Streamlit Cloud's opaque
"Oh no. Error running app." screen. This lets the error be diagnosed without
access to the hosting dashboard's logs.
"""
import traceback

import streamlit as st

try:
    from autodock.web import render

    render()
except Exception:  # noqa: BLE001 - we want to surface *any* startup failure
    st.error(
        "Auto-Dock It failed to start. The full traceback is below — "
        "please copy it so the issue can be fixed."
    )
    st.code(traceback.format_exc(), language="text")
    st.stop()
