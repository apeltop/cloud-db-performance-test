import asyncio
import time
import random
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from config.config_loader import ConfigLoader

@dataclass
class DatabaseConnection:
    """Database connection information"""
    cloud: str
    name: str
    host: str
    port: int
    database: str
    user: str
    password: str
    ssl_mode: str = "require"
    connection_timeout: int = 30

@dataclass
class InsertResult:
    """Result of a batch insert operation"""
    cloud: str
    chunk_id: int
    records_count: int
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

class DatabaseManager:
    """Manages database connections and operations for cloud PostgreSQL instances"""

    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.db_config = config_loader.load_database_config()
        self.schema_config = config_loader.load_schema()
        self.mock_settings = config_loader.get_mock_settings()
        self.connections: Dict[str, DatabaseConnection] = {}
        self._setup_connections()

    def _setup_connections(self):
        """Initialize database connections for all clouds"""
        clouds_config = self.db_config.get('clouds', {})

        for cloud, config in clouds_config.items():
            self.connections[cloud] = DatabaseConnection(
                cloud=cloud,
                name=config.get('name', f'{cloud.upper()} PostgreSQL'),
                host=config.get('host', 'localhost'),
                port=config.get('port', 5432),
                database=config.get('database', f'test_{cloud}'),
                user=config.get('user', 'postgres'),
                password=config.get('password', 'password'),
                ssl_mode=config.get('ssl_mode', 'require'),
                connection_timeout=config.get('connection_timeout', 30)
            )

    def get_table_creation_sql(self) -> str:
        """Generate CREATE TABLE SQL from schema configuration"""
        table_name = self.schema_config['table_name']
        fields = self.schema_config['fields']

        sql_parts = [f"CREATE TABLE IF NOT EXISTS {table_name} ("]

        field_definitions = []
        for field_name, field_config in fields.items():
            field_def = f"    {field_name} {field_config['type']}"

            if field_config.get('primary_key'):
                field_def += " PRIMARY KEY"
            elif not field_config.get('nullable', True):
                field_def += " NOT NULL"

            if 'default' in field_config:
                default_val = field_config['default']
                if default_val == "NOW()":
                    field_def += " DEFAULT NOW()"
                elif isinstance(default_val, bool):
                    field_def += f" DEFAULT {str(default_val).upper()}"
                else:
                    field_def += f" DEFAULT '{default_val}'"

            field_definitions.append(field_def)

        sql_parts.append(",\n".join(field_definitions))
        sql_parts.append(");")

        return "\n".join(sql_parts)

    def generate_insert_sql(self, records: List[Dict[str, Any]]) -> tuple[str, List[tuple]]:
        """Generate INSERT SQL and parameters from records"""
        if not records:
            return "", []

        table_name = self.schema_config['table_name']
        fields = self.schema_config['fields']

        # Get field names (excluding auto-generated fields like SERIAL)
        insert_fields = []
        for field_name, field_config in fields.items():
            if field_config['type'] != 'SERIAL':
                insert_fields.append(field_name)

        # Generate SQL
        placeholders = ", ".join([f"${i+1}" for i in range(len(insert_fields))])
        sql = f"INSERT INTO {table_name} ({', '.join(insert_fields)}) VALUES ({placeholders})"

        # Generate parameters
        parameters = []
        for record in records:
            param_tuple = []
            for field_name in insert_fields:
                value = record.get(field_name)

                # Handle special cases
                if field_name == 'metadata' and isinstance(value, dict):
                    import json
                    param_tuple.append(json.dumps(value, ensure_ascii=False))
                else:
                    param_tuple.append(value)

            parameters.append(tuple(param_tuple))

        return sql, parameters

    async def test_connection(self, cloud: str) -> bool:
        """Test database connection"""
        if self.mock_settings['enabled']:
            # Simulate connection test with random delay
            await asyncio.sleep(random.uniform(0.01, 0.05))
            # 95% success rate for mock connections
            return random.random() < 0.95

        # TODO: Implement real database connection test
        # For now, return True for development
        return True

    async def create_table(self, cloud: str) -> bool:
        """Create table in specified cloud database"""
        if self.mock_settings['enabled']:
            # Simulate table creation
            await asyncio.sleep(random.uniform(0.02, 0.08))
            return True

        # TODO: Implement real table creation
        return True

    async def batch_insert(self, cloud: str, chunk_id: int, records: List[Dict[str, Any]]) -> InsertResult:
        """Perform batch insert operation"""
        start_time = time.time()

        try:
            if self.mock_settings['enabled']:
                # Simulate database insert with realistic latency
                latency_range = self.mock_settings['latency_ranges'].get(cloud, [0.05, 0.15])
                simulated_latency = random.uniform(latency_range[0], latency_range[1])

                # Add some randomness for chunk size impact
                base_latency = simulated_latency
                chunk_impact = len(records) * 0.001  # 1ms per record
                total_latency = base_latency + chunk_impact

                await asyncio.sleep(total_latency)

                # 98% success rate for mock inserts
                success = random.random() < 0.98
                error_message = None if success else f"Mock error for {cloud} chunk {chunk_id}"

            else:
                # TODO: Implement real database insert
                success = True
                error_message = None

            execution_time = time.time() - start_time

            return InsertResult(
                cloud=cloud,
                chunk_id=chunk_id,
                records_count=len(records),
                execution_time=execution_time,
                success=success,
                error_message=error_message
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return InsertResult(
                cloud=cloud,
                chunk_id=chunk_id,
                records_count=len(records),
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )

    async def cleanup_table(self, cloud: str) -> bool:
        """Clean up test table"""
        if self.mock_settings['enabled']:
            await asyncio.sleep(random.uniform(0.01, 0.03))
            return True

        # TODO: Implement real table cleanup
        return True

    def get_connection_info(self, cloud: str) -> Optional[DatabaseConnection]:
        """Get connection information for specified cloud"""
        return self.connections.get(cloud)