"""
Stats writer utility for migration progress and statistics
Thread-safe JSON file operations for migration monitoring
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime
import threading


class StatsWriter:
    """Thread-safe writer for migration statistics"""

    def __init__(self, output_dir: str = "migration_outputs", cloud_provider: str = None, instance_type: str = None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.progress_file = self.output_dir / "migration_progress.json"
        self.stats_file = self.output_dir / "migration_stats.json"
        self.results_file = self.output_dir / "migration_results.json"

        self.cloud_provider = cloud_provider
        self.instance_type = instance_type

        self._lock = threading.Lock()

        # Initialize files
        self._init_files()

    def _init_files(self):
        """Initialize JSON files with empty structures"""
        if not self.progress_file.exists():
            self._write_json(self.progress_file, {
                "status": "idle",
                "current_file": "",
                "current_batch": 0,
                "files_completed": 0,
                "total_files": 0,
                "total_records_processed": 0,
                "start_time": None,
                "last_update": None
            })

        if not self.stats_file.exists():
            self._write_json(self.stats_file, {"batches": []})

        if not self.results_file.exists():
            self._write_json(self.results_file, {})

    def _write_json(self, file_path: Path, data: Dict[str, Any]):
        """Write JSON data to file"""
        with self._lock:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def _read_json(self, file_path: Path) -> Dict[str, Any]:
        """Read JSON data from file"""
        with self._lock:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}

    def update_progress(self, **kwargs):
        """Update migration progress"""
        progress = self._read_json(self.progress_file)
        progress.update(kwargs)
        progress['last_update'] = datetime.now().isoformat()
        self._write_json(self.progress_file, progress)

    def start_migration(self, total_files: int):
        """Mark migration start"""
        progress_data = {
            "status": "running",
            "current_file": "",
            "current_batch": 0,
            "files_completed": 0,
            "total_files": total_files,
            "total_records_processed": 0,
            "start_time": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat()
        }
        if self.cloud_provider:
            progress_data["cloud_provider"] = self.cloud_provider
        if self.instance_type:
            progress_data["instance_type"] = self.instance_type

        self._write_json(self.progress_file, progress_data)
        # Reset stats
        stats_data = {"batches": []}
        if self.cloud_provider:
            stats_data["cloud_provider"] = self.cloud_provider
        if self.instance_type:
            stats_data["instance_type"] = self.instance_type
        self._write_json(self.stats_file, stats_data)

    def add_batch_stat(self, batch_stat: Dict[str, Any]):
        """Add a batch statistic"""
        stats = self._read_json(self.stats_file)
        if "batches" not in stats:
            stats["batches"] = []
        stats["batches"].append(batch_stat)
        self._write_json(self.stats_file, stats)

    def complete_file(self, file_result: Dict[str, Any]):
        """Mark a file as completed"""
        progress = self._read_json(self.progress_file)
        progress['files_completed'] = progress.get('files_completed', 0) + 1
        progress['current_file'] = ""
        progress['last_update'] = datetime.now().isoformat()
        self._write_json(self.progress_file, progress)

    def complete_migration(self, results: Dict[str, Any]):
        """Mark migration as completed and save final results"""
        # Update progress
        progress = self._read_json(self.progress_file)
        progress['status'] = 'completed'
        progress['last_update'] = datetime.now().isoformat()
        self._write_json(self.progress_file, progress)

        # Save final results with cloud metadata
        results['completion_time'] = datetime.now().isoformat()
        if self.cloud_provider:
            results['cloud_provider'] = self.cloud_provider
        if self.instance_type:
            results['instance_type'] = self.instance_type
        self._write_json(self.results_file, results)

    def error_migration(self, error_message: str):
        """Mark migration as failed"""
        progress = self._read_json(self.progress_file)
        progress['status'] = 'error'
        progress['error_message'] = error_message
        progress['last_update'] = datetime.now().isoformat()
        self._write_json(self.progress_file, progress)

    def read_progress(self) -> Dict[str, Any]:
        """Read current progress"""
        return self._read_json(self.progress_file)

    def read_stats(self) -> Dict[str, Any]:
        """Read batch statistics"""
        return self._read_json(self.stats_file)

    def read_results(self) -> Dict[str, Any]:
        """Read final results"""
        return self._read_json(self.results_file)

    def clear_all(self):
        """Clear all statistics files"""
        self._init_files()