import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from collections import defaultdict

# 페이지 설정
st.set_page_config(
    page_title="Claude Code 사용량 대시보드",
    page_icon="🤖",
    layout="wide"
)

# 제목
st.title("🤖 Claude Code 사용량 대시보드")
st.markdown("---")


def parse_jsonl_file(file_path):
    """JSONL 파일 파싱"""
    messages = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    messages.append(json.loads(line))
                except json.JSONDecodeError as e:
                    st.warning(f"JSON 파싱 오류 ({file_path.name}): {str(e)}")
                    continue
    return messages


def get_project_name_from_folder(folder_name):
    """폴더명에서 프로젝트 이름 추출"""
    # -Users-apeltop-project-personal-jodal-insert-test -> jodal-insert-test
    parts = folder_name.split('-')
    if len(parts) > 5:
        return '-'.join(parts[-3:])  # 마지막 3개 부분만 사용
    return folder_name


def load_all_sessions_from_projects(projects_folder):
    """프로젝트 폴더에서 모든 세션 로드"""
    sessions = []
    projects_path = Path(projects_folder)

    if not projects_path.exists():
        return sessions, []

    # 프로젝트별 폴더 찾기
    project_folders = [f for f in projects_path.iterdir() if f.is_dir()]

    project_info = []

    for project_folder in project_folders:
        project_name = get_project_name_from_folder(project_folder.name)
        jsonl_files = list(project_folder.glob("*.jsonl"))

        project_sessions = []
        for jsonl_file in jsonl_files:
            try:
                messages = parse_jsonl_file(jsonl_file)
                if messages:  # 메시지가 있는 경우만 추가
                    project_sessions.append({
                        'session_id': jsonl_file.stem,
                        'project_name': project_name,
                        'project_folder': project_folder.name,
                        'messages': messages
                    })
            except Exception as e:
                st.warning(f"파일 읽기 오류 ({jsonl_file.name}): {str(e)}")

        if project_sessions:
            sessions.extend(project_sessions)
            project_info.append({
                'project': project_name,
                'folder': project_folder.name,
                'sessions': len(project_sessions),
                'files': len(jsonl_files)
            })

    return sessions, project_info


def calculate_cost(usage):
    """비용 계산 (Claude Sonnet 4 기준)"""
    input_tokens = usage.get('input_tokens', 0)
    output_tokens = usage.get('output_tokens', 0)
    cache_read_tokens = usage.get('cache_read_input_tokens', 0)
    cache_creation_tokens = usage.get('cache_creation_input_tokens', 0)

    input_cost = (input_tokens / 1_000_000) * 3
    output_cost = (output_tokens / 1_000_000) * 15
    cache_read_cost = (cache_read_tokens / 1_000_000) * 0.3
    cache_creation_cost = (cache_creation_tokens / 1_000_000) * 3.75

    return input_cost + output_cost + cache_read_cost + cache_creation_cost


