"""
Sidebar component for Streamlit app
"""
import streamlit as st
import pandas as pd
import json
from datetime import datetime


def render_sidebar():
    """Render sidebar with export options"""
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