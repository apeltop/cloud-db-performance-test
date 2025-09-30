"""
Upload tab component for data upload functionality
"""
import streamlit as st
import pandas as pd
import json
import asyncio
from services.db_manager import DatabaseManager
from services.data_processor import DataProcessor


def run_performance_test(data, selected_clouds, chunk_size, config_loader):
    """Run performance test on uploaded data"""
    # Create progress container for real-time updates
    progress_container = st.empty()
    status_container = st.empty()

    with progress_container.container():
        st.info("🚀 테스트 실행 중...")
        progress_bar = st.progress(0.0)

    with status_container.container():
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

        # Create batch statistics from test results for consistency
        batch_stats = []
        for i, result in enumerate(data_processor.results):
            if result.success:
                batch_stats.append({
                    "batch_number": i + 1,
                    "table_name": f"sample_test_{result.cloud}",
                    "records_count": result.records_count,
                    "start_time": result.timestamp,
                    "end_time": result.timestamp + result.execution_time,
                    "total_duration_seconds": result.execution_time,
                    "execution_duration_seconds": result.execution_time,
                    "records_per_second": result.records_count / result.execution_time if result.execution_time > 0 else 0,
                    "cumulative_records": sum(r.records_count for r in data_processor.results[:i+1] if r.success)
                })
        st.session_state.current_batch_stats = batch_stats

    progress_bar.progress(1.0)
    st.success("✅ 테스트가 완료되었습니다! '성능 비교' 탭에서 결과를 확인하세요.")
    st.experimental_rerun()  # Enable auto reload for real-time updates


def render_upload_tab(chunk_size, selected_clouds, config_loader):
    """Render data upload tab"""
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
                        run_performance_test(data, selected_clouds, chunk_size, config_loader)
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
                    run_performance_test(data, selected_clouds, chunk_size, config_loader)
                else:
                    st.error("테스트할 클라우드를 선택하세요!")