def analyze_sessions(sessions):
    """세션 데이터 분석"""
    all_messages = []
    for session in sessions:
        all_messages.extend(session['messages'])

    # 통계 초기화
    stats = {
        'total_sessions': len(sessions),
        'total_messages': len(all_messages),
        'total_input_tokens': 0,
        'total_output_tokens': 0,
        'total_cache_read_tokens': 0,
        'total_cache_creation_tokens': 0,
        'total_cost': 0,
    }

    # 일별, 모델별, 브랜치별, 프로젝트별 데이터
    daily_data = defaultdict(lambda: {'tokens': 0, 'cost': 0, 'messages': 0})
    model_usage = defaultdict(int)
    branch_usage = defaultdict(int)
    tool_usage = defaultdict(int)
    project_usage = defaultdict(lambda: {'messages': 0, 'tokens': 0, 'cost': 0})

    # 프로젝트별로 메시지 매핑
    session_project_map = {session['session_id']: session['project_name'] for session in sessions}

    for msg in all_messages:
        # 프로젝트 정보 추가
        session_id = msg.get('sessionId', '')
        project_name = session_project_map.get(session_id, 'unknown')

        # 토큰 및 비용 계산
        if msg.get('message', {}).get('usage'):
            usage = msg['message']['usage']
            stats['total_input_tokens'] += usage.get('input_tokens', 0)
            stats['total_output_tokens'] += usage.get('output_tokens', 0)
            stats['total_cache_read_tokens'] += usage.get('cache_read_input_tokens', 0)
            stats['total_cache_creation_tokens'] += usage.get('cache_creation_input_tokens', 0)

            cost = calculate_cost(usage)
            stats['total_cost'] += cost

            tokens = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)

            # 모델별 집계
            model = msg['message'].get('model', 'unknown')
            model_usage[model] += 1

            # 일별 집계
            date = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00')).date()
            daily_data[date]['tokens'] += tokens
            daily_data[date]['cost'] += cost
            daily_data[date]['messages'] += 1

            # 프로젝트별 집계
            project_usage[project_name]['messages'] += 1
            project_usage[project_name]['tokens'] += tokens
            project_usage[project_name]['cost'] += cost

        # 브랜치별 집계
        if msg.get('gitBranch'):
            branch_usage[msg['gitBranch']] += 1

        # 도구 사용 집계
        if msg.get('message', {}).get('content'):
            content = msg['message']['content']
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'tool_use':
                        tool_name = item.get('name', 'unknown')
                        tool_usage[tool_name] += 1

    # 평균 계산
    if stats['total_messages'] > 0:
        stats['avg_tokens_per_message'] = (stats['total_input_tokens'] + stats['total_output_tokens']) / stats[
            'total_messages']
    else:
        stats['avg_tokens_per_message'] = 0

    # 데이터프레임 생성
    daily_df = pd.DataFrame([
        {'date': date, **data}
        for date, data in sorted(daily_data.items())
    ])

    model_df = pd.DataFrame([
        {'model': model, 'count': count}
        for model, count in model_usage.items()
    ]).sort_values('count', ascending=False)

    branch_df = pd.DataFrame([
        {'branch': branch, 'count': count}
        for branch, count in branch_usage.items()
    ]).sort_values('count', ascending=False).head(10)

    tool_df = pd.DataFrame([
        {'tool': tool, 'count': count}
        for tool, count in tool_usage.items()
    ]).sort_values('count', ascending=False).head(10)

    project_df = pd.DataFrame([
        {'project': project, **data}
        for project, data in project_usage.items()
    ]).sort_values('cost', ascending=False)

    return stats, daily_df, model_df, branch_df, tool_df, project_df


# 사이드바 - 파일 업로드
with st.sidebar:
    st.header("📁 데이터 로드")

    # 옵션 1: 폴더 경로 입력
    folder_path = st.text_input(
        "프로젝트 폴더 경로",
        value=str(Path.home() / ".claude" / "projects"),
        help="~/.claude/projects 폴더 경로를 입력하세요"
    )

    load_button = st.button("📂 폴더에서 로드")

    st.markdown("---")

    # 옵션 2: 파일 업로드
    uploaded_files = st.file_uploader(
        "또는 JSONL 파일 업로드",
        type=['jsonl'],
        accept_multiple_files=True,
        help="여러 개의 .jsonl 파일을 선택할 수 있습니다"
    )

# 데이터 로드
sessions = []
project_info = []

if load_button and folder_path:
    with st.spinner("프로젝트 폴더에서 데이터 로딩 중..."):
        sessions, project_info = load_all_sessions_from_projects(folder_path)

    if sessions:
        st.sidebar.success(f"✅ {len(sessions)}개 세션 로드 완료!")

        # 프로젝트 정보 표시
        if project_info:
            st.sidebar.markdown("### 📊 프로젝트 요약")
            for info in project_info:
                st.sidebar.markdown(f"**{info['project']}**: {info['sessions']}개 세션")
    else:
        st.sidebar.warning("⚠️ JSONL 파일을 찾을 수 없습니다.")

