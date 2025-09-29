import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import asyncio
import json
import time
from datetime import datetime

# Import our custom modules
from config.config_loader import ConfigLoader
from services.db_manager import DatabaseManager
from services.data_processor import DataProcessor

# 페이지 설정
st.set_page_config(
    page_title="Cloud PostgreSQL Performance Tester",
    page_icon="🚀",
    layout="wide"
)

# Initialize session state
if 'test_results' not in st.session_state:
    st.session_state.test_results = None
if 'processing_stats' not in st.session_state:
    st.session_state.processing_stats = None
if 'data_processor' not in st.session_state:
    st.session_state.data_processor = None

# 메인 타이틀
st.title("🚀 Cloud PostgreSQL Performance Tester")
st.markdown("클라우드 3사(GCP, Azure, AWS) PostgreSQL 성능 비교 도구")

st.markdown("---")

# 사이드바 설정
st.sidebar.header("⚙️ 테스트 설정")

# Load configuration
if 'config_loader' not in st.session_state:
    st.session_state.config_loader = ConfigLoader()

config_loader = st.session_state.config_loader

# 테스트 설정
chunk_size = st.sidebar.slider("청크 크기", 5, 50, 10, 5)
selected_clouds = st.sidebar.multiselect(
    "테스트할 클라우드",
    options=['gcp', 'azure', 'aws'],
    default=['gcp', 'azure', 'aws']
)

# Mock 모드 설정
mock_mode = st.sidebar.checkbox("Mock 모드 사용", value=True, help="실제 DB 연결 없이 시뮬레이션으로 테스트")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📊 결과 내보내기")

