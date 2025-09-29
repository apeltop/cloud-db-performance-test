import streamlit as st
import pandas as pd
import numpy as np

# 페이지 설정
st.set_page_config(
    page_title="Streamlit Demo App",
    page_icon="🚀",
    layout="wide"
)

# 메인 타이틀
st.title("🚀 Streamlit Demo Application")

st.markdown("---")

# 사이드바
st.sidebar.header("설정")
user_name = st.sidebar.text_input("이름을 입력하세요", "사용자")
number = st.sidebar.slider("숫자를 선택하세요", 1, 100, 50)

# 메인 콘텐츠
col1, col2 = st.columns(2)

with col1:
    st.header("📊 데이터 시각화")

    # 샘플 데이터 생성
    data = pd.DataFrame({
        'x': np.random.randn(100),
        'y': np.random.randn(100)
    })

    st.line_chart(data)

    if st.button("새 데이터 생성"):
        st.experimental_rerun()

with col2:
    st.header("🎛️ 인터랙티브 요소")

    st.write(f"안녕하세요, {user_name}님!")
    st.write(f"선택한 숫자: {number}")

    # 파일 업로드
    uploaded_file = st.file_uploader("CSV 파일을 업로드하세요", type=['csv'])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("업로드된 데이터:")
        st.dataframe(df.head())

# 푸터
st.markdown("---")
st.markdown("✨ Streamlit으로 만든 첫 번째 앱입니다!")