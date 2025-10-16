"""
Detailed analysis tab component
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
import os
from datetime import datetime
from pathlib import Path
from services.migration.test_run_manager import TestRunManager


def load_saved_migration_stats(test_output_dir: Path = None):
    """Load saved migration statistics from file"""
    if test_output_dir:
        stats_file = test_output_dir / "migration_stats.json"
    else:
        stats_file = Path("migration_outputs/migration_stats.json")

    if stats_file.exists():
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('batches', []), str(stats_file)
        except Exception as e:
            st.error(f"통계 파일 로드 중 오류 발생: {e}")
            return [], None
    return [], None


def load_test_results(test_output_dir: Path = None):
    """Load test results from file"""
    if test_output_dir:
        results_file = test_output_dir / "migration_results.json"
    else:
        results_file = Path("migration_outputs/migration_results.json")

    if results_file.exists():
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"결과 파일 로드 중 오류 발생: {e}")
            return None
    return None


def render_batch_statistics(batch_stats, data_source="real-time", file_path=None):
    """Render batch statistics section with filtering and charts"""
    if not batch_stats:
        return

    # Create DataFrame from batch stats
    df_batch_stats = pd.DataFrame(batch_stats)

    # Data source indicator
    if data_source == "saved" and file_path:
        mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
        st.info(f"📁 저장된 데이터 (마지막 업데이트: {mod_time.strftime('%Y-%m-%d %H:%M:%S')})")
    elif data_source == "real-time":
        st.success("🔴 실시간 데이터")

    # Get unique table names for filtering
    unique_tables = df_batch_stats['table_name'].unique().tolist()

    # File/Table selection filter
    filter_option = st.selectbox(
        "📁 테이블 선택",
        options=["전체"] + unique_tables,
        key=f"table_filter_{data_source}"
    )

    # Filter data based on selection
    if filter_option == "전체":
        filtered_stats = batch_stats
        filtered_df = df_batch_stats
    else:
        filtered_stats = [s for s in batch_stats if s['table_name'] == filter_option]
        filtered_df = df_batch_stats[df_batch_stats['table_name'] == filter_option].copy()
        # Reset batch numbers for filtered view
        filtered_df['batch_number'] = range(1, len(filtered_df) + 1)

    # Performance metrics
    if len(filtered_stats) > 0:
        latest_stats = filtered_stats[-1]
        recent_stats = filtered_stats[-min(5, len(filtered_stats)):]
        avg_recent_rps = sum(s['records_per_second'] for s in recent_stats) / len(recent_stats)
        avg_duration = sum(s['total_duration_seconds'] for s in filtered_stats) / len(filtered_stats)
        total_records = sum(s['records_count'] for s in filtered_stats)

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("총 배치", len(filtered_stats))
        with col2:
            st.metric("총 레코드", f"{total_records:,}")
        with col3:
            st.metric("최근 처리량", f"{latest_stats['records_per_second']:.1f} rec/s")
        with col4:
            st.metric("평균 처리량", f"{avg_recent_rps:.1f} rec/s")
        with col5:
            st.metric("평균 배치 시간", f"{avg_duration:.3f}초")

    # Charts
    if not filtered_df.empty:
        if filter_option == "전체":
            # Show separate charts for each table
            st.markdown("### 배치별 처리 시간 추이")
            cols = st.columns(2)
            for idx, table in enumerate(unique_tables):
                table_df = filtered_df[filtered_df['table_name'] == table].copy()
                table_df['batch_number'] = range(1, len(table_df) + 1)

                with cols[idx % 2]:
                    fig = px.line(
                        table_df,
                        x='batch_number',
                        y='total_duration_seconds',
                        title=f'{table}',
                        labels={
                            'batch_number': '배치 번호',
                            'total_duration_seconds': '처리 시간 (초)'
                        },
                        markers=True
                    )
                    fig.update_layout(height=300, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

            st.markdown("### 배치별 처리량 추이")
            cols = st.columns(2)
            for idx, table in enumerate(unique_tables):
                table_df = filtered_df[filtered_df['table_name'] == table].copy()
                table_df['batch_number'] = range(1, len(table_df) + 1)

                with cols[idx % 2]:
                    fig = px.line(
                        table_df,
                        x='batch_number',
                        y='records_per_second',
                        title=f'{table}',
                        labels={
                            'batch_number': '배치 번호',
                            'records_per_second': '처리량 (records/sec)'
                        },
                        markers=True
                    )
                    fig.update_layout(height=300, showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)

            # Cumulative records chart
            if 'cumulative_records' in filtered_df.columns:
                st.markdown("### 누적 레코드 수")
                cols = st.columns(2)
                for idx, table in enumerate(unique_tables):
                    table_df = filtered_df[filtered_df['table_name'] == table].copy()
                    table_df['batch_number'] = range(1, len(table_df) + 1)

                    with cols[idx % 2]:
                        fig = px.area(
                            table_df,
                            x='batch_number',
                            y='cumulative_records',
                            title=f'{table}',
                            labels={
                                'batch_number': '배치 번호',
                                'cumulative_records': '누적 레코드 수'
                            }
                        )
                        fig.update_layout(height=300, showlegend=False)
                        st.plotly_chart(fig, use_container_width=True)
        else:
            # Single table selected - show single charts
            fig_realtime = px.line(
                filtered_df,
                x='batch_number',
                y='total_duration_seconds',
                title=f'배치별 처리 시간 추이 - {filter_option}',
                labels={
                    'batch_number': '배치 번호',
                    'total_duration_seconds': '처리 시간 (초)'
                },
                markers=True
            )
            fig_realtime.update_layout(height=400)
            st.plotly_chart(fig_realtime, use_container_width=True)

            # Throughput trend
            fig_throughput_realtime = px.line(
                filtered_df,
                x='batch_number',
                y='records_per_second',
                title=f'배치별 처리량 추이 - {filter_option}',
                labels={
                    'batch_number': '배치 번호',
                    'records_per_second': '처리량 (records/sec)'
                },
                markers=True
            )
            fig_throughput_realtime.update_layout(height=400)
            st.plotly_chart(fig_throughput_realtime, use_container_width=True)

            # Cumulative records chart
            if 'cumulative_records' in filtered_df.columns:
                fig_cumulative = px.area(
                    filtered_df,
                    x='batch_number',
                    y='cumulative_records',
                    title=f'누적 레코드 수 - {filter_option}',
                    labels={
                        'batch_number': '배치 번호',
                        'cumulative_records': '누적 레코드 수'
                    }
                )
                fig_cumulative.update_layout(height=400)
                st.plotly_chart(fig_cumulative, use_container_width=True)

        # Performance degradation warning (for filtered data)
        if len(filtered_stats) >= 3:
            recent_times = [s['total_duration_seconds'] for s in filtered_stats[-3:]]
            if all(recent_times[i] < recent_times[i+1] for i in range(len(recent_times)-1)):
                warning_msg = "⚠️ 성능 저하 감지: 최근 3개 배치의 처리 시간이 계속 증가하고 있습니다."
                if filter_option != "전체":
                    warning_msg += f" (테이블: {filter_option})"
                st.warning(warning_msg)


def render_analysis_tab():
    """Render detailed analysis tab"""
    st.header("📈 상세 분석")

    # Initialize test run manager
    test_manager = TestRunManager()

    # Get all completed test runs
    all_test_runs = test_manager.get_test_runs_by_status("completed")

    if not all_test_runs:
        st.info("완료된 테스트가 없습니다. CLI를 통해 마이그레이션을 먼저 실행하세요.")
        st.code("python migrate_cli.py --batch-size 1000 --connections 1")
        return

    # Test selection dropdown
    st.subheader("🎯 분석할 테스트 선택")

    test_options = {}
    for tr in all_test_runs:
        label = f"{tr['timestamp'][:19]} - {tr['cloud_provider']} {tr['instance_type']} (batch:{tr['batch_size']}, conn:{tr['num_connections']}) - {tr.get('average_records_per_second', 0):.0f} rec/s"
        test_options[label] = tr['test_id']

    selected_label = st.selectbox(
        "테스트를 선택하세요",
        options=list(test_options.keys()),
        index=0
    )

    selected_test_id = test_options[selected_label]
    selected_test = test_manager.get_test_run(selected_test_id)
    test_output_dir = test_manager.get_test_output_dir(selected_test_id)

    if not test_output_dir:
        st.error("테스트 출력 디렉토리를 찾을 수 없습니다.")
        return

    st.markdown("---")

    # Load and display file results from migration
    st.subheader("📁 파일별 마이그레이션 결과")

    results = load_test_results(test_output_dir)
    if results:
        if results.get('status') == 'completed':
            # Summary metrics
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("총 파일", results.get('total_files', 0))
            with col_b:
                st.metric("✅ 성공", results.get('successful', 0))
            with col_c:
                st.metric("❌ 실패", results.get('failed', 0))

            # File results table
            file_results = results.get('file_results', [])
            if file_results:
                df_file_results = pd.DataFrame(file_results)
                # Select and rename columns
                display_cols = ['filename', 'table', 'status', 'records_inserted']
                df_display = df_file_results[display_cols].copy()
                df_display.columns = ['파일명', '테이블', '상태', '삽입된 레코드']
                df_display['상태'] = df_display['상태'].map({
                    'success': '✅ 성공',
                    'error': '❌ 실패',
                    'skipped': '⚠️ 건너뜀'
                })
                st.dataframe(df_display, use_container_width=True)
            else:
                st.info("파일별 결과 데이터가 없습니다.")
        else:
            st.info("완료된 마이그레이션 결과가 없습니다.")
    else:
        st.info("마이그레이션 결과 파일이 없습니다.")

    st.markdown("---")

    # Load and display batch statistics for selected test
    st.subheader("📊 배치 성능 통계")

    saved_stats, stats_file = load_saved_migration_stats(test_output_dir)

    if saved_stats:
        render_batch_statistics(saved_stats, data_source="saved", file_path=stats_file)
    else:
        st.info("선택한 테스트의 배치 통계를 찾을 수 없습니다.")