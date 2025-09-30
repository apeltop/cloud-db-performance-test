import streamlit as st

# Import custom modules
from utils.session_state import initialize_session_state
from ui.sidebar import render_sidebar
from ui.upload_tab import render_upload_tab
from ui.migration_tab import render_migration_tab
from ui.performance_tab import render_performance_tab
from ui.analysis_tab import render_analysis_tab
from ui.settings_tab import render_settings_tab

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

# Render sidebar and get settings
chunk_size, selected_clouds, mock_mode = render_sidebar(config_loader)

# 메인 콘텐츠
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📤 데이터 업로드", "🔄 데이터 마이그레이션", "📊 성능 비교", "📈 상세 분석", "⚙️ 설정"])

with tab1:
    render_upload_tab(chunk_size, selected_clouds, config_loader)

with tab2:
    render_migration_tab()

with tab3:
    render_performance_tab()

with tab4:
    render_analysis_tab()

with tab5:
    render_settings_tab(config_loader)

# 푸터
st.markdown("---")
st.markdown("🚀 **Cloud PostgreSQL Performance Tester** - 클라우드 데이터베이스 성능 최적화를 위한 도구")