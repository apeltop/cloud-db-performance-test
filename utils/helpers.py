import json
import yaml
import os
from typing import Dict, Any, List

def ensure_directory_exists(path: str):
    """Ensure that a directory exists, create if it doesn't"""
    os.makedirs(path, exist_ok=True)

def load_json_file(file_path: str) -> Dict[str, Any]:
    """Load JSON file safely"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in file {file_path}: {str(e)}")

def load_yaml_file(file_path: str) -> Dict[str, Any]:
    """Load YAML file safely"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {file_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in file {file_path}: {str(e)}")

def save_json_file(data: Dict[str, Any], file_path: str):
    """Save data to JSON file"""
    ensure_directory_exists(os.path.dirname(file_path))
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def validate_schema_config(schema: Dict[str, Any]) -> bool:
    """Validate schema configuration structure"""
    required_keys = ['table_name', 'fields']

    for key in required_keys:
        if key not in schema:
            raise ValueError(f"Missing required key in schema: {key}")

    # Validate fields structure
    fields = schema['fields']
    if not isinstance(fields, dict):
        raise ValueError("Schema fields must be a dictionary")

    for field_name, field_config in fields.items():
        if 'type' not in field_config:
            raise ValueError(f"Field '{field_name}' is missing 'type' specification")

    return True

def validate_database_config(db_config: Dict[str, Any]) -> bool:
    """Validate database configuration structure"""
    if 'clouds' not in db_config:
        raise ValueError("Database config must contain 'clouds' section")

    clouds = db_config['clouds']
    required_cloud_keys = ['host', 'database', 'user', 'password']

    for cloud_name, cloud_config in clouds.items():
        for key in required_cloud_keys:
            if key not in cloud_config:
                raise ValueError(f"Cloud '{cloud_name}' is missing required key: {key}")

    return True

def get_supported_postgres_types() -> List[str]:
    """Get list of supported PostgreSQL data types"""
    return [
        'SERIAL', 'INTEGER', 'BIGINT', 'SMALLINT',
        'VARCHAR', 'TEXT', 'CHAR',
        'DECIMAL', 'NUMERIC', 'REAL', 'DOUBLE PRECISION',
        'BOOLEAN',
        'DATE', 'TIME', 'TIMESTAMP', 'TIMESTAMPTZ',
        'JSON', 'JSONB',
        'UUID'
    ]

def format_execution_time(seconds: float) -> str:
    """Format execution time in human-readable format"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.1f} μs"
    elif seconds < 1:
        return f"{seconds * 1000:.1f} ms"
    else:
        return f"{seconds:.3f} s"

def calculate_percentiles(values: List[float], percentiles: List[int] = [25, 50, 75, 95, 99]) -> Dict[int, float]:
    """Calculate percentiles for a list of values"""
    import numpy as np

    if not values:
        return {p: 0.0 for p in percentiles}

    return {p: np.percentile(values, p) for p in percentiles}

def generate_performance_report(results: Dict[str, Any]) -> str:
    """Generate a text-based performance report"""
    report_lines = []
    report_lines.append("=" * 60)
    report_lines.append("         CLOUD POSTGRESQL PERFORMANCE REPORT")
    report_lines.append("=" * 60)
    report_lines.append("")

    for cloud, data in results.items():
        report_lines.append(f"🏢 {cloud.upper()}")
        report_lines.append("-" * 30)
        report_lines.append(f"Total Operations: {data['total_operations']}")
        report_lines.append(f"Successful: {data['successful_operations']}")
        report_lines.append(f"Failed: {data['failed_operations']}")
        report_lines.append(f"Success Rate: {data['success_rate']:.1f}%")
        report_lines.append(f"Average Time: {format_execution_time(data['average_execution_time'])}")
        report_lines.append(f"Min Time: {format_execution_time(data['min_execution_time'])}")
        report_lines.append(f"Max Time: {format_execution_time(data['max_execution_time'])}")
        report_lines.append(f"Throughput: {data['records_per_second']:.2f} records/sec")
        report_lines.append("")

    # Performance ranking
    successful_clouds = [(cloud, data) for cloud, data in results.items()
                        if data['successful_operations'] > 0]

    if successful_clouds:
        report_lines.append("🏆 PERFORMANCE RANKING")
        report_lines.append("-" * 30)

        # Sort by throughput (records per second)
        by_throughput = sorted(successful_clouds,
                             key=lambda x: x[1]['records_per_second'],
                             reverse=True)

        report_lines.append("By Throughput (records/sec):")
        for i, (cloud, data) in enumerate(by_throughput, 1):
            report_lines.append(f"  {i}. {cloud.upper()}: {data['records_per_second']:.2f}")

        report_lines.append("")

        # Sort by average execution time
        by_speed = sorted(successful_clouds,
                         key=lambda x: x[1]['average_execution_time'])

        report_lines.append("By Average Speed (lower is better):")
        for i, (cloud, data) in enumerate(by_speed, 1):
            report_lines.append(f"  {i}. {cloud.upper()}: {format_execution_time(data['average_execution_time'])}")

    report_lines.append("")
    report_lines.append("=" * 60)

    return "\n".join(report_lines)