elif uploaded_files:
    with st.spinner(f"{len(uploaded_files)}개 파일 처리 중..."):
        for uploaded_file in uploaded_files:
            try:
                content = uploaded_file.read().decode('utf-8')
                messages = []
                for line in content.strip().split('\n'):
                    if line.strip():
                        messages.append(json.loads(line))

                sessions.append({
                    'session_id': uploaded_file.name.replace('.jsonl', ''),
                    'project_name': 'uploaded',
                    'project_folder': 'uploaded',
                    'messages': messages
                })
            except Exception as e:
                st.error(f"파일 처리 오류 ({uploaded_file.name}): {str(e)}")
    st.sidebar.success(f"✅ {len(sessions)}개 세션 업로드 완료!")

# 데이터 분석 및 시각화
if sessions:
    stats, daily_df, model_df, branch_df, tool_df, project_df = analyze_sessions(sessions)

    # 요약 통계
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="💰 총 비용",
            value=f"${stats['total_cost']:.2f}",
            delta=f"{stats['total_sessions']} 세션"
        )

    with col2:
        total_tokens = (stats['total_input_tokens'] + stats['total_output_tokens']) / 1000
        st.metric(
            label="📊 총 토큰",
            value=f"{total_tokens:.1f}K",
            delta=f"{stats['total_messages']} 메시지"
        )

    with col3:
        cache_saved = stats['total_cache_read_tokens'] / 1000
        st.metric(
            label="⚡ 캐시 절약",
            value=f"{cache_saved:.1f}K",
            delta="토큰"
        )

    with col4:
        st.metric(
            label="📝 평균 토큰/메시지",
            value=f"{stats['avg_tokens_per_message']:.0f}",
            delta="tokens"
        )

    st.markdown("---")

    # 프로젝트별 사용량
    st.subheader("📁 프로젝트별 사용량")
    if not project_df.empty:
        col1, col2 = st.columns([2, 1])

        with col1:
            fig = px.bar(
                project_df,
                x='project',
                y='cost',
                title='프로젝트별 비용',
                color='cost',
                color_continuous_scale='Blues'
            )
            fig.update_layout(
                xaxis_title="프로젝트",
                yaxis_title="비용 ($)",
                xaxis_tickangle=-45,
                showlegend=False
            )
            st.plotly_chart(fig)

        with col2:
            # 프로젝트 데이터 테이블
            display_project_df = project_df.copy()
            display_project_df['cost'] = display_project_df['cost'].apply(lambda x: f"${x:.4f}")
            display_project_df['tokens'] = display_project_df['tokens'].apply(lambda x: f"{x:,}")
            st.dataframe(
                display_project_df,
                hide_index=True,
                height=400
            )

    st.markdown("---")

    # 일별 사용량 차트
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 일별 토큰 사용량")
        if not daily_df.empty:
            fig = px.line(
                daily_df,
                x='date',
                y='tokens',
                markers=True,
                title='일별 토큰 사용 추이'
            )
            fig.update_layout(
                xaxis_title="날짜",
                yaxis_title="토큰 수",
                hovermode='x unified'
            )
            st.plotly_chart(fig)
        else:
            st.info("데이터가 없습니다.")

    with col2:
        st.subheader("💵 일별 비용")
        if not daily_df.empty:
            fig = px.bar(
                daily_df,
                x='date',
                y='cost',
                title='일별 비용 추이'
            )
            fig.update_layout(
                xaxis_title="날짜",
                yaxis_title="비용 ($)",
                hovermode='x unified'
            )
            st.plotly_chart(fig)
        else:
            st.info("데이터가 없습니다.")

    st.markdown("---")

    # 모델별, 브랜치별 사용량
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🤖 모델별 사용 빈도")
        if not model_df.empty:
            # 모델명 단순화
            model_df['short_name'] = model_df['model'].apply(
                lambda x: '-'.join(x.split('-')[-2:]) if isinstance(x, str) else x
            )

            fig = px.pie(
                model_df,
                values='count',
                names='short_name',
                title='모델 사용 분포'
            )
            st.plotly_chart(fig)
        else:
            st.info("데이터가 없습니다.")

    with col2:
        st.subheader("🌿 브랜치별 사용량 (Top 10)")
        if not branch_df.empty:
            fig = px.bar(
                branch_df,
                x='count',
                y='branch',
                orientation='h',
                title='브랜치별 메시지 수'
            )
            fig.update_layout(
                xaxis_title="메시지 수",
                yaxis_title="브랜치",
                height=400
            )
            st.plotly_chart(fig)
        else:
            st.info("데이터가 없습니다.")

    st.markdown("---")

    # 도구 사용 통계
    st.subheader("🔧 도구 사용 통계 (Top 10)")
    if not tool_df.empty:
        col1, col2 = st.columns([2, 1])

        with col1:
            fig = px.bar(
                tool_df,
                x='tool',
                y='count',
                title='가장 많이 사용된 도구'
            )
            fig.update_layout(
                xaxis_title="도구",
                yaxis_title="사용 횟수",
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig)

        with col2:
            st.dataframe(
                tool_df,
                hide_index=True,
                height=400
            )
    else:
        st.info("도구 사용 데이터가 없습니다.")

    st.markdown("---")

    # 상세 데이터 테이블
    with st.expander("📋 상세 일별 데이터 보기"):
        if not daily_df.empty:
            # 비용을 소수점 4자리로 포맷
            display_df = daily_df.copy()
            display_df['cost'] = display_df['cost'].apply(lambda x: f"${x:.4f}")
            st.dataframe(display_df, hide_index=True)
        else:
            st.info("데이터가 없습니다.")

    # 다운로드 버튼
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if not daily_df.empty:
            csv = daily_df.to_csv(index=False)
            st.download_button(
                label="📥 일별 데이터 CSV",
                data=csv,
                file_name="claude_code_daily_usage.csv",
                mime="text/csv"
            )

    with col2:
        if not project_df.empty:
            csv = project_df.to_csv(index=False)
            st.download_button(
                label="📥 프로젝트별 데이터 CSV",
                data=csv,
                file_name="claude_code_project_usage.csv",
                mime="text/csv"
            )

    with col3:
        if not model_df.empty:
            csv = model_df.to_csv(index=False)
            st.download_button(
                label="📥 모델별 데이터 CSV",
                data=csv,
                file_name="claude_code_model_usage.csv",
                mime="text/csv"
            )

    with col4:
        if not tool_df.empty:
            csv = tool_df.to_csv(index=False)
            st.download_button(
                label="📥 도구 사용 데이터 CSV",
                data=csv,
                file_name="claude_code_tool_usage.csv",
                mime="text/csv"
            )

else:
    # 초기 화면
    st.info("👈 왼쪽 사이드바에서 데이터를 로드해주세요.")

    st.markdown("""
    ### 사용 방법

    1. **폴더에서 로드**: 
       - `~/.claude/projects` 폴더 경로 입력
       - "폴더에서 로드" 버튼 클릭
       - 각 프로젝트 폴더의 JSONL 파일들을 자동으로 읽어옵니다

    2. **파일 업로드**:
       - 하나 이상의 `.jsonl` 파일 선택
       - 자동으로 분석 시작

    ### 폴더 구조 예시
    ```
    ~/.claude/projects/
    ├── -Users-apeltop-project-personal-jodal-insert-test/
    │   ├── session1.jsonl
    │   └── session2.jsonl
    └── -Users-apeltop-project-company-bank-bank-app-agency-app/
        ├── session3.jsonl
        └── session4.jsonl
    ```

    ### 주요 기능

    - 📁 프로젝트별 사용량 분석
    - 📊 토큰 사용량 및 비용 추적
    - 📈 일별 사용 패턴 분석
    - 🤖 모델별 사용 통계
    - 🌿 브랜치별 활동 분석
    - 🔧 도구 사용 빈도 분석
    - 📥 CSV 다운로드 지원
    """)