"""
Detailed analysis tab component
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_analysis_tab():
    """Render detailed analysis tab"""
    st.header("📈 상세 분석")

    # Check if migration is in progress or has batch stats
    if st.session_state.migration_in_progress or st.session_state.current_batch_stats:
        st.subheader("🚀 실시간 마이그레이션 성능 모니터링")

        # Show migration progress if in progress
        if st.session_state.migration_in_progress:
            progress = st.session_state.migration_progress

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("현재 파일", progress.get('current_file', 'N/A'))
            with col2:
                files_progress = f"{progress.get('files_completed', 0)}/{progress.get('total_files', 0)}"
                st.metric("파일 진행률", files_progress)
            with col3:
                current_batch = progress.get('current_batch', 0)
                st.metric("현재 배치", current_batch)

            # Auto-refresh control
            if st.button("🔄 새로고침", key="refresh_migration"):
                st.rerun()

        # Display real-time batch statistics
        if st.session_state.current_batch_stats:
            batch_stats = st.session_state.current_batch_stats

            if batch_stats:
                st.markdown("---")
                st.subheader("📊 실시간 배치 성능")

                # Create DataFrame from current batch stats
                df_batch_stats = pd.DataFrame(batch_stats)

                # Recent performance metrics
                if len(batch_stats) > 0:
                    latest_stats = batch_stats[-1]
                    recent_stats = batch_stats[-min(5, len(batch_stats)):]
                    avg_recent_rps = sum(s['records_per_second'] for s in recent_stats) / len(recent_stats)

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("총 배치", len(batch_stats))
                    with col2:
                        st.metric("최근 처리량", f"{latest_stats['records_per_second']:.1f} rec/s")
                    with col3:
                        st.metric("평균 처리량 (최근 5배치)", f"{avg_recent_rps:.1f} rec/s")
                    with col4:
                        st.metric("최근 배치 시간", f"{latest_stats['total_duration_seconds']:.3f}초")

                # Real-time charts
                if not df_batch_stats.empty:
                    # Processing time trend
                    fig_realtime = px.line(
                        df_batch_stats,
                        x='batch_number',
                        y='total_duration_seconds',
                        color='table_name',
                        title='실시간 배치별 처리 시간 추이',
                        labels={
                            'batch_number': '배치 번호',
                            'total_duration_seconds': '처리 시간 (초)',
                            'table_name': '테이블'
                        }
                    )
                    fig_realtime.update_layout(height=400)
                    st.plotly_chart(fig_realtime, use_container_width=True)

                    # Throughput trend
                    fig_throughput_realtime = px.line(
                        df_batch_stats,
                        x='batch_number',
                        y='records_per_second',
                        color='table_name',
                        title='실시간 배치별 처리량 추이',
                        labels={
                            'batch_number': '배치 번호',
                            'records_per_second': '처리량 (records/sec)',
                            'table_name': '테이블'
                        }
                    )
                    fig_throughput_realtime.update_layout(height=400)
                    st.plotly_chart(fig_throughput_realtime, use_container_width=True)

                    # Performance degradation warning
                    if len(batch_stats) >= 3:
                        recent_times = [s['total_duration_seconds'] for s in batch_stats[-3:]]
                        if all(recent_times[i] < recent_times[i+1] for i in range(len(recent_times)-1)):
                            st.warning("⚠️ 성능 저하 감지: 최근 3개 배치의 처리 시간이 계속 증가하고 있습니다.")

        st.markdown("---")

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

    elif not st.session_state.migration_in_progress and not st.session_state.current_batch_stats:
        st.info("테스트를 실행하거나 데이터 마이그레이션을 시작하면 상세 분석이 여기에 표시됩니다.")