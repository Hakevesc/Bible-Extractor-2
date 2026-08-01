"""
Canonical Streamlit entry point.

Streamlit Community Cloud auto-detects `streamlit_app.py` when no explicit
main file is set. This simply launches the full Amharic Bible downloader UI.
"""
import app

if __name__ == "__main__":
    app.main()