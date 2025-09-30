"""
Sidebar component for Streamlit app
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime


def render_sidebar(config_loader):
    """Render sidebar with settings and export options"""
    st.sidebar.header("⚙️ 테스트 설정")

    # 테스트 설정
    chunk_size = st.sidebar.slider("청크 크기", 5, 100, 10, 10)
    selected_clouds = st.sidebar.multiselect(
        "테스트할 클라우드",
        options=['gcp', 'azure', 'aws'],
        default=['gcp', 'azure', 'aws']
    )

    # Mock 모드 설정
    mock_mode = st.sidebar.checkbox("Mock 모드 사용", value=True, help="실제 DB 연결 없이 시뮬레이션으로 테스트")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 결과 내보내기")

    if st.session_state.current_batch_stats:
        if st.sidebar.button("CSV로 내보내기"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = f"results/batch_stats_{timestamp}.csv"
            df_stats = pd.DataFrame(st.session_state.current_batch_stats)
            df_stats.to_csv(csv_path, index=False)
            st.sidebar.success(f"배치 통계가 {csv_path}에 저장되었습니다!")

        if st.sidebar.button("JSON으로 내보내기"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_path = f"results/batch_stats_{timestamp}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(st.session_state.current_batch_stats, f, indent=2, ensure_ascii=False, default=str)
            st.sidebar.success(f"배치 통계가 {json_path}에 저장되었습니다!")

    return chunk_size, selected_clouds, mock_mode