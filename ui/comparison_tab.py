"""
Comparison tab for comparing multiple test runs
Provides visualization and analysis of performance across different configurations
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from services.migration.test_run_manager import TestRunManager
from utils.comparison_utils import (
    calculate_performance_metrics,
    analyze_performance_comparison,
    prepare_batch_comparison_data,
    get_test_summary
)


def render_comparison_tab():
    """Render test comparison tab"""
    st.header("📊 테스트 결과 비교")

    # Initialize test run manager
    test_manager = TestRunManager()

    # Get all test runs
    all_test_runs = test_manager.get_all_test_runs()

    if not all_test_runs:
        st.info("아직 저장된 테스트가 없습니다. CLI를 통해 마이그레이션을 실행하세요.")
        st.code("python migrate_cli.py --batch-size 1000 --connections 1")
        return

    # Filter options
    st.subheader("🔍 필터")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Get unique providers
        providers = list(set([tr.get('cloud_provider', 'Unknown') for tr in all_test_runs]))
        selected_provider = st.selectbox("클라우드 프로바이더", ["전체"] + providers)

    with col2:
        # Get unique batch sizes
        batch_sizes = list(set([tr.get('batch_size', 0) for tr in all_test_runs]))
        selected_batch = st.selectbox("배치 크기", ["전체"] + sorted(batch_sizes))

    with col3:
        # Get unique connection counts
        connections = list(set([tr.get('num_connections', 0) for tr in all_test_runs]))
        selected_conn = st.selectbox("커넥션 수", ["전체"] + sorted(connections))

    with col4:
        # Status filter
        selected_status = st.selectbox("상태", ["전체", "completed", "running", "error"])

    # Apply filters
    filtered_runs = all_test_runs
    if selected_provider != "전체":
        filtered_runs = [tr for tr in filtered_runs if tr.get('cloud_provider') == selected_provider]
    if selected_batch != "전체":
        filtered_runs = [tr for tr in filtered_runs if tr.get('batch_size') == selected_batch]
    if selected_conn != "전체":
        filtered_runs = [tr for tr in filtered_runs if tr.get('num_connections') == selected_conn]
    if selected_status != "전체":
        filtered_runs = [tr for tr in filtered_runs if tr.get('status') == selected_status]

    st.markdown("---")

    # Display test runs table
    st.subheader("📋 저장된 테스트 목록")

    if not filtered_runs:
        st.warning("필터 조건에 맞는 테스트가 없습니다.")
        return

    # Prepare table data
    table_data = []
    for tr in filtered_runs:
        table_data.append({
            '선택': False,
            '테스트 ID': tr['test_id'],
            '시간': tr['timestamp'][:19] if tr.get('timestamp') else 'N/A',
            'Provider': tr.get('cloud_provider', 'Unknown'),
            'Instance': tr.get('instance_type', 'Unknown'),
            'Batch': tr.get('batch_size', 0),
            'Conn': tr.get('num_connections', 0),
            'RPS': f"{tr.get('average_records_per_second', 0):.0f}" if tr.get('average_records_per_second') else 'N/A',
            '상태': '✅' if tr.get('status') == 'completed' else ('⚠️' if tr.get('status') == 'running' else '❌')
        })

    df_tests = pd.DataFrame(table_data)

    # Display dataframe with selection
    st.dataframe(df_tests, use_container_width=True, hide_index=True)

    # Multi-select for comparison
    st.markdown("---")
    st.subheader("🎯 비교할 테스트 선택")

    # Create selection options with readable labels
    test_options = {}
    for tr in filtered_runs:
        if tr.get('status') == 'completed':
            label = f"{tr['timestamp'][:19]} - {get_test_summary(tr)} - {tr.get('average_records_per_second', 0):.0f} rec/s"
            test_options[label] = tr['test_id']

    if not test_options:
        st.warning("비교할 수 있는 완료된 테스트가 없습니다.")
        return

    selected_labels = st.multiselect(
        "비교할 테스트를 선택하세요 (2개 이상)",
        options=list(test_options.keys()),
        default=list(test_options.keys())[:min(2, len(test_options))]
    )

    selected_test_ids = [test_options[label] for label in selected_labels]

    if len(selected_test_ids) < 2:
        st.info("비교 분석을 위해 최소 2개의 테스트를 선택하세요.")
        return

    # Get selected test runs
    selected_tests = [tr for tr in filtered_runs if tr['test_id'] in selected_test_ids]

    # Comparison button
    if st.button("📊 선택한 테스트 비교 분석", type="primary"):
        render_comparison_analysis(selected_tests, test_manager)


def render_comparison_analysis(selected_tests: list, test_manager: TestRunManager):
    """Render comparison analysis and charts"""
    st.markdown("---")
    st.header("📈 성능 비교 분석")

    # Performance analysis
    analysis = analyze_performance_comparison(selected_tests)

    if analysis['status'] == 'no_data':
        st.warning(analysis['message'])
        return

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("비교 테스트 수", analysis['total_tests'])
    with col2:
        st.metric("평균 처리량", f"{analysis['averages']['throughput']:.1f} rec/s")
    with col3:
        st.metric("평균 처리 시간", f"{analysis['averages']['duration']:.1f}초")

    # Best/Worst performers
    st.markdown("### 🏆 성능 순위")
    col1, col2 = st.columns(2)

    with col1:
        st.success("**최고 처리량**")
        best = analysis['best_throughput']
        st.write(f"**Provider:** {best['provider']}")
        st.write(f"**Instance:** {best['instance']}")
        st.write(f"**처리량:** {best['value']:.1f} rec/s")

    with col2:
        st.success("**최단 처리 시간**")
        fastest = analysis['fastest_duration']
        st.write(f"**Provider:** {fastest['provider']}")
        st.write(f"**Instance:** {fastest['instance']}")
        st.write(f"**시간:** {fastest['value']:.1f}초")

    st.markdown("---")

    # Comparison charts
    st.markdown("### 📊 비교 차트")

    # Prepare data for charts
    df_metrics = calculate_performance_metrics(selected_tests)

    # Chart 1: Total Duration Comparison
    st.markdown("#### ⏱️ 총 처리 시간 비교")
    fig_duration = px.bar(
        df_metrics,
        x='test_id',
        y='total_duration_seconds',
        color='cloud_provider',
        title='총 처리 시간 비교',
        labels={
            'test_id': '테스트 ID',
            'total_duration_seconds': '처리 시간 (초)',
            'cloud_provider': 'Provider'
        },
        text='total_duration_seconds'
    )
    fig_duration.update_traces(texttemplate='%{text:.1f}s', textposition='outside')
    fig_duration.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig_duration, use_container_width=True)

    # Chart 2: Throughput Comparison
    st.markdown("#### 🚀 평균 처리량 비교")
    fig_throughput = px.bar(
        df_metrics,
        x='test_id',
        y='average_records_per_second',
        color='cloud_provider',
        title='평균 처리량 비교',
        labels={
            'test_id': '테스트 ID',
            'average_records_per_second': '처리량 (records/sec)',
            'cloud_provider': 'Provider'
        },
        text='average_records_per_second'
    )
    fig_throughput.update_traces(texttemplate='%{text:.0f}', textposition='outside')
    fig_throughput.update_layout(height=400, xaxis_tickangle=-45)
    st.plotly_chart(fig_throughput, use_container_width=True)

    # Chart 3: Batch-level performance overlay
    st.markdown("#### 📈 배치별 처리 시간 추이 (오버레이)")
    batch_df = prepare_batch_comparison_data(selected_tests, test_manager.base_output_dir)

    if not batch_df.empty:
        fig_batch = px.line(
            batch_df,
            x='batch_number',
            y='total_duration_seconds',
            color='test_label',
            title='배치별 처리 시간 추이',
            labels={
                'batch_number': '배치 번호',
                'total_duration_seconds': '처리 시간 (초)',
                'test_label': '테스트'
            },
            markers=True
        )
        fig_batch.update_layout(height=500)
        st.plotly_chart(fig_batch, use_container_width=True)

        # Chart 4: Batch-level throughput overlay
        st.markdown("#### 📈 배치별 처리량 추이 (오버레이)")
        fig_batch_rps = px.line(
            batch_df,
            x='batch_number',
            y='records_per_second',
            color='test_label',
            title='배치별 처리량 추이',
            labels={
                'batch_number': '배치 번호',
                'records_per_second': '처리량 (records/sec)',
                'test_label': '테스트'
            },
            markers=True
        )
        fig_batch_rps.update_layout(height=500)
        st.plotly_chart(fig_batch_rps, use_container_width=True)

        # Chart 5: Time breakdown comparison (stacked bar)
        st.markdown("#### ⏱️ 시간 구성 비교 (평균)")
        time_breakdown = batch_df.groupby('test_label').agg({
            'data_preparation_time': 'mean',
            'query_execution_time': 'mean',
            'commit_time': 'mean',
            'overhead_time': 'mean'
        }).reset_index()

        fig_breakdown = go.Figure()
        fig_breakdown.add_trace(go.Bar(
            name='Data Preparation',
            x=time_breakdown['test_label'],
            y=time_breakdown['data_preparation_time'],
            text=time_breakdown['data_preparation_time'].round(3),
            textposition='inside'
        ))
        fig_breakdown.add_trace(go.Bar(
            name='Query Execution',
            x=time_breakdown['test_label'],
            y=time_breakdown['query_execution_time'],
            text=time_breakdown['query_execution_time'].round(3),
            textposition='inside'
        ))
        fig_breakdown.add_trace(go.Bar(
            name='Commit',
            x=time_breakdown['test_label'],
            y=time_breakdown['commit_time'],
            text=time_breakdown['commit_time'].round(3),
            textposition='inside'
        ))
        fig_breakdown.add_trace(go.Bar(
            name='Overhead',
            x=time_breakdown['test_label'],
            y=time_breakdown['overhead_time'],
            text=time_breakdown['overhead_time'].round(3),
            textposition='inside'
        ))

        fig_breakdown.update_layout(
            barmode='stack',
            title='배치 처리 시간 구성 비교 (평균)',
            xaxis_title='테스트',
            yaxis_title='시간 (초)',
            height=500,
            xaxis_tickangle=-45
        )
        st.plotly_chart(fig_breakdown, use_container_width=True)

    # Configuration comparison
    st.markdown("---")
    st.markdown("### ⚙️ 설정별 성능 비교")

    config_comparison = df_metrics[['batch_size', 'num_connections', 'average_records_per_second', 'total_duration_seconds']].copy()
    config_comparison = config_comparison.groupby(['batch_size', 'num_connections']).agg({
        'average_records_per_second': 'mean',
        'total_duration_seconds': 'mean'
    }).reset_index()

    col1, col2 = st.columns(2)

    with col1:
        # Scatter plot: batch size vs throughput
        fig_scatter = px.scatter(
            df_metrics,
            x='batch_size',
            y='average_records_per_second',
            size='num_connections',
            color='cloud_provider',
            title='배치 크기 vs 처리량',
            labels={
                'batch_size': '배치 크기',
                'average_records_per_second': '처리량 (rec/s)',
                'num_connections': '커넥션 수',
                'cloud_provider': 'Provider'
            },
            hover_data=['instance_type']
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, use_container_width=True)

    with col2:
        # Scatter plot: connections vs throughput
        fig_scatter2 = px.scatter(
            df_metrics,
            x='num_connections',
            y='average_records_per_second',
            size='batch_size',
            color='cloud_provider',
            title='커넥션 수 vs 처리량',
            labels={
                'num_connections': '커넥션 수',
                'average_records_per_second': '처리량 (rec/s)',
                'batch_size': '배치 크기',
                'cloud_provider': 'Provider'
            },
            hover_data=['instance_type']
        )
        fig_scatter2.update_layout(height=400)
        st.plotly_chart(fig_scatter2, use_container_width=True)
