"""
Session state initialization and management for Streamlit app
"""
import streamlit as st


def initialize_session_state():
    """Initialize all session state variables"""
    if 'migration_in_progress' not in st.session_state:
        st.session_state.migration_in_progress = False
    if 'current_batch_stats' not in st.session_state:
        st.session_state.current_batch_stats = []
    if 'migration_progress' not in st.session_state:
        st.session_state.migration_progress = {
            'current_file': '',
            'files_completed': 0,
            'total_files': 0,
            'current_batch': 0,
            'total_batches_estimated': 0
        }
    if 'migration_files_queue' not in st.session_state:
        st.session_state.migration_files_queue = []
    if 'migration_results' not in st.session_state:
        st.session_state.migration_results = []
    if 'migration_migrator' not in st.session_state:
        st.session_state.migration_migrator = None
    if 'migration_initial_counts' not in st.session_state:
        st.session_state.migration_initial_counts = {}