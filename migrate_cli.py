#!/usr/bin/env python3
"""
CLI Data Migration Script for Bid Information
Processes JSON files and inserts data into PostgreSQL with real-time stats output
"""

import os
import json
import psycopg2
import psycopg2.extras
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv
from datetime import datetime
from services.migration.stats_writer import StatsWriter

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CLIDataMigrator:
    """Command-line data migrator with stats output"""

    def __init__(self, output_dir: str = "migration_outputs"):
        self.conn = None
        self.cloud_provider = os.getenv('CLOUD_PROVIDER', 'Unknown')
        self.instance_type = os.getenv('INSTANCE_TYPE', 'Unknown')
        self.env = os.getenv('ENV', 'CLOUD POSTGRESQL')
        self.stats_writer = StatsWriter(output_dir, self.cloud_provider, self.instance_type)
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
            logger.info("Successfully connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

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
            logger.warning(f"Unknown file pattern: {filename}")
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
            return columns
        except Exception as e:
            logger.error(f"Failed to get columns for {table_name}: {e}")
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

    def insert_batch(self, table_name: str, records: List[Dict[str, Any]], batch_size: int = 1000) -> int:
        """Insert records in batches with performance monitoring"""
        if not records:
            return 0

        table_columns = self.get_table_columns(table_name)
        if not table_columns:
            logger.error(f"No columns found for table {table_name}")
            return 0

        total_inserted = 0

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

                    # Execute batch
                    cur.executemany(insert_sql, batch_data)
                    self.conn.commit()

                    total_inserted += len(batch_data)
                    batch_end_time = time.time()

                    # Calculate performance metrics
                    batch_duration = batch_end_time - batch_start_time
                    records_per_second = len(batch_data) / batch_duration if batch_duration > 0 else 0

                    # Store batch performance stats
                    batch_stat = {
                        "batch_number": batch_number,
                        "table_name": table_name,
                        "records_count": len(batch_data),
                        "start_time": datetime.fromtimestamp(batch_start_time).isoformat(),
                        "end_time": datetime.fromtimestamp(batch_end_time).isoformat(),
                        "total_duration_seconds": batch_duration,
                        "records_per_second": records_per_second,
                        "cumulative_records": total_inserted
                    }
                    self.batch_performance_stats.append(batch_stat)

                    # Write to stats file
                    self.stats_writer.add_batch_stat(batch_stat)

                    # Update progress
                    self.stats_writer.update_progress(
                        current_batch=batch_number,
                        total_records_processed=total_inserted
                    )

                    # Log progress
                    logger.info(f"Batch {batch_number} for {table_name}: {len(batch_data)} records in {batch_duration:.3f}s ({records_per_second:.1f} rec/s)")

            cur.close()
            logger.info(f"Total inserted into {table_name}: {total_inserted} records")

        except Exception as e:
            logger.error(f"Failed to insert batch into {table_name}: {e}")
            self.conn.rollback()
            raise

        return total_inserted

    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single JSON file"""
        filename = file_path.name
        table_name = self.get_table_name_from_filename(filename)

        if not table_name:
            return {"filename": filename, "status": "skipped", "reason": "unknown file pattern"}

        try:
            logger.info(f"Processing {filename} -> {table_name}")

            # Update progress
            self.stats_writer.update_progress(current_file=filename)

            # Read and parse JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                logger.warning(f"Expected list in {filename}, got {type(data)}")
                return {"filename": filename, "status": "error", "reason": "invalid data format"}

            # Insert data
            inserted_count = self.insert_batch(table_name, data)

            result = {
                "filename": filename,
                "table": table_name,
                "status": "success",
                "records_processed": len(data),
                "records_inserted": inserted_count
            }

            # Mark file as completed
            self.stats_writer.complete_file(result)

            return result

        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")
            return {
                "filename": filename,
                "table": table_name,
                "status": "error",
                "reason": str(e)
            }

    def migrate_all_files(self, data_dir: str = "data") -> List[Dict[str, Any]]:
        """Process all JSON files in the data directory"""
        data_path = Path(data_dir)

        if not data_path.exists():
            raise FileNotFoundError(f"Data directory {data_dir} not found")

        # Get all JSON files except sample_data.json
        json_files = [f for f in data_path.glob("*.json") if f.name != "sample_data.json"]

        if not json_files:
            logger.warning("No JSON files found to process")
            return []

        logger.info(f"Found {len(json_files)} files to process")

        # Start migration
        self.stats_writer.start_migration(total_files=len(json_files))

        results = []

        for file_path in sorted(json_files):
            try:
                result = self.process_file(file_path)
                results.append(result)

                # Log progress
                if result["status"] == "success":
                    logger.info(f"✓ {result['filename']}: {result['records_inserted']} records inserted")
                else:
                    logger.warning(f"✗ {result['filename']}: {result.get('reason', 'unknown error')}")

            except KeyboardInterrupt:
                logger.info("Migration interrupted by user")
                self.stats_writer.error_migration("Interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error processing {file_path.name}: {e}")
                results.append({
                    "filename": file_path.name,
                    "status": "error",
                    "reason": str(e)
                })

        return results

    def print_summary(self, results: List[Dict[str, Any]]):
        """Print migration summary"""
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] == "error"]
        skipped = [r for r in results if r["status"] == "skipped"]

        total_records = sum(r.get("records_inserted", 0) for r in successful)

        print("\n" + "="*60)
        print("MIGRATION SUMMARY")
        print("="*60)
        print(f"Total files processed: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        print(f"Skipped: {len(skipped)}")
        print(f"Total records inserted: {total_records:,}")

        if successful:
            print("\n✓ SUCCESSFUL FILES:")
            for result in successful:
                print(f"  {result['filename']} -> {result['table']}: {result['records_inserted']:,} records")

        if failed:
            print("\n✗ FAILED FILES:")
            for result in failed:
                print(f"  {result['filename']}: {result['reason']}")

        if skipped:
            print("\n⚠ SKIPPED FILES:")
            for result in skipped:
                print(f"  {result['filename']}: {result['reason']}")

        print("="*60)

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
            logger.error(f"Failed to get table counts: {e}")

        return counts

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


def main():
    """Main migration function"""
    migrator = CLIDataMigrator()

    print("="*60)
    print(f"{migrator.env} DATA MIGRATION - CLI")
    print("="*60)
    print(f"Cloud Provider: {migrator.cloud_provider}")
    print(f"Instance Type: {migrator.instance_type}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    try:
        # Show initial table counts
        print("\n📊 Initial table counts:")
        initial_counts = migrator.get_table_counts()
        for table, count in initial_counts.items():
            print(f"  {table}: {count:,} records")

        # Run migration
        print("\n🚀 Starting migration...\n")
        start_time = time.time()
        results = migrator.migrate_all_files()
        end_time = time.time()

        # Show final results
        migrator.print_summary(results)

        # Show final table counts
        print("\n📊 Final table counts:")
        final_counts = migrator.get_table_counts()
        for table, count in final_counts.items():
            initial = initial_counts.get(table, 0)
            added = count - initial
            print(f"  {table}: {count:,} records (+{added:,})")

        # Calculate performance summary
        successful = [r for r in results if r["status"] == "success"]
        failed = [r for r in results if r["status"] == "error"]
        total_records = sum(r.get("records_inserted", 0) for r in successful)
        total_duration = end_time - start_time

        # Save final results
        final_results = {
            "status": "completed" if not failed else "completed_with_errors",
            "total_files": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "total_records": total_records,
            "total_duration_seconds": total_duration,
            "average_records_per_second": total_records / total_duration if total_duration > 0 else 0,
            "file_results": results,
            "table_counts": final_counts,
            "initial_counts": initial_counts
        }

        migrator.stats_writer.complete_migration(final_results)

        print(f"\n⏱️  Total migration time: {total_duration:.2f} seconds")
        print(f"📈 Average throughput: {total_records / total_duration:.1f} records/second")
        print(f"\n✅ Statistics saved to: migration_outputs/")
        print("="*60)

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        migrator.stats_writer.error_migration(str(e))
        raise
    finally:
        migrator.close()


if __name__ == "__main__":
    main()