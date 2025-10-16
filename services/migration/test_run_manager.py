"""
Test Run Manager for managing multiple migration test executions
Handles test metadata, indexing, and comparison across different configurations
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import threading


@dataclass
class TestRun:
    """Test run metadata"""
    test_id: str
    timestamp: str
    cloud_provider: str
    instance_type: str
    batch_size: int
    num_connections: int
    status: str  # 'running', 'completed', 'error'
    output_dir: str
    total_records: Optional[int] = None
    total_duration_seconds: Optional[float] = None
    average_records_per_second: Optional[float] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class TestRunManager:
    """Manager for test run metadata and indexing"""

    def __init__(self, base_output_dir: str = "migration_outputs"):
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)

        self.runs_dir = self.base_output_dir / "runs"
        self.runs_dir.mkdir(exist_ok=True)

        self.index_file = self.base_output_dir / "test_runs_index.json"
        self._lock = threading.Lock()

        # Initialize index file
        self._init_index()

    def _init_index(self):
        """Initialize test runs index file"""
        if not self.index_file.exists():
            self._write_index({"test_runs": []})

    def _read_index(self) -> Dict[str, Any]:
        """Read test runs index"""
        with self._lock:
            if self.index_file.exists():
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"test_runs": []}

    def _write_index(self, data: Dict[str, Any]):
        """Write test runs index"""
        with self._lock:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def generate_test_id(self, cloud_provider: str, instance_type: str,
                        batch_size: int, num_connections: int) -> str:
        """
        Generate unique test ID
        Format: {timestamp}_{provider}_{instance}_b{batch}_c{conn}
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize instance_type for filename
        instance_clean = instance_type.replace(".", "_").replace(" ", "_")
        test_id = f"{timestamp}_{cloud_provider}_{instance_clean}_b{batch_size}_c{num_connections}"
        return test_id

    def create_test_run(self, cloud_provider: str, instance_type: str,
                       batch_size: int, num_connections: int) -> TestRun:
        """Create a new test run"""
        test_id = self.generate_test_id(cloud_provider, instance_type, batch_size, num_connections)

        # Create output directory for this test
        output_dir = self.runs_dir / test_id
        output_dir.mkdir(exist_ok=True)

        test_run = TestRun(
            test_id=test_id,
            timestamp=datetime.now().isoformat(),
            cloud_provider=cloud_provider,
            instance_type=instance_type,
            batch_size=batch_size,
            num_connections=num_connections,
            status="running",
            output_dir=str(output_dir.relative_to(self.base_output_dir))
        )

        # Add to index
        index_data = self._read_index()
        index_data["test_runs"].append(test_run.to_dict())
        self._write_index(index_data)

        return test_run

    def update_test_run(self, test_id: str, **updates):
        """Update test run metadata"""
        index_data = self._read_index()

        for test_run in index_data["test_runs"]:
            if test_run["test_id"] == test_id:
                test_run.update(updates)
                break

        self._write_index(index_data)

    def complete_test_run(self, test_id: str, total_records: int,
                         total_duration_seconds: float,
                         average_records_per_second: float):
        """Mark test run as completed"""
        self.update_test_run(
            test_id,
            status="completed",
            total_records=total_records,
            total_duration_seconds=total_duration_seconds,
            average_records_per_second=average_records_per_second
        )

    def error_test_run(self, test_id: str, error_message: str):
        """Mark test run as failed"""
        self.update_test_run(
            test_id,
            status="error",
            error_message=error_message
        )

    def get_test_run(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get specific test run by ID"""
        index_data = self._read_index()
        for test_run in index_data["test_runs"]:
            if test_run["test_id"] == test_id:
                return test_run
        return None

    def get_all_test_runs(self) -> List[Dict[str, Any]]:
        """Get all test runs"""
        index_data = self._read_index()
        return index_data.get("test_runs", [])

    def get_test_runs_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get test runs by status"""
        all_runs = self.get_all_test_runs()
        return [run for run in all_runs if run.get("status") == status]

    def get_test_runs_by_provider(self, cloud_provider: str) -> List[Dict[str, Any]]:
        """Get test runs by cloud provider"""
        all_runs = self.get_all_test_runs()
        return [run for run in all_runs if run.get("cloud_provider") == cloud_provider]

    def get_recent_test_runs(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get most recent test runs"""
        all_runs = self.get_all_test_runs()
        # Sort by timestamp descending
        sorted_runs = sorted(all_runs, key=lambda x: x.get("timestamp", ""), reverse=True)
        return sorted_runs[:limit]

    def get_test_output_dir(self, test_id: str) -> Optional[Path]:
        """Get full path to test output directory"""
        test_run = self.get_test_run(test_id)
        if test_run:
            return self.base_output_dir / test_run["output_dir"]
        return None
