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
  source venv/bin/activate && streamlit run app.py
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
   - Each test run creates unique output directory in `migration_outputs/runs/{test_id}/`
   - Test metadata tracked in `migration_outputs/test_runs_index.json`
   - Supports multi-connection processing via psycopg2 connection pool
   - Used for performance benchmarking
   - Managed by `TestRunManager` for test tracking and comparison

2. **UI Mode** (`app.py` + Streamlit UI):
   - Web dashboard for monitoring migrations
   - Reads statistics from JSON files written by CLI
   - Does NOT execute migrations directly - instructs users to run CLI commands
   - Provides visualization, analysis, and comparison of multiple test runs
   - Three tabs: Migration, Analysis, Comparison

### Test Run Management

**TestRunManager** (`services/migration/test_run_manager.py`):
- Manages multiple test executions and metadata
- Creates unique test IDs: `{timestamp}_{provider}_{instance}_b{batch}_c{conn}`
- Maintains index file: `migration_outputs/test_runs_index.json`
- Provides filtering, sorting, and retrieval of test runs
- Each test run stored in separate directory: `migration_outputs/runs/{test_id}/`

**Test Run Directory Structure:**
```
migration_outputs/
├── test_runs_index.json
└── runs/
    ├── 20251016_103045_GCP_db-custom-1-3840_b1000_c1/
    │   ├── migration_progress.json
    │   ├── migration_stats.json
    │   └── migration_results.json
    └── 20251016_110530_GCP_db-custom-2-7680_b1000_c10/
        ├── migration_progress.json
        ├── migration_stats.json
        └── migration_results.json
```

### Migration Service Architecture

**CLIDataMigrator** (in `migrate_cli.py`):
- CLI execution with connection pooling
- Integrates with TestRunManager for test tracking
- Creates unique output directory per test run
- Stores results with test metadata

### Multi-Connection Processing via Connection Pool

Both migrator classes use **psycopg2.pool.ThreadedConnectionPool** for database connection management:
- Data is split into batches (configurable size: 100-5000 records)
- Connection pool maintains 1 to N database connections (configurable via `--connections`)
- Connections are reused across batches automatically
- Pool handles connection lifecycle management

Key implementation details:
- `connect_to_db()`: Creates `ThreadedConnectionPool` with `minconn=1, maxconn=num_connections`
- `get_connection()`: Gets a connection from the pool
- `return_connection()`: Returns connection to pool after batch completion
- `close()`: Closes all pooled connections via `closeall()`
- No threading complexity or locks needed - pool handles concurrency

### Statistics Tracking System

**JSON-based monitoring** via `StatsWriter` class:
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

JSON filenames map to PostgreSQL table via `get_table_name_from_filename()`:
- `PubDataOpnStdService_ScsBidInfo_*.json` → `opn_std_scsbid_info`

**Composite ID Generation**: Each record requires a unique composite ID:
```python
data['id'] = f"{data.get('bidNtceNo', '')}_{data.get('bidNtceOrd', '')}_{offset+j+1}"
```

This tool focuses on a single table (`opn_std_scsbid_info`) for database performance testing, keeping business logic minimal while maintaining sufficient data volume.

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
# Generate composite ID for each record
for j, data in enumerate(batch_data):
    data['id'] = f"{data.get('bidNtceNo', '')}_{data.get('bidNtceOrd', '')}_{offset+j+1}"

# Quote column names for case sensitivity
quoted_columns = '"id", ' + ', '.join([f'"{col}"' for col in table_columns])
placeholders = '%(id)s, ' + ', '.join([f'%({col})s' for col in table_columns])

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

Streamlit app organized in modules with three main tabs:

1. **Migration Tab** (`ui/migration_tab.py`):
   - Shows data files and CLI command guidance
   - Displays recent test runs (last 5)
   - Shows test status (running, completed, error)
   - Provides quick view of test configurations and results

2. **Analysis Tab** (`ui/analysis_tab.py`):
   - Test selection dropdown to choose which test to analyze
   - File-level migration results
   - Batch-level performance statistics
   - Performance charts (duration, throughput, cumulative records)
   - Time breakdown analysis (data prep, query, commit, overhead)

3. **Comparison Tab** (`ui/comparison_tab.py`):
   - Lists all completed test runs
   - Filters by provider, batch size, connections, status
   - Multi-select for comparing 2+ tests
   - Comparison charts:
     - Total duration comparison (bar chart)
     - Average throughput comparison (bar chart)
     - Batch-level performance overlay (line charts)
     - Time breakdown comparison (stacked bar)
     - Configuration analysis (scatter plots)

**Supporting Modules:**
- `ui/sidebar.py`: Database connection info and configuration
- `utils/session_state.py`: Session state initialization
- `utils/comparison_utils.py`: Comparison data processing and analysis

UI reads JSON files but does NOT execute migrations - it's a monitoring and analysis dashboard only.

## Important Notes

- **Sample data exclusion**: `sample_data.json` is always excluded from processing
- **Transaction isolation**: Each batch is an independent transaction - partial failures don't rollback other batches
- **Connection pooling**: Uses `psycopg2.pool.ThreadedConnectionPool` for efficient connection reuse
- **Connection management**: Connections obtained from pool per batch, returned after completion
- **Case sensitivity**: Column names are quoted to preserve PostgreSQL case sensitivity
- **Empty strings**: Treated as NULL values in data preparation
- **Test isolation**: Each test run creates a separate directory - no data overwriting
- **Test tracking**: All tests indexed in `test_runs_index.json` for easy retrieval and comparison
- **Multi-test comparison**: Dashboard supports comparing unlimited number of test runs simultaneously
