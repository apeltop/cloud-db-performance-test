"""
Settings tab component
"""
import streamlit as st


def render_settings_tab(config_loader):
    """Render settings tab"""
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