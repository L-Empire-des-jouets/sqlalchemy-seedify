"""
Environment management for seeders.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EnvironmentConfig(BaseModel):
    """Configuration for an environment."""

    name: str
    database_url: Optional[str] = None
    seeders_path: str = "seeders"
    auto_discover: bool = True
    allowed_seeders: List[str] = Field(default_factory=list)
    excluded_seeders: List[str] = Field(default_factory=list)
    variables: Dict[str, Any] = Field(default_factory=dict)
    is_production: bool = False
    require_confirmation: bool = False


class EnvironmentManager:
    """
    Manages different environments and their configurations.

    This class handles environment-specific settings and provides
    methods to work with different environments (dev, test, prod, etc.).
    """

    DEFAULT_ENVIRONMENTS = {
        "development": EnvironmentConfig(
            name="development",
            is_production=False,
            require_confirmation=False,
        ),
        "testing": EnvironmentConfig(
            name="testing",
            is_production=False,
            require_confirmation=False,
        ),
        "staging": EnvironmentConfig(
            name="staging",
            is_production=False,
            require_confirmation=True,
        ),
        "production": EnvironmentConfig(
            name="production",
            is_production=True,
            require_confirmation=True,
        ),
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the environment manager.

        Args:
            config_path: Path to environment configuration file
        """
        self.config_path = config_path
        self._environments: Dict[str, EnvironmentConfig] = {}
        self._current_environment: Optional[str] = None

        # Load default environments
        self._load_defaults()

        # Load custom configuration if provided
        if config_path:
            self._load_config(config_path)

        # Detect current environment
        self._detect_environment()

    def _load_defaults(self) -> None:
        """Load default environment configurations."""
        self._environments = self.DEFAULT_ENVIRONMENTS.copy()

    def _load_config(self, config_path: str) -> None:
        """
        Load environment configuration from file.

        Args:
            config_path: Path to configuration file
        """
        # This would typically load from YAML/JSON/TOML
        # For now, we'll keep it simple
        logger.info(f"Loading environment config from {config_path}")

    def _detect_environment(self) -> None:
        """Detect the current environment from environment variables."""
        # Check common environment variable names
        env_vars = [
            "ENVIRONMENT",
            "ENV",
            "APP_ENV",
            "FLASK_ENV",
            "DJANGO_ENV",
            "NODE_ENV",
            "PYTHON_ENV",
        ]

        for var in env_vars:
            env_value = os.environ.get(var)
            if env_value:
                self._current_environment = env_value.lower()
                logger.info(f"Detected environment: {self._current_environment} (from {var})")
                break

        # Default to development if not detected
        if not self._current_environment:
            self._current_environment = "development"
            logger.info("No environment detected, defaulting to: development")

    @property
    def current_environment(self) -> str:
        """Get the current environment name."""
        return self._current_environment or "development"

    @current_environment.setter
    def current_environment(self, value: str) -> None:
        """Set the current environment."""
        if value not in self._environments:
            logger.warning(f"Unknown environment: {value}, creating default config")
            self._environments[value] = EnvironmentConfig(name=value)

        self._current_environment = value
        logger.info(f"Environment set to: {value}")

    def get_config(self, environment: Optional[str] = None) -> EnvironmentConfig:
        """
        Get configuration for an environment.

        Args:
            environment: Environment name (defaults to current)

        Returns:
            Environment configuration
        """
        env = environment or self.current_environment

        if env not in self._environments:
            logger.warning(f"Environment {env} not configured, using defaults")
            return EnvironmentConfig(name=env)

        return self._environments[env]

    def register_environment(self, config: EnvironmentConfig) -> None:
        """
        Register a new environment configuration.

        Args:
            config: Environment configuration
        """
        self._environments[config.name] = config
        logger.info(f"Registered environment: {config.name}")

    def is_production(self, environment: Optional[str] = None) -> bool:
        """
        Check if an environment is production.

        Args:
            environment: Environment name (defaults to current)

        Returns:
            True if production environment
        """
        config = self.get_config(environment)
        return config.is_production

    def requires_confirmation(self, environment: Optional[str] = None) -> bool:
        """
        Check if an environment requires confirmation for operations.

        Args:
            environment: Environment name (defaults to current)

        Returns:
            True if confirmation required
        """
        config = self.get_config(environment)
        return config.require_confirmation

    def get_database_url(self, environment: Optional[str] = None) -> Optional[str]:
        """
        Get database URL for an environment.

        Args:
            environment: Environment name (defaults to current)

        Returns:
            Database URL or None
        """
        config = self.get_config(environment)

        # Try configuration first
        if config.database_url:
            return config.database_url

        # Try environment variables
        env_var_names = [
            "DATABASE_URL",
            f"{environment.upper()}_DATABASE_URL" if environment else None,
            "SQLALCHEMY_DATABASE_URI",
        ]

        for var_name in env_var_names:
            if var_name:
                url = os.environ.get(var_name)
                if url:
                    return url

        return None

    def get_seeders_path(self, environment: Optional[str] = None) -> str:
        """
        Get the seeders directory path for an environment.

        Args:
            environment: Environment name (defaults to current)

        Returns:
            Path to seeders directory
        """
        config = self.get_config(environment)
        return config.seeders_path

    def should_run_seeder(self, seeder_name: str, environment: Optional[str] = None) -> bool:
        """
        Check if a seeder should run in an environment based on allow/exclude lists.

        Args:
            seeder_name: Name of the seeder
            environment: Environment name (defaults to current)

        Returns:
            True if seeder should run
        """
        config = self.get_config(environment)

        # Check excluded list first
        if config.excluded_seeders and seeder_name in config.excluded_seeders:
            return False

        # Check allowed list if specified
        if config.allowed_seeders:
            return seeder_name in config.allowed_seeders

        # Default to allowing if no restrictions
        return True

    def get_variable(self, key: str, environment: Optional[str] = None, default: Any = None) -> Any:
        """
        Get an environment-specific variable.

        Args:
            key: Variable key
            environment: Environment name (defaults to current)
            default: Default value if not found

        Returns:
            Variable value or default
        """
        config = self.get_config(environment)
        return config.variables.get(key, default)

    def set_variable(self, key: str, value: Any, environment: Optional[str] = None) -> None:
        """
        Set an environment-specific variable.

        Args:
            key: Variable key
            value: Variable value
            environment: Environment name (defaults to current)
        """
        config = self.get_config(environment)
        config.variables[key] = value

    def list_environments(self) -> List[str]:
        """
        List all registered environments.

        Returns:
            List of environment names
        """
        return list(self._environments.keys())

    def validate_environment(self, environment: str) -> bool:
        """
        Validate that an environment is properly configured.

        Args:
            environment: Environment name

        Returns:
            True if valid, False otherwise
        """
        if environment not in self._environments:
            return False

        self._environments[environment]

        # Check for database connection if needed
        if not self.get_database_url(environment):
            logger.warning(f"No database URL configured for environment: {environment}")

        return True

    def get_environment_info(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed information about an environment.

        Args:
            environment: Environment name (defaults to current)

        Returns:
            Dictionary with environment information
        """
        config = self.get_config(environment)

        return {
            "name": config.name,
            "is_production": config.is_production,
            "requires_confirmation": config.require_confirmation,
            "seeders_path": config.seeders_path,
            "auto_discover": config.auto_discover,
            "has_database_url": bool(self.get_database_url(config.name)),
            "allowed_seeders_count": len(config.allowed_seeders),
            "excluded_seeders_count": len(config.excluded_seeders),
            "variables_count": len(config.variables),
        }