if st.session_state.test_results is not None:
    if st.sidebar.button("CSV로 내보내기"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = f"results/test_results_{timestamp}.csv"
        st.session_state.data_processor.export_results_to_csv(csv_path)
        st.sidebar.success(f"결과가 {csv_path}에 저장되었습니다!")

    if st.sidebar.button("JSON으로 내보내기"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_path = f"results/summary_{timestamp}.json"
        st.session_state.data_processor.export_summary_to_json(json_path)
        st.sidebar.success(f"요약이 {json_path}에 저장되었습니다!")

# 메인 콘텐츠
tab1, tab2, tab3, tab4 = st.tabs(["📤 데이터 업로드", "📊 성능 비교", "📈 상세 분석", "⚙️ 설정"])

with tab1:
    st.header("📤 JSON 데이터 업로드")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 파일 업로드
        uploaded_file = st.file_uploader(
            "JSON 파일을 업로드하세요",
            type=['json'],
            help="테스트할 JSON 데이터 파일을 선택하세요"
        )

        if uploaded_file is not None:
            try:
                data = json.load(uploaded_file)
                if isinstance(data, dict):
                    data = [data]

                st.success(f"✅ {len(data)}개의 레코드가 로드되었습니다!")

                # 데이터 미리보기
                st.subheader("데이터 미리보기")
                df_preview = pd.DataFrame(data[:5])  # Show first 5 records
                st.dataframe(df_preview)

                # 테스트 실행 버튼
                if st.button("🚀 성능 테스트 실행"):
                    if selected_clouds:
                        with st.spinner("테스트 실행 중..."):
                            # Initialize database manager and data processor
                            db_manager = DatabaseManager(config_loader)
                            data_processor = DataProcessor(db_manager, chunk_size)

                            # Run the test
                            async def run_test():
                                return await data_processor.process_all_clouds(data, selected_clouds)

                            # Execute async function
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            processing_stats = loop.run_until_complete(run_test())
                            loop.close()

                            # Store results in session state
                            st.session_state.processing_stats = processing_stats
                            st.session_state.data_processor = data_processor
                            st.session_state.test_results = data_processor.get_performance_summary()

                        st.success("✅ 테스트가 완료되었습니다! '성능 비교' 탭에서 결과를 확인하세요.")
                        # st.rerun()  # 오래된 버전에서는 자동 리로드 안함
                    else:
                        st.error("테스트할 클라우드를 선택하세요!")

            except json.JSONDecodeError:
                st.error("❌ JSON 파일 형식이 올바르지 않습니다!")
            except Exception as e:
                st.error(f"❌ 파일 로드 중 오류가 발생했습니다: {str(e)}")

    with col2:
        st.subheader("예시 데이터")
        if st.button("📄 샘플 데이터 사용"):
            try:
                with open('data/sample_data.json', 'r', encoding='utf-8') as f:
                    sample_data = json.load(f)

                # 샘플 데이터를 세션 상태에 저장
                st.session_state.uploaded_data = sample_data
                st.success(f"✅ {len(sample_data)}개의 샘플 레코드가 로드되었습니다!")

                # 샘플 데이터 미리보기
                st.subheader("샘플 데이터 미리보기")
                df_sample = pd.DataFrame(sample_data[:3])
                st.dataframe(df_sample)

            except Exception as e:
                st.error(f"샘플 데이터 로드 실패: {str(e)}")

        # 세션 상태에 데이터가 있으면 테스트 실행 버튼 표시
        if 'uploaded_data' in st.session_state and st.session_state.uploaded_data:
            data = st.session_state.uploaded_data
            st.write(f"현재 로드된 데이터: {len(data)}개 레코드")

            # 테스트 실행 버튼
            if st.button("🚀 성능 테스트 실행", key="sample_test_button"):
                if selected_clouds:
                    with st.spinner("테스트 실행 중..."):
                        # Initialize database manager and data processor
                        db_manager = DatabaseManager(config_loader)
                        data_processor = DataProcessor(db_manager, chunk_size)

                        # Run the test
                        async def run_test():
                            return await data_processor.process_all_clouds(data, selected_clouds)

                        # Execute async function
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        processing_stats = loop.run_until_complete(run_test())
                        loop.close()

                        # Store results in session state
                        st.session_state.processing_stats = processing_stats
                        st.session_state.data_processor = data_processor
                        st.session_state.test_results = data_processor.get_performance_summary()

                    st.success("✅ 테스트가 완료되었습니다! '성능 비교' 탭에서 결과를 확인하세요.")
                    # st.experimental_rerun()  # 오래된 버전에서는 자동 리로드 안함
                else:
                    st.error("테스트할 클라우드를 선택하세요!")

with tab2:
    st.header("📊 성능 비교 결과")

    if st.session_state.test_results is not None:
        results = st.session_state.test_results
        stats = st.session_state.processing_stats

        # 전체 통계
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("총 레코드 수", stats.total_records)
        with col2:
            st.metric("총 청크 수", stats.total_chunks)
        with col3:
            st.metric("처리 시간", f"{stats.processing_time:.2f}초")
        with col4:
            success_rate = (stats.success_count / (stats.success_count + stats.failure_count)) * 100
            st.metric("성공률", f"{success_rate:.1f}%")

        st.markdown("---")

        # 클라우드별 성능 비교
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("평균 실행 시간 비교")

            cloud_names = []
            avg_times = []

            for cloud, data in results.items():
                if data['successful_operations'] > 0:
                    cloud_names.append(cloud.upper())
                    avg_times.append(data['average_execution_time'])

            if cloud_names:
                fig_bar = px.bar(
                    x=cloud_names,
                    y=avg_times,
                    labels={'x': 'Cloud Provider', 'y': 'Average Execution Time (seconds)'},
                    color=avg_times,
                    color_continuous_scale='Viridis'
                )
                fig_bar.update_layout(showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True)

        with col2:
            st.subheader("처리량 비교 (records/sec)")

            cloud_names = []
            throughput = []

            for cloud, data in results.items():
                if data['successful_operations'] > 0:
                    cloud_names.append(cloud.upper())
                    throughput.append(data['records_per_second'])

            if cloud_names:
                fig_throughput = px.bar(
                    x=cloud_names,
                    y=throughput,
                    labels={'x': 'Cloud Provider', 'y': 'Records per Second'},
                    color=throughput,
                    color_continuous_scale='Plasma'
                )
                fig_throughput.update_layout(showlegend=False)
                st.plotly_chart(fig_throughput, use_container_width=True)

        # 상세 통계 테이블
        st.subheader("상세 성능 통계")

        summary_data = []
        for cloud, data in results.items():
            summary_data.append({
                'Cloud': cloud.upper(),
                '총 작업': data['total_operations'],
                '성공': data['successful_operations'],
                '실패': data['failed_operations'],
                '성공률 (%)': f"{data['success_rate']:.1f}",
                '평균 시간 (초)': f"{data['average_execution_time']:.4f}",
                '최소 시간 (초)': f"{data['min_execution_time']:.4f}",
                '최대 시간 (초)': f"{data['max_execution_time']:.4f}",
                '처리량 (records/sec)': f"{data['records_per_second']:.2f}"
            })

        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary, use_container_width=True)

    else:
        st.info("테스트를 실행하면 결과가 여기에 표시됩니다.")

with tab3:
    st.header("📈 상세 분석")

    if st.session_state.data_processor is not None:
        processor = st.session_state.data_processor

        # 시간별 성능 분석
        st.subheader("청크별 실행 시간 분석")

        results_by_cloud = processor.get_results_by_cloud()

        fig_timeline = go.Figure()

        for cloud, cloud_results in results_by_cloud.items():
            successful_results = [r for r in cloud_results if r.success]
            if successful_results:
                chunk_ids = [r.chunk_id for r in successful_results]
                exec_times = [r.execution_time for r in successful_results]

                fig_timeline.add_trace(go.Scatter(
                    x=chunk_ids,
                    y=exec_times,
                    mode='lines+markers',
                    name=cloud.upper(),
                    line=dict(width=2),
                    marker=dict(size=6)
                ))

        fig_timeline.update_layout(
            xaxis_title="Chunk ID",
            yaxis_title="Execution Time (seconds)",
            hovermode='x unified'
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

        # 실행 시간 분포
        st.subheader("실행 시간 분포")

        col1, col2 = st.columns(2)

        with col1:
            # Box plot
            fig_box = go.Figure()

            for cloud, cloud_results in results_by_cloud.items():
                successful_results = [r for r in cloud_results if r.success]
                if successful_results:
                    exec_times = [r.execution_time for r in successful_results]
                    fig_box.add_trace(go.Box(
                        y=exec_times,
                        name=cloud.upper(),
                        boxpoints='all',
                        jitter=0.3,
                        pointpos=-1.8
                    ))

            fig_box.update_layout(
                yaxis_title="Execution Time (seconds)",
                showlegend=False
            )
            st.plotly_chart(fig_box, use_container_width=True)

        with col2:
            # Histogram
            selected_cloud_detail = st.selectbox(
                "분석할 클라우드 선택",
                options=list(results_by_cloud.keys()),
                format_func=lambda x: x.upper()
            )

            if selected_cloud_detail in results_by_cloud:
                cloud_results = results_by_cloud[selected_cloud_detail]
                successful_results = [r for r in cloud_results if r.success]

                if successful_results:
                    exec_times = [r.execution_time for r in successful_results]

                    fig_hist = px.histogram(
                        x=exec_times,
                        nbins=20,
                        labels={'x': 'Execution Time (seconds)', 'y': 'Count'},
                        title=f"{selected_cloud_detail.upper()} 실행 시간 히스토그램"
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)

    else:
        st.info("테스트를 실행하면 상세 분석이 여기에 표시됩니다.")

with tab4:
    st.header("⚙️ 설정")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("데이터베이스 연결 설정")

        # 현재 설정 표시
        db_config = config_loader.load_database_config()

        for cloud, config in db_config.get('clouds', {}).items():
            with st.expander(f"{cloud.upper()} 설정"):
                st.code(f"""
Host: {config.get('host', 'Not set')}
Port: {config.get('port', 5432)}
Database: {config.get('database', 'Not set')}
User: {config.get('user', 'Not set')}
SSL Mode: {config.get('ssl_mode', 'require')}
                """)

    with col2:
        st.subheader("스키마 설정")

        # 현재 스키마 표시
        schema_config = config_loader.load_schema()

        st.code(f"Table Name: {schema_config.get('table_name', 'test_data')}")

        with st.expander("필드 정의"):
            for field_name, field_config in schema_config.get('fields', {}).items():
                st.write(f"**{field_name}**: {field_config.get('type', 'Unknown')} - {field_config.get('description', 'No description')}")

# 푸터
st.markdown("---")
st.markdown("🚀 **Cloud PostgreSQL Performance Tester** - 클라우드 데이터베이스 성능 최적화를 위한 도구")