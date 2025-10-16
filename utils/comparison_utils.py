"""
Comparison utilities for analyzing multiple test runs
Provides functions for merging, analyzing, and visualizing test comparisons
"""
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import pandas as pd


def load_test_stats(test_output_dir: Path) -> Optional[Dict[str, Any]]:
    """Load statistics from a test run directory"""
    stats_file = test_output_dir / "migration_stats.json"
    if stats_file.exists():
        try:
            with open(stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    return None


def load_test_results(test_output_dir: Path) -> Optional[Dict[str, Any]]:
    """Load results from a test run directory"""
    results_file = test_output_dir / "migration_results.json"
    if results_file.exists():
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    return None


def merge_test_data(test_runs: List[Dict[str, Any]], base_output_dir: Path) -> List[Dict[str, Any]]:
    """
    Merge test run metadata with detailed statistics

    Args:
        test_runs: List of test run metadata from index
        base_output_dir: Base output directory path

    Returns:
        List of merged test data with stats and results
    """
    merged_data = []

    for test_run in test_runs:
        test_output_dir = base_output_dir / test_run['output_dir']

        # Load stats and results
        stats = load_test_stats(test_output_dir)
        results = load_test_results(test_output_dir)

        # Create merged entry
        merged = {
            **test_run,
            'stats': stats,
            'results': results,
            'has_stats': stats is not None,
            'has_results': results is not None
        }

        merged_data.append(merged)

    return merged_data


def calculate_performance_metrics(test_runs: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Calculate performance comparison metrics

    Args:
        test_runs: List of test run metadata

    Returns:
        DataFrame with comparison metrics
    """
    metrics = []

    for test_run in test_runs:
        if test_run.get('status') == 'completed':
            metric = {
                'test_id': test_run['test_id'],
                'timestamp': test_run['timestamp'],
                'cloud_provider': test_run['cloud_provider'],
                'instance_type': test_run['instance_type'],
                'batch_size': test_run['batch_size'],
                'num_connections': test_run['num_connections'],
                'total_records': test_run.get('total_records', 0),
                'total_duration_seconds': test_run.get('total_duration_seconds', 0),
                'average_records_per_second': test_run.get('average_records_per_second', 0)
            }
            metrics.append(metric)

    df = pd.DataFrame(metrics)

    # Add ranking columns
    if not df.empty:
        df['duration_rank'] = df['total_duration_seconds'].rank(ascending=True)
        df['throughput_rank'] = df['average_records_per_second'].rank(ascending=False)

    return df


def calculate_percentage_difference(base_value: float, compare_value: float) -> float:
    """Calculate percentage difference between two values"""
    if base_value == 0:
        return 0.0
    return ((compare_value - base_value) / base_value) * 100


def analyze_performance_comparison(test_runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze performance differences between test runs

    Args:
        test_runs: List of test run metadata

    Returns:
        Analysis results with comparisons
    """
    df = calculate_performance_metrics(test_runs)

    if df.empty:
        return {
            'status': 'no_data',
            'message': 'No completed test runs to compare'
        }

    # Find best and worst performers
    best_throughput = df.loc[df['average_records_per_second'].idxmax()]
    worst_throughput = df.loc[df['average_records_per_second'].idxmin()]
    fastest_duration = df.loc[df['total_duration_seconds'].idxmin()]
    slowest_duration = df.loc[df['total_duration_seconds'].idxmax()]

    # Calculate average metrics
    avg_throughput = df['average_records_per_second'].mean()
    avg_duration = df['total_duration_seconds'].mean()

    # Performance by cloud provider
    provider_stats = df.groupby('cloud_provider').agg({
        'average_records_per_second': 'mean',
        'total_duration_seconds': 'mean'
    }).to_dict()

    # Performance by configuration
    config_stats = df.groupby(['batch_size', 'num_connections']).agg({
        'average_records_per_second': 'mean',
        'total_duration_seconds': 'mean'
    }).to_dict()

    return {
        'status': 'success',
        'total_tests': len(df),
        'best_throughput': {
            'test_id': best_throughput['test_id'],
            'value': best_throughput['average_records_per_second'],
            'provider': best_throughput['cloud_provider'],
            'instance': best_throughput['instance_type']
        },
        'worst_throughput': {
            'test_id': worst_throughput['test_id'],
            'value': worst_throughput['average_records_per_second'],
            'provider': worst_throughput['cloud_provider'],
            'instance': worst_throughput['instance_type']
        },
        'fastest_duration': {
            'test_id': fastest_duration['test_id'],
            'value': fastest_duration['total_duration_seconds'],
            'provider': fastest_duration['cloud_provider'],
            'instance': fastest_duration['instance_type']
        },
        'slowest_duration': {
            'test_id': slowest_duration['test_id'],
            'value': slowest_duration['total_duration_seconds'],
            'provider': slowest_duration['cloud_provider'],
            'instance': slowest_duration['instance_type']
        },
        'averages': {
            'throughput': avg_throughput,
            'duration': avg_duration
        },
        'by_provider': provider_stats,
        'by_configuration': config_stats
    }


def prepare_batch_comparison_data(selected_tests: List[Dict[str, Any]],
                                   base_output_dir: Path) -> pd.DataFrame:
    """
    Prepare batch-level data for comparison charts

    Args:
        selected_tests: List of selected test runs
        base_output_dir: Base output directory path

    Returns:
        DataFrame with batch-level data from all selected tests
    """
    all_batches = []

    for test_run in selected_tests:
        test_output_dir = base_output_dir / test_run['output_dir']
        stats = load_test_stats(test_output_dir)

        if stats and 'batches' in stats:
            for batch in stats['batches']:
                batch_data = {
                    'test_id': test_run['test_id'],
                    'test_label': f"{test_run['cloud_provider']}-{test_run['instance_type']}-b{test_run['batch_size']}-c{test_run['num_connections']}",
                    'cloud_provider': test_run['cloud_provider'],
                    'instance_type': test_run['instance_type'],
                    'batch_size': test_run['batch_size'],
                    'num_connections': test_run['num_connections'],
                    **batch
                }
                all_batches.append(batch_data)

    return pd.DataFrame(all_batches)


def get_test_summary(test_run: Dict[str, Any]) -> str:
    """Generate a human-readable summary for a test run"""
    provider = test_run.get('cloud_provider', 'Unknown')
    instance = test_run.get('instance_type', 'Unknown')
    batch = test_run.get('batch_size', 0)
    conn = test_run.get('num_connections', 0)

    return f"{provider} {instance} (batch:{batch}, conn:{conn})"
