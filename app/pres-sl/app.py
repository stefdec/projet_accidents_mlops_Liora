"""Point d'entrée de la présentation Accidents MLOps."""

import streamlit as st
from components.navigation import document
from components.renderer import render


def main() -> None:
    st.set_page_config(
        page_title="Accidents MLOps",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(
        """<style>
        header, footer, #MainMenu, .stApp > header { display: none !important; }
        .block-container { padding: 0 !important; max-width: none !important; }
        .stMain { overflow: hidden !important; }
        .stVerticalBlock { gap: 0 !important; }
        .stElementContainer:has(iframe[title="st.iframe"]) {
            flex: 0 0 100vh !important;
            height: 100vh !important;
        }
        iframe[title="st.iframe"] { height: 100vh !important; }
        </style>""",
        unsafe_allow_html=True,
    )
    render(document())


if __name__ == "__main__":
    main()
