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
chunk_size = st.sidebar.slider("청크 크기", 5, 100, 10, 10)
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📤 데이터 업로드", "🔄 데이터 마이그레이션", "📊 성능 비교", "📈 상세 분석", "⚙️ 설정"])

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
    st.header("🔄 데이터 마이그레이션")
    st.markdown("기존 입찰 데이터를 PostgreSQL 테이블에 마이그레이션합니다.")

    # 데이터 마이그레이션 import
    import os
    import json
    import psycopg2
    import psycopg2.extras
    from pathlib import Path
    from typing import Dict, List, Any, Optional
    import logging
    from datetime import datetime

    # Setup logging
    def setup_migration_logger():
        """Setup logger for migration process"""
        logger = logging.getLogger('migration')
        logger.setLevel(logging.INFO)

        # Clear existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Create file handler
        log_filename = f"migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        file_handler = logging.FileHandler(log_filename)
        file_handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        return logger, log_filename

    class StreamlitDataMigrator:
        def __init__(self, logger=None):
            self.conn = None
            self.logger = logger or logging.getLogger(__name__)
            self.batch_performance_stats = []
            self.connect_to_db()

        def connect_to_db(self):
            """Connect to PostgreSQL database"""
            try:
                self.conn = psycopg2.connect(
                    host=os.getenv('GCP_DB_HOST'),
                    port=os.getenv('GCP_DB_PORT', 5432),
                    database=os.getenv('GCP_DB_NAME'),
                    user=os.getenv('GCP_DB_USER'),
                    password=os.getenv('GCP_DB_PASSWORD'),
                    sslmode='require'
                )
                self.logger.info("Successfully connected to PostgreSQL database")
                return True
            except Exception as e:
                error_msg = f"Database connection failed: {e}"
                self.logger.error(error_msg)
                st.error(error_msg)
                return False

        def get_table_name_from_filename(self, filename: str) -> Optional[str]:
            """Extract table name from filename"""
            if filename.startswith("BidPublicInfoService_BID_CNSTWK_"):
                return "bid_pblanclistinfo_cnstwk"
            elif filename.startswith("BidPublicInfoService_BID_SERVC_"):
                return "bid_pblanclistinfo_servc"
            elif filename.startswith("BidPublicInfoService_BID_THNG_"):
                return "bid_pblanclistinfo_thng"
            elif filename.startswith("BidPublicInfoService_BID_FRGCPT_"):
                return "bid_pblanclistinfo_frgcpt"
            elif filename.startswith("PubDataOpnStdService_ScsBidInfo_"):
                return "opn_std_scsbid_info"
            else:
                return None

        def get_table_columns(self, table_name: str) -> List[str]:
            """Get column names for a table (excluding auto-generated columns)"""
            try:
                cur = self.conn.cursor()
                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = %s
                    AND column_name NOT IN ('createdAt', 'updatedAt', 'id')
                    ORDER BY ordinal_position;
                """, (table_name,))

                columns = [row[0] for row in cur.fetchall()]
                cur.close()

                # Log columns found
                self.logger.info(f"Found {len(columns)} columns for {table_name}")
                self.logger.debug(f"Columns for {table_name}: {columns}")

                return columns
            except Exception as e:
                error_msg = f"Failed to get columns for {table_name}: {e}"
                self.logger.error(error_msg)
                st.error(error_msg)
                return []

        def prepare_record_data(self, record: Dict[str, Any], table_columns: List[str]) -> Dict[str, Any]:
            """Prepare record data to match table columns"""
            prepared_data = {}

            for column in table_columns:
                if column in record:
                    value = record[column]
                    if value is None:
                        prepared_data[column] = None
                    else:
                        prepared_data[column] = str(value) if not isinstance(value, str) else value
                else:
                    prepared_data[column] = None

            return prepared_data

        def insert_batch(self, table_name: str, records: List[Dict[str, Any]], batch_size: int = 100) -> int:
            """Insert records in batches with performance monitoring"""
            if not records:
                return 0

            table_columns = self.get_table_columns(table_name)
            if not table_columns:
                st.error(f"No columns found for table {table_name}")
                return 0

            total_inserted = 0
            insert_sql = ""

            try:
                cur = self.conn.cursor()

                for i in range(0, len(records), batch_size):
                    batch_start_time = time.time()
                    batch_number = i // batch_size + 1

                    batch = records[i:i + batch_size]
                    batch_data = []

                    for record in batch:
                        prepared_data = self.prepare_record_data(record, table_columns)
                        batch_data.append(prepared_data)

                    if batch_data:
                        # Add timestamp fields for all records
                        current_timestamp = 'NOW()'
                        for data in batch_data:
                            # These will be added as SQL functions, not as parameters
                            pass

                        # Quote column names to preserve case sensitivity
                        quoted_columns = ', '.join([f'"{col}"' for col in table_columns])
                        placeholders = ', '.join([f'%({col})s' for col in table_columns])

                        # Add timestamp columns
                        quoted_columns += ', "createdAt", "updatedAt"'
                        placeholders += ', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP'

                        insert_sql = f"INSERT INTO {table_name} ({quoted_columns}) VALUES ({placeholders})"

                        # Handle special case for opn_std_scsbid_info table
                        if table_name == 'opn_std_scsbid_info':
                            for j, data in enumerate(batch_data):
                                data['id'] = f"{data.get('bidNtceNo', '')}_{data.get('bidNtceOrd', '')}_{i+j+1}"

                            quoted_columns = '"id", ' + quoted_columns
                            placeholders = '%(id)s, ' + placeholders
                            insert_sql = f"INSERT INTO {table_name} ({quoted_columns}) VALUES ({placeholders})"

                        # Log the SQL for debugging (to file only)
                        self.logger.debug(f"SQL: {insert_sql}")
                        if i == 0:  # Log sample data for first batch
                            self.logger.debug(f"Sample data: {batch_data[0] if batch_data else 'No data'}")

                        # Execute batch with timing
                        exec_start_time = time.time()
                        cur.executemany(insert_sql, batch_data)
                        self.conn.commit()
                        exec_end_time = time.time()

                        total_inserted += len(batch_data)
                        batch_end_time = time.time()

                        # Calculate performance metrics
                        batch_duration = batch_end_time - batch_start_time
                        exec_duration = exec_end_time - exec_start_time
                        records_per_second = len(batch_data) / batch_duration if batch_duration > 0 else 0

                        # Store batch performance stats
                        batch_stat = {
                            "batch_number": batch_number,
                            "table_name": table_name,
                            "records_count": len(batch_data),
                            "start_time": datetime.fromtimestamp(batch_start_time),
                            "end_time": datetime.fromtimestamp(batch_end_time),
                            "total_duration_seconds": batch_duration,
                            "execution_duration_seconds": exec_duration,
                            "records_per_second": records_per_second,
                            "cumulative_records": total_inserted
                        }
                        self.batch_performance_stats.append(batch_stat)

                        # Log progress with performance info
                        self.logger.info(f"Batch {batch_number} for {table_name}: {len(batch_data)} records in {batch_duration:.3f}s ({records_per_second:.1f} rec/s)")

                cur.close()
                self.logger.info(f"Successfully inserted {total_inserted} records into {table_name}")

            except Exception as e:
                error_msg = f"Failed to insert batch into {table_name}: {str(e)}"
                self.logger.error(error_msg)
                self.logger.error(f"Failed SQL: {insert_sql}")
                if 'batch_data' in locals() and batch_data:
                    self.logger.error(f"Failed data sample: {batch_data[0]}")
                    self.logger.error(f"Available columns: {table_columns}")
                    self.logger.error(f"Data keys: {list(batch_data[0].keys()) if batch_data else 'No data'}")

                st.error(f"❌ SQL Error in {table_name}: {str(e)}")
                self.conn.rollback()
                raise

            return total_inserted

        def process_file(self, file_path: Path, progress_bar) -> Dict[str, Any]:
            """Process a single JSON file"""
            filename = file_path.name
            table_name = self.get_table_name_from_filename(filename)

            if not table_name:
                self.logger.warning(f"Skipping {filename}: unknown file pattern")
                return {"filename": filename, "status": "skipped", "reason": "unknown file pattern"}

            try:
                self.logger.info(f"Processing {filename} -> {table_name}")

                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if not isinstance(data, list):
                    self.logger.error(f"Invalid data format in {filename}: expected list, got {type(data)}")
                    return {"filename": filename, "status": "error", "reason": "invalid data format"}

                self.logger.info(f"Loaded {len(data)} records from {filename}")
                inserted_count = self.insert_batch(table_name, data)
                progress_bar.progress(1.0)

                result = {
                    "filename": filename,
                    "table": table_name,
                    "status": "success",
                    "records_processed": len(data),
                    "records_inserted": inserted_count
                }

                self.logger.info(f"Completed {filename}: {inserted_count} records inserted")
                return result

            except Exception as e:
                error_msg = f"Failed to process {filename}: {str(e)}"
                self.logger.error(error_msg)
                return {
                    "filename": filename,
                    "table": table_name,
                    "status": "error",
                    "reason": str(e)
                }

        def get_table_counts(self) -> Dict[str, int]:
            """Get record counts for all tables"""
            tables = [
                'bid_pblanclistinfo_cnstwk',
                'bid_pblanclistinfo_frgcpt',
                'bid_pblanclistinfo_servc',
                'bid_pblanclistinfo_thng',
                'opn_std_scsbid_info'
            ]

            counts = {}
            try:
                cur = self.conn.cursor()
                for table in tables:
                    cur.execute(f'SELECT COUNT(*) FROM {table}')
                    counts[table] = cur.fetchone()[0]
                cur.close()
            except Exception as e:
                st.error(f"Failed to get table counts: {e}")

            return counts

        def get_batch_performance_stats(self) -> List[Dict[str, Any]]:
            """Get batch performance statistics"""
            return self.batch_performance_stats

        def get_performance_summary(self) -> Dict[str, Any]:
            """Get performance summary statistics"""
            if not self.batch_performance_stats:
                return {}

            total_batches = len(self.batch_performance_stats)
            total_records = sum(stat['records_count'] for stat in self.batch_performance_stats)
            total_duration = sum(stat['total_duration_seconds'] for stat in self.batch_performance_stats)

            avg_batch_time = total_duration / total_batches if total_batches > 0 else 0
            avg_records_per_second = total_records / total_duration if total_duration > 0 else 0

            # Group by table
            table_stats = {}
            for stat in self.batch_performance_stats:
                table = stat['table_name']
                if table not in table_stats:
                    table_stats[table] = {
                        'batches': 0,
                        'records': 0,
                        'duration': 0,
                        'avg_rps': 0
                    }
                table_stats[table]['batches'] += 1
                table_stats[table]['records'] += stat['records_count']
                table_stats[table]['duration'] += stat['total_duration_seconds']

            # Calculate averages for each table
            for table, stats in table_stats.items():
                if stats['duration'] > 0:
                    stats['avg_rps'] = stats['records'] / stats['duration']

            return {
                'total_batches': total_batches,
                'total_records': total_records,
                'total_duration_seconds': total_duration,
                'average_batch_time_seconds': avg_batch_time,
                'average_records_per_second': avg_records_per_second,
                'table_statistics': table_stats
            }

        def close(self):
            """Close database connection"""
            if self.conn:
                self.conn.close()

    # 마이그레이션 UI
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📁 데이터 파일 현황")

        # 데이터 디렉토리 확인
        data_path = Path("data")
        if data_path.exists():
            json_files = [f for f in data_path.glob("*.json") if f.name != "sample_data.json"]

            if json_files:
                st.success(f"✅ {len(json_files)}개의 데이터 파일을 발견했습니다.")

                # 파일 목록 표시
                file_info = []
                total_size = 0

                for file_path in sorted(json_files):
                    size_mb = file_path.stat().st_size / (1024 * 1024)
                    total_size += size_mb

                    table_name = "Unknown"
                    if file_path.name.startswith("BidPublicInfoService_BID_CNSTWK_"):
                        table_name = "bid_pblanclistinfo_cnstwk"
                    elif file_path.name.startswith("BidPublicInfoService_BID_SERVC_"):
                        table_name = "bid_pblanclistinfo_servc"
                    elif file_path.name.startswith("BidPublicInfoService_BID_THNG_"):
                        table_name = "bid_pblanclistinfo_thng"
                    elif file_path.name.startswith("BidPublicInfoService_BID_FRGCPT_"):
                        table_name = "bid_pblanclistinfo_frgcpt"
                    elif file_path.name.startswith("PubDataOpnStdService_ScsBidInfo_"):
                        table_name = "opn_std_scsbid_info"

                    file_info.append({
                        "파일명": file_path.name,
                        "크기 (MB)": f"{size_mb:.2f}",
                        "대상 테이블": table_name
                    })

                df_files = pd.DataFrame(file_info)
                st.dataframe(df_files, use_container_width=True)

                st.info(f"총 데이터 크기: {total_size:.2f} MB")

                # 마이그레이션 실행 버튼
                if st.button("🚀 데이터 마이그레이션 실행", type="primary"):
                    # Setup logger
                    logger, log_filename = setup_migration_logger()
                    st.info(f"📝 로그 파일: `{log_filename}`")

                    migrator = StreamlitDataMigrator(logger)

                    if migrator.conn:
                        # 초기 테이블 카운트
                        st.subheader("📊 마이그레이션 진행상황")
                        initial_counts = migrator.get_table_counts()

                        st.write("**초기 테이블 레코드 수:**")
                        for table, count in initial_counts.items():
                            st.write(f"  - {table}: {count:,} records")

                        # 진행상황 추적
                        progress_container = st.container()
                        results = []

                        for i, file_path in enumerate(sorted(json_files)):
                            with progress_container:
                                st.write(f"처리 중: {file_path.name}")
                                file_progress = st.progress(0)

                                result = migrator.process_file(file_path, file_progress)
                                results.append(result)

                                if result["status"] == "success":
                                    st.success(f"✅ {result['filename']}: {result['records_inserted']:,} 레코드 삽입 완료")
                                else:
                                    st.error(f"❌ {result['filename']}: {result.get('reason', '알 수 없는 오류')}")

                        # 최종 결과
                        st.subheader("🎉 마이그레이션 완료!")

                        successful = [r for r in results if r["status"] == "success"]
                        failed = [r for r in results if r["status"] == "error"]
                        skipped = [r for r in results if r["status"] == "skipped"]

                        total_records = sum(r.get("records_inserted", 0) for r in successful)

                        col_a, col_b, col_c, col_d = st.columns(4)
                        with col_a:
                            st.metric("총 파일", len(results))
                        with col_b:
                            st.metric("성공", len(successful))
                        with col_c:
                            st.metric("실패", len(failed))
                        with col_d:
                            st.metric("총 레코드", f"{total_records:,}")

                        # 최종 테이블 카운트
                        final_counts = migrator.get_table_counts()

                        st.write("**최종 테이블 레코드 수:**")
                        for table, count in final_counts.items():
                            initial = initial_counts.get(table, 0)
                            added = count - initial
                            st.write(f"  - {table}: {count:,} records (+{added:,})")

                        # 배치 성능 분석 표시
                        batch_stats = migrator.get_batch_performance_stats()
                        performance_summary = migrator.get_performance_summary()

                        if batch_stats and performance_summary:
                            st.markdown("---")
                            st.subheader("📈 배치별 성능 분석")

                            # 성능 요약 메트릭
                            col1, col2, col3, col4 = st.columns(4)
                            with col1:
                                st.metric("총 배치 수", performance_summary['total_batches'])
                            with col2:
                                st.metric("평균 배치 시간", f"{performance_summary['average_batch_time_seconds']:.3f}초")
                            with col3:
                                st.metric("평균 처리량", f"{performance_summary['average_records_per_second']:.1f} rec/s")
                            with col4:
                                st.metric("총 처리 시간", f"{performance_summary['total_duration_seconds']:.1f}초")

                            # 배치별 처리 시간 차트
                            df_batch_stats = pd.DataFrame(batch_stats)

                            if not df_batch_stats.empty:
                                # 처리 시간 추이 차트
                                fig_timeline = px.line(
                                    df_batch_stats,
                                    x='batch_number',
                                    y='total_duration_seconds',
                                    color='table_name',
                                    title='배치별 처리 시간 추이',
                                    labels={
                                        'batch_number': '배치 번호',
                                        'total_duration_seconds': '처리 시간 (초)',
                                        'table_name': '테이블'
                                    }
                                )
                                fig_timeline.update_layout(height=400)
                                st.plotly_chart(fig_timeline, use_container_width=True)

                                # 처리량 추이 차트
                                fig_throughput = px.line(
                                    df_batch_stats,
                                    x='batch_number',
                                    y='records_per_second',
                                    color='table_name',
                                    title='배치별 처리량 추이',
                                    labels={
                                        'batch_number': '배치 번호',
                                        'records_per_second': '처리량 (records/sec)',
                                        'table_name': '테이블'
                                    }
                                )
                                fig_throughput.update_layout(height=400)
                                st.plotly_chart(fig_throughput, use_container_width=True)

                                # 테이블별 성능 요약
                                if 'table_statistics' in performance_summary:
                                    st.subheader("테이블별 성능 요약")
                                    table_summary_data = []
                                    for table, stats in performance_summary['table_statistics'].items():
                                        table_summary_data.append({
                                            '테이블': table,
                                            '배치 수': stats['batches'],
                                            '총 레코드': f"{stats['records']:,}",
                                            '총 시간 (초)': f"{stats['duration']:.2f}",
                                            '평균 처리량 (rec/s)': f"{stats['avg_rps']:.1f}"
                                        })

                                    if table_summary_data:
                                        df_table_summary = pd.DataFrame(table_summary_data)
                                        st.dataframe(df_table_summary, use_container_width=True)

                        migrator.close()

            else:
                st.warning("데이터 파일을 찾을 수 없습니다.")
        else:
            st.error("data 디렉토리를 찾을 수 없습니다.")

    with col2:
        st.subheader("📋 현재 테이블 상태")

        if st.button("🔄 테이블 상태 새로고침"):
            try:
                # Use a simple logger for refresh operation
                refresh_logger = logging.getLogger('refresh')
                migrator = StreamlitDataMigrator(refresh_logger)
                if migrator.conn:
                    counts = migrator.get_table_counts()

                    st.write("**현재 레코드 수:**")
                    for table, count in counts.items():
                        st.write(f"  - {table}: {count:,}")

                    migrator.close()
            except Exception as e:
                st.error(f"테이블 상태 조회 실패: {e}")

with tab3:
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

with tab4:
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

with tab5:
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