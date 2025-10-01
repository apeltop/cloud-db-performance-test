"""
Data migration handler for PostgreSQL
"""
import os
import json
import psycopg2
import psycopg2.extras
import streamlit as st
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class StreamlitDataMigrator:
    def __init__(self, logger=None, batch_size=1000, num_connections=1):
        self.conn = None
        self.logger = logger or logging.getLogger(__name__)
        self.batch_performance_stats = []
        self.batch_size = batch_size
        self.num_connections = num_connections
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
                if value is None or value == "":
                    prepared_data[column] = None
                else:
                    prepared_data[column] = str(value) if not isinstance(value, str) else value
            else:
                prepared_data[column] = None

        return prepared_data

    def insert_batch(self, table_name: str, records: List[Dict[str, Any]], batch_size: int = None) -> int:
        """Insert records in batches with performance monitoring"""
        if not records:
            return 0

        # Use instance batch_size if not provided
        if batch_size is None:
            batch_size = self.batch_size

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

                # Data preparation phase
                data_prep_start = time.time()
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

                    data_prep_end = time.time()
                    data_preparation_time = data_prep_end - data_prep_start

                    # Log the SQL for debugging (to file only)
                    self.logger.debug(f"SQL: {insert_sql}")
                    if i == 0:  # Log sample data for first batch
                        self.logger.debug(f"Sample data: {batch_data[0] if batch_data else 'No data'}")

                    # Execute batch with timing (query execution phase)
                    query_exec_start = time.time()
                    cur.executemany(insert_sql, batch_data)
                    query_exec_end = time.time()
                    query_execution_time = query_exec_end - query_exec_start

                    # Commit phase
                    commit_start = time.time()
                    self.conn.commit()
                    commit_end = time.time()
                    commit_time = commit_end - commit_start

                    total_inserted += len(batch_data)
                    batch_end_time = time.time()

                    # Calculate performance metrics
                    batch_duration = batch_end_time - batch_start_time
                    records_per_second = len(batch_data) / batch_duration if batch_duration > 0 else 0
                    network_db_time = query_execution_time + commit_time
                    overhead_time = batch_duration - data_preparation_time - network_db_time

                    # Store batch performance stats
                    batch_stat = {
                        "batch_number": batch_number,
                        "table_name": table_name,
                        "records_count": len(batch_data),
                        "start_time": datetime.fromtimestamp(batch_start_time),
                        "end_time": datetime.fromtimestamp(batch_end_time),
                        "total_duration_seconds": batch_duration,
                        "data_preparation_time": data_preparation_time,
                        "query_execution_time": query_execution_time,
                        "commit_time": commit_time,
                        "network_db_time": network_db_time,
                        "overhead_time": overhead_time,
                        "records_per_second": records_per_second,
                        "cumulative_records": total_inserted
                    }
                    self.batch_performance_stats.append(batch_stat)

                    # Update session state for real-time monitoring
                    try:
                        if hasattr(st, 'session_state'):
                            st.session_state.current_batch_stats = self.batch_performance_stats.copy()
                            st.session_state.migration_progress['current_batch'] = batch_number
                            # Force UI refresh for real-time updates
                            if batch_number % 5 == 0:  # Refresh every 5 batches to avoid too frequent updates
                                try:
                                    st.rerun()
                                except:
                                    pass  # Ignore if rerun is not available in this context
                    except ImportError:
                        pass

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

            # Update migration progress
            try:
                if hasattr(st, 'session_state'):
                    st.session_state.migration_progress['current_file'] = filename
            except ImportError:
                pass

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