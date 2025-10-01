import streamlit as st

# Import custom modules
from utils.session_state import initialize_session_state
from ui.sidebar import render_sidebar
from ui.migration_tab import render_migration_tab
from ui.analysis_tab import render_analysis_tab

# 페이지 설정
st.set_page_config(
    page_title="Cloud PostgreSQL Performance Tester",
    page_icon="🚀",
    layout="wide"
)

# Initialize session state
initialize_session_state()

# 메인 타이틀
st.title("🚀 Cloud PostgreSQL Performance Tester")
st.markdown("클라우드 3사(GCP, Azure, AWS) PostgreSQL 성능 비교 도구")

st.markdown("---")

# Get config loader from session state
config_loader = st.session_state.config_loader

# Render sidebar
render_sidebar()

# 메인 콘텐츠
tab1, tab2 = st.tabs(["🔄 데이터 마이그레이션", "📈 상세 분석"])

with tab1:
    render_migration_tab()

with tab2:
    render_analysis_tab()

# 푸터
st.markdown("---")
st.markdown("🚀 **Cloud PostgreSQL Performance Tester** - 클라우드 데이터베이스 성능 최적화를 위한 도구")