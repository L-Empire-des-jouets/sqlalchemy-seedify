"""
Configuration management for sqlalchemy-seedify.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SeederConfig(BaseModel):
    """Main configuration for sqlalchemy-seedify."""

    # Database configuration
    database_url: Optional[str] = None
    echo_sql: bool = False

    # Seeder paths
    seeders_path: str = "seeders"
    templates_path: Optional[str] = None

    # Execution settings
    default_environment: str = "development"
    auto_discover: bool = True
    batch_size: int = 1000
    parallel_execution: bool = False
    max_workers: int = 4

    # Tracking settings
    tracking_table_name: str = "alembic_seeder_history"
    auto_create_tracking_table: bool = True

    # Safety settings
    require_confirmation_prod: bool = True
    allow_destructive_seeders: bool = False
    dry_run_by_default: bool = False

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # Integration settings
    alembic_config_path: Optional[str] = "alembic.ini"
    integrate_with_alembic: bool = True

    # Custom settings
    custom_settings: Dict[str, Any] = Field(default_factory=dict)


class Config:
    """
    Configuration manager for sqlalchemy-seedify.

    This class handles loading and managing configuration from various sources:
    - Environment variables
    - Configuration files (JSON, YAML, TOML)
    - Alembic configuration
    - Default values
    """

    CONFIG_FILE_NAMES = [
        "seeder.config.json",
        "seeder.config.yaml",
        "seeder.config.toml",
        ".seederrc",
        ".seederrc.json",
    ]

    ENV_PREFIX = "SEEDER_"

    def __init__(
        self,
        config_file: Optional[str] = None,
        load_env: bool = True,
        load_alembic: bool = True,
    ):
        """
        Initialize the configuration manager.

        Args:
            config_file: Path to configuration file
            load_env: Whether to load from environment variables
            load_alembic: Whether to load from Alembic config
        """
        self._config = SeederConfig()

        # Load .env file if present
        if load_env:
            load_dotenv()

        # Load configuration in order of precedence
        self._load_defaults()

        if config_file:
            self._load_from_file(config_file)
        else:
            self._auto_discover_config()

        if load_env:
            self._load_from_env()

        if load_alembic and self._config.integrate_with_alembic:
            self._load_from_alembic()

        # Validate configuration
        self._validate()

    def _load_defaults(self) -> None:
        """Load default configuration values."""
        # Defaults are already set in SeederConfig model
        pass

    def _auto_discover_config(self) -> None:
        """Auto-discover configuration file in project."""
        for filename in self.CONFIG_FILE_NAMES:
            config_path = Path(filename)
            if config_path.exists():
                logger.info(f"Found configuration file: {filename}")
                self._load_from_file(str(config_path))
                break

    def _load_from_file(self, file_path: str) -> None:
        """
        Load configuration from file.

        Args:
            file_path: Path to configuration file
        """
        path = Path(file_path)

        if not path.exists():
            logger.warning(f"Configuration file not found: {file_path}")
            return

        try:
            if path.suffix == ".json" or path.name.endswith(".json"):
                with open(path) as f:
                    data = json.load(f)
                    self._update_config(data)

            elif path.suffix in [".yaml", ".yml"]:
                try:
                    import yaml

                    with open(path) as f:
                        data = yaml.safe_load(f)
                        self._update_config(data)
                except ImportError:
                    logger.warning("PyYAML not installed, cannot load YAML config")

            elif path.suffix == ".toml":
                try:
                    import toml

                    with open(path) as f:
                        data = toml.load(f)
                        self._update_config(data)
                except ImportError:
                    logger.warning("toml not installed, cannot load TOML config")

            else:
                # Try to parse as JSON
                with open(path) as f:
                    data = json.load(f)
                    self._update_config(data)

            logger.info(f"Loaded configuration from {file_path}")

        except Exception as e:
            logger.error(f"Error loading configuration from {file_path}: {e}")

    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        env_mapping = {
            "DATABASE_URL": "database_url",
            "SEEDERS_PATH": "seeders_path",
            "DEFAULT_ENVIRONMENT": "default_environment",
            "BATCH_SIZE": "batch_size",
            "LOG_LEVEL": "log_level",
            "DRY_RUN": "dry_run_by_default",
        }

        for env_var, config_key in env_mapping.items():
            # Check with prefix
            prefixed_var = f"{self.ENV_PREFIX}{env_var}"
            value = os.environ.get(prefixed_var) or os.environ.get(env_var)

            if value:
                # Convert types as needed
                if config_key in ["batch_size", "max_workers"]:
                    value = int(value)
                elif config_key in [
                    "echo_sql",
                    "auto_discover",
                    "parallel_execution",
                    "dry_run_by_default",
                    "require_confirmation_prod",
                ]:
                    value = value.lower() in ["true", "1", "yes", "on"]

                setattr(self._config, config_key, value)
                logger.debug(f"Loaded {config_key} from environment variable")

    def _load_from_alembic(self) -> None:
        """Load configuration from Alembic config file."""
        if not self._config.alembic_config_path:
            return

        alembic_path = Path(self._config.alembic_config_path)

        if not alembic_path.exists():
            logger.debug(f"Alembic config not found: {alembic_path}")
            return

        try:
            from configparser import ConfigParser

            parser = ConfigParser()
            parser.read(alembic_path)

            # Try to get database URL from Alembic config
            if parser.has_option("alembic", "sqlalchemy.url"):
                url = parser.get("alembic", "sqlalchemy.url")
                if url and not self._config.database_url:
                    self._config.database_url = url
                    logger.info("Loaded database URL from Alembic config")

            # Check for custom seeder section
            if parser.has_section("seeder"):
                for key, value in parser.items("seeder"):
                    if hasattr(self._config, key):
                        # Convert types as needed
                        if key in ["batch_size", "max_workers"]:
                            value = int(value)
                        elif key in ["echo_sql", "auto_discover", "parallel_execution"]:
                            value = value.lower() in ["true", "1", "yes", "on"]

                        setattr(self._config, key, value)
                        logger.debug(f"Loaded {key} from Alembic config")

        except Exception as e:
            logger.warning(f"Error loading from Alembic config: {e}")

    def _update_config(self, data: Dict[str, Any]) -> None:
        """
        Update configuration with data from dictionary.

        Args:
            data: Configuration data
        """
        for key, value in data.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                # Add to custom settings
                self._config.custom_settings[key] = value

    def _validate(self) -> None:
        """Validate the configuration."""
        # Ensure paths exist
        if self._config.seeders_path:
            seeders_path = Path(self._config.seeders_path)
            if not seeders_path.exists():
                logger.info(f"Creating seeders directory: {seeders_path}")
                seeders_path.mkdir(parents=True, exist_ok=True)

        # Validate database URL for production
        if self._config.default_environment == "production":
            if not self._config.database_url:
                logger.warning("No database URL configured for production environment")

        # Set up logging
        logging.basicConfig(
            level=getattr(logging, self._config.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        if self._config.log_file:
            file_handler = logging.FileHandler(self._config.log_file)
            file_handler.setLevel(getattr(logging, self._config.log_level.upper()))
            logging.getLogger().addHandler(file_handler)

    @property
    def database_url(self) -> Optional[str]:
        """Get the database URL."""
        return self._config.database_url

    @property
    def seeders_path(self) -> str:
        """Get the seeders directory path."""
        return self._config.seeders_path

    @property
    def default_environment(self) -> str:
        """Get the default environment."""
        return self._config.default_environment

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        if hasattr(self._config, key):
            return getattr(self._config, key)

        return self._config.custom_settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        if hasattr(self._config, key):
            setattr(self._config, key, value)
        else:
            self._config.custom_settings[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration as dictionary
        """
        return self._config.model_dump()

    def save(self, file_path: str) -> None:
        """
        Save configuration to file.

        Args:
            file_path: Path to save configuration
        """
        path = Path(file_path)
        data = self.to_dict()

        if path.suffix == ".json":
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
        else:
            # Default to JSON format
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

        logger.info(f"Saved configuration to {file_path}")
