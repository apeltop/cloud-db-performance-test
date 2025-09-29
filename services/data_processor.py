import json
import asyncio
from typing import List, Dict, Any, Iterator
from dataclasses import dataclass
from services.db_manager import DatabaseManager, InsertResult

@dataclass
class ProcessingStats:
    """Statistics for data processing operation"""
    total_records: int
    total_chunks: int
    chunk_size: int
    processing_time: float
    success_count: int
    failure_count: int
    clouds_tested: List[str]

class DataProcessor:
    """Handles JSON data processing and chunking for database operations"""

    def __init__(self, db_manager: DatabaseManager, chunk_size: int = 10):
        self.db_manager = db_manager
        self.chunk_size = chunk_size
        self.results: List[InsertResult] = []

    def load_json_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Load JSON data from file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            return data
        else:
            # If single object, wrap in list
            return [data]

    def chunk_data(self, data: List[Dict[str, Any]]) -> Iterator[List[Dict[str, Any]]]:
        """Split data into chunks of specified size"""
        for i in range(0, len(data), self.chunk_size):
            yield data[i:i + self.chunk_size]

    async def process_single_cloud(self, cloud: str, data: List[Dict[str, Any]]) -> List[InsertResult]:
        """Process data insertion for a single cloud"""
        cloud_results = []

        # Test connection first
        connection_success = await self.db_manager.test_connection(cloud)
        if not connection_success:
            # Create a failure result for connection
            failure_result = InsertResult(
                cloud=cloud,
                chunk_id=0,
                records_count=0,
                execution_time=0.0,
                success=False,
                error_message=f"Failed to connect to {cloud} database"
            )
            cloud_results.append(failure_result)
            return cloud_results

        # Create table
        table_created = await self.db_manager.create_table(cloud)
        if not table_created:
            failure_result = InsertResult(
                cloud=cloud,
                chunk_id=0,
                records_count=0,
                execution_time=0.0,
                success=False,
                error_message=f"Failed to create table in {cloud} database"
            )
            cloud_results.append(failure_result)
            return cloud_results

        # Process data chunks
        chunk_id = 0
        for chunk in self.chunk_data(data):
            chunk_id += 1
            result = await self.db_manager.batch_insert(cloud, chunk_id, chunk)
            cloud_results.append(result)

        return cloud_results

    async def process_all_clouds(self, data: List[Dict[str, Any]], clouds: List[str] = None) -> ProcessingStats:
        """Process data insertion across all specified clouds"""
        import time
        start_time = time.time()

        if clouds is None:
            clouds = list(self.db_manager.connections.keys())

        # Clear previous results
        self.results.clear()

        # Process each cloud concurrently
        tasks = []
        for cloud in clouds:
            task = self.process_single_cloud(cloud, data)
            tasks.append(task)

        # Wait for all tasks to complete
        cloud_results_list = await asyncio.gather(*tasks)

        # Flatten results
        for cloud_results in cloud_results_list:
            self.results.extend(cloud_results)

        processing_time = time.time() - start_time

        # Calculate statistics
        success_count = sum(1 for r in self.results if r.success)
        failure_count = len(self.results) - success_count
        total_chunks = len(list(self.chunk_data(data))) * len(clouds)

        stats = ProcessingStats(
            total_records=len(data),
            total_chunks=total_chunks,
            chunk_size=self.chunk_size,
            processing_time=processing_time,
            success_count=success_count,
            failure_count=failure_count,
            clouds_tested=clouds
        )

        return stats

    def get_results_by_cloud(self) -> Dict[str, List[InsertResult]]:
        """Group results by cloud provider"""
        results_by_cloud = {}
        for result in self.results:
            if result.cloud not in results_by_cloud:
                results_by_cloud[result.cloud] = []
            results_by_cloud[result.cloud].append(result)
        return results_by_cloud

    def get_performance_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get performance summary for each cloud"""
        results_by_cloud = self.get_results_by_cloud()
        summary = {}

        for cloud, cloud_results in results_by_cloud.items():
            successful_results = [r for r in cloud_results if r.success]

            if successful_results:
                execution_times = [r.execution_time for r in successful_results]
                total_records = sum(r.records_count for r in successful_results)

                summary[cloud] = {
                    'total_operations': len(cloud_results),
                    'successful_operations': len(successful_results),
                    'failed_operations': len(cloud_results) - len(successful_results),
                    'success_rate': len(successful_results) / len(cloud_results) * 100,
                    'total_execution_time': sum(execution_times),
                    'average_execution_time': sum(execution_times) / len(execution_times),
                    'min_execution_time': min(execution_times),
                    'max_execution_time': max(execution_times),
                    'total_records_inserted': total_records,
                    'records_per_second': total_records / sum(execution_times) if sum(execution_times) > 0 else 0
                }
            else:
                summary[cloud] = {
                    'total_operations': len(cloud_results),
                    'successful_operations': 0,
                    'failed_operations': len(cloud_results),
                    'success_rate': 0.0,
                    'total_execution_time': 0.0,
                    'average_execution_time': 0.0,
                    'min_execution_time': 0.0,
                    'max_execution_time': 0.0,
                    'total_records_inserted': 0,
                    'records_per_second': 0.0
                }

        return summary

    def export_results_to_csv(self, file_path: str):
        """Export results to CSV file"""
        import csv
        import os

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'cloud', 'chunk_id', 'records_count', 'execution_time',
                'success', 'error_message', 'timestamp'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for result in self.results:
                writer.writerow({
                    'cloud': result.cloud,
                    'chunk_id': result.chunk_id,
                    'records_count': result.records_count,
                    'execution_time': result.execution_time,
                    'success': result.success,
                    'error_message': result.error_message or '',
                    'timestamp': result.timestamp
                })

    def export_summary_to_json(self, file_path: str):
        """Export performance summary to JSON file"""
        import os

        # Ensure directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        summary = self.get_performance_summary()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)