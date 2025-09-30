"""
Performance comparison tab component
"""
import streamlit as st
import pandas as pd
import plotly.express as px


def render_performance_tab():
    """Render performance comparison results tab"""
    st.header("📊 성능 비교 결과")

    # Check for both migration batch stats and sample test data
    if st.session_state.current_batch_stats or st.session_state.data_processor is not None:

        # Display migration performance if available
        if st.session_state.current_batch_stats:
            batch_stats = st.session_state.current_batch_stats

            st.subheader("🚀 마이그레이션 성능 통계")

            if batch_stats:
                # Calculate overall statistics
                total_batches = len(batch_stats)
                total_records = sum(stat['records_count'] for stat in batch_stats)
                total_duration = sum(stat['total_duration_seconds'] for stat in batch_stats)
                avg_records_per_second = total_records / total_duration if total_duration > 0 else 0

                # Performance metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("총 배치 수", total_batches)
                with col2:
                    st.metric("총 레코드 수", f"{total_records:,}")
                with col3:
                    st.metric("총 처리 시간", f"{total_duration:.2f}초")
                with col4:
                    st.metric("평균 처리량", f"{avg_records_per_second:.1f} rec/s")

                st.markdown("---")

                # Table-wise performance
                df_batch_stats = pd.DataFrame(batch_stats)

                if not df_batch_stats.empty:
                    # Group by table for comparison
                    table_summary = df_batch_stats.groupby('table_name').agg({
                        'records_count': 'sum',
                        'total_duration_seconds': 'sum',
                        'records_per_second': 'mean',
                        'batch_number': 'count'
                    }).reset_index()

                    table_summary.columns = ['테이블', '총 레코드', '총 시간(초)', '평균 처리량(rec/s)', '배치 수']

                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("테이블별 성능 비교")
                        st.dataframe(table_summary)

                    with col2:
                        st.subheader("테이블별 처리량 비교")
                        if len(table_summary) > 0:
                            fig_bar = px.bar(
                                table_summary,
                                x='테이블',
                                y='평균 처리량(rec/s)',
                                title="테이블별 평균 처리량",
                                color='평균 처리량(rec/s)',
                                color_continuous_scale='Viridis'
                            )
                            fig_bar.update_layout(showlegend=False, xaxis_tickangle=-45)
                            st.plotly_chart(fig_bar, use_container_width=True)

        # Display sample test performance if available
        elif st.session_state.data_processor is not None and st.session_state.processing_stats is not None:
            stats = st.session_state.processing_stats
            processor = st.session_state.data_processor

            st.subheader("🌟 샘플 데이터 테스트 성능")

            # 전체 통계
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("총 레코드 수", stats.total_records)
            with col2:
                st.metric("총 청크 수", stats.total_chunks)
            with col3:
                st.metric("처리 시간", f"{stats.processing_time:.2f}초")
            with col4:
                success_rate = (stats.success_count / (stats.success_count + stats.failure_count)) * 100 if (stats.success_count + stats.failure_count) > 0 else 0
                st.metric("성공률", f"{success_rate:.1f}%")

            st.markdown("---")

            # Cloud performance comparison
            results = processor.get_performance_summary()
            if results:
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
                st.dataframe(df_summary)
    else:
        st.info("데이터 마이그레이션을 실행하거나 샘플 데이터 테스트를 실행하면 결과가 여기에 표시됩니다.")