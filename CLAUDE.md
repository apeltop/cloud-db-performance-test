# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Cloud PostgreSQL Performance Tester - A tool for benchmarking and comparing PostgreSQL performance across cloud providers (GCP, Azure, AWS) using JSON data migration workloads. The tool supports configurable batch sizes, multi-connection parallel processing, and provides real-time performance monitoring.

## Core Commands

### Run CLI Migration
```bash
# Basic migration (1000 batch size, single connection)
python migrate_cli.py

# Multi-connection parallel processing
python migrate_cli.py --batch-size 1000 --connections 10

# Small batch size for stability
python migrate_cli.py --batch-size 100 --connections 1

# Available options: --batch-size (100,500,1000,2000,5000), --connections (1,2,5,10)
```

### Run Streamlit Dashboard
```bash
streamlit run app.py
```

### Setup
```bash
pip install -r requirements.txt
# Configure .env file with database credentials for GCP/Azure/AWS
```

## Architecture

### Dual Execution Model

The project has two independent execution paths:

1. **CLI Mode** (`migrate_cli.py` + `CLIDataMigrator`):
   - Direct execution with command-line arguments
   - Writes statistics to JSON files in `migration_outputs/`
   - Supports multi-connection parallel processing via ThreadPoolExecutor
   - Used for performance benchmarking

2. **UI Mode** (`app.py` + Streamlit UI):
   - Web dashboard for monitoring migrations
   - Reads statistics from JSON files written by CLI
   - Does NOT execute migrations directly - instructs users to run CLI commands
   - Provides visualization and analysis of results

### Migration Service Architecture

**Two migrator classes** (similar but separate):
- `CLIDataMigrator` (in `migrate_cli.py`): CLI execution with parallel processing
- `StreamlitDataMigrator` (in `services/migration/migrator.py`): Used by UI for monitoring

Both share similar logic but are independent implementations.

### Multi-Connection Parallel Processing

The CLI migrator uses **ThreadPoolExecutor** to process batches in parallel:
- Data is split into batches (configurable size: 100-5000 records)
- Each worker thread gets its own database connection
- Thread-safe statistics collection using locks
- Workers process batches concurrently, collecting results via `as_completed()`

Key implementation in `migrate_cli.py:215-297` (`_insert_batch_parallel` method):
- Creates connection pool with N workers
- Each batch submitted as separate job with dedicated connection
- Results aggregated with thread-safe locking
- Connections closed after batch completion

### Statistics Tracking System

**Thread-safe JSON-based monitoring** via `StatsWriter` class:
- `migration_progress.json`: Real-time progress updates
- `migration_stats.json`: Per-batch performance metrics
- `migration_results.json`: Final summary results

Performance metrics tracked per batch:
- `data_preparation_time`: Time to prepare data structures
- `query_execution_time`: Time for SQL execution
- `commit_time`: Time for transaction commit
- `records_per_second`: Throughput metric
- `network_db_time`: Combined query + commit time
- `overhead_time`: Non-DB processing time

### Table Mapping Logic

JSON filenames map to specific PostgreSQL tables via `get_table_name_from_filename()`:
- `BidPublicInfoService_BID_CNSTWK_*.json` → `bid_pblanclistinfo_cnstwk`
- `BidPublicInfoService_BID_SERVC_*.json` → `bid_pblanclistinfo_servc`
- `BidPublicInfoService_BID_THNG_*.json` → `bid_pblanclistinfo_thng`
- `BidPublicInfoService_BID_FRGCPT_*.json` → `bid_pblanclistinfo_frgcpt`
- `PubDataOpnStdService_ScsBidInfo_*.json` → `opn_std_scsbid_info`

**Special case**: `opn_std_scsbid_info` table requires composite ID generation:
```python
data['id'] = f"{data.get('bidNtceNo', '')}_{data.get('bidNtceOrd', '')}_{offset+j+1}"
```

## Environment Configuration

Database connections read from `.env` file:
- `ENV`: Environment name (e.g., "GCP")
- `CLOUD_PROVIDER`: Cloud provider name for metadata
- `INSTANCE_TYPE`: Instance type for metadata
- `GCP_DB_HOST`, `GCP_DB_PORT`, `GCP_DB_NAME`, `GCP_DB_USER`, `GCP_DB_PASSWORD`
- `AZURE_DB_*` and `AWS_DB_*` follow same pattern

All PostgreSQL connections use `sslmode='require'`.

## Key Implementation Details

### Data Preparation Process

1. Read JSON files from `data/` directory (excluding `sample_data.json`)
2. Extract table name from filename
3. Query `information_schema.columns` to get table schema (excluding `createdAt`, `updatedAt`, `id`)
4. Prepare records to match table columns, converting values to strings, handling None/empty strings
5. Add `createdAt` and `updatedAt` with `CURRENT_TIMESTAMP`
6. Use parameterized queries with quoted column names to preserve case sensitivity

### Batch Insert Pattern

```python
# Quote column names for case sensitivity
quoted_columns = ', '.join([f'"{col}"' for col in table_columns])
placeholders = ', '.join([f'%({col})s' for col in table_columns])

# Add timestamp columns
quoted_columns += ', "createdAt", "updatedAt"'
placeholders += ', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP'

insert_sql = f"INSERT INTO {table_name} ({quoted_columns}) VALUES ({placeholders})"
cur.executemany(insert_sql, batch_data)
```

### Performance Optimization Strategy

The tool enables testing different configurations:
- **Small batches + Single connection**: Transaction stability, lower memory
- **Large batches + Single connection**: Reduced network roundtrips
- **Small batches + Multi-connection**: Balanced parallelism
- **Large batches + Multi-connection**: Maximum throughput (highest DB load)

Optimal configuration depends on:
- Network latency to database
- Database server resources (CPU, memory, max_connections)
- Data characteristics and size

## UI Components

Streamlit app organized in modules:
- `ui/migration_tab.py`: Shows data files, provides CLI command guidance
- `ui/analysis_tab.py`: Visualizes batch statistics and performance trends
- `ui/sidebar.py`: Database connection info and configuration
- `utils/session_state.py`: Session state initialization

UI reads JSON files but does NOT execute migrations - it's a monitoring dashboard only.

## Important Notes

- **Sample data exclusion**: `sample_data.json` is always excluded from processing
- **Transaction isolation**: Each batch is an independent transaction - partial failures don't rollback other batches
- **Connection management**: Multi-connection mode creates new connections per batch, closes after completion
- **Thread safety**: Stats collection uses locks to prevent race conditions
- **Case sensitivity**: Column names are quoted to preserve PostgreSQL case sensitivity
- **Empty strings**: Treated as NULL values in data preparation
