import json
import yaml
import os
from typing import Dict, Any

class ConfigLoader:
    """Configuration loader for database and schema settings"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir

    def load_schema(self) -> Dict[str, Any]:
        """Load database schema configuration"""
        schema_path = os.path.join(self.config_dir, "schema.json")
        with open(schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_database_config(self) -> Dict[str, Any]:
        """Load database connection configuration"""
        db_config_path = os.path.join(self.config_dir, "database.yaml")
        with open(db_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Expand environment variables
        for cloud, settings in config.get('clouds', {}).items():
            for key, value in settings.items():
                if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
                    # Extract env var and default value
                    env_expr = value[2:-1]  # Remove ${ and }
                    if ':-' in env_expr:
                        env_var, default = env_expr.split(':-', 1)
                        settings[key] = os.getenv(env_var, default)
                    else:
                        settings[key] = os.getenv(env_expr, value)

        return config

    def get_test_settings(self) -> Dict[str, Any]:
        """Get performance test settings"""
        config = self.load_database_config()
        return config.get('test_settings', {
            'chunk_size': 10,
            'max_concurrent_connections': 5,
            'retry_attempts': 3,
            'retry_delay': 1.0
        })

    def get_mock_settings(self) -> Dict[str, Any]:
        """Get mock database settings"""
        config = self.load_database_config()
        return config.get('mock_mode', {
            'enabled': True,
            'simulate_latency': True,
            'latency_ranges': {
                'gcp': [0.05, 0.15],
                'azure': [0.08, 0.18],
                'aws': [0.06, 0.16]
            }
        })