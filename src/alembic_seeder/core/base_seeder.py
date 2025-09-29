"""
Base seeder class that all seeders must inherit from.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SeederMetadata(BaseModel):
    """Metadata for a seeder."""

    name: str
    description: Optional[str] = None
    environments: List[str] = Field(default_factory=lambda: ["all"])
    dependencies: List[str] = Field(default_factory=list)
    priority: int = 100
    batch_size: int = 1000
    can_rollback: bool = False
    tags: List[str] = Field(default_factory=list)


class BaseSeeder(ABC):
    """
    Abstract base class for all seeders.

    This class provides the interface that all seeders must implement,
    similar to Laravel's seeder system.
    """

    def __init__(self, session: Optional[Session] = None):
        """
        Initialize the seeder.

        Args:
            session: SQLAlchemy session to use for database operations
        """
        self.session = session
        self._metadata = self._get_metadata()
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._records_affected = 0

    @classmethod
    def _get_metadata(cls) -> SeederMetadata:
        """
        Get metadata for this seeder.

        Override this method to provide custom metadata.
        """
        return SeederMetadata(
            name=cls.__name__,
            description=cls.__doc__,
        )

    @property
    def name(self) -> str:
        """Get the seeder name."""
        return self._metadata.name

    @property
    def description(self) -> Optional[str]:
        """Get the seeder description."""
        return self._metadata.description

    @property
    def environments(self) -> List[str]:
        """Get the environments this seeder should run in."""
        return self._metadata.environments

    @property
    def dependencies(self) -> List[str]:
        """Get the list of seeder dependencies."""
        return self._metadata.dependencies

    @property
    def priority(self) -> int:
        """Get the seeder priority (lower runs first)."""
        return self._metadata.priority

    @property
    def can_rollback(self) -> bool:
        """Check if this seeder supports rollback."""
        return self._metadata.can_rollback

    @abstractmethod
    def run(self) -> None:
        """
        Execute the seeder.

        This method must be implemented by all seeders and should contain
        the logic to insert data into the database.
        """
        pass

    def rollback(self) -> None:
        """
        Rollback the seeder.

        Override this method if your seeder supports rollback.
        This should remove or revert the data inserted by the run method.
        """
        if not self.can_rollback:
            raise NotImplementedError(
                f"Seeder {self.name} does not support rollback. "
                "Override the rollback method and set can_rollback=True in metadata."
            )

    def before_run(self) -> None:
        """
        Hook called before the seeder runs.

        Override this method to add custom logic before seeding.
        """
        self._start_time = datetime.utcnow()
        logger.info(f"Starting seeder: {self.name}")

    def after_run(self) -> None:
        """
        Hook called after the seeder runs.

        Override this method to add custom logic after seeding.
        """
        self._end_time = datetime.utcnow()
        duration = (self._end_time - self._start_time).total_seconds()
        logger.info(
            f"Completed seeder: {self.name} "
            f"(Duration: {duration:.2f}s, Records: {self._records_affected})"
        )

    def before_rollback(self) -> None:
        """
        Hook called before the seeder rollback.

        Override this method to add custom logic before rollback.
        """
        logger.info(f"Starting rollback for seeder: {self.name}")

    def after_rollback(self) -> None:
        """
        Hook called after the seeder rollback.

        Override this method to add custom logic after rollback.
        """
        logger.info(f"Completed rollback for seeder: {self.name}")

    def should_run(self, environment: str) -> bool:
        """
        Check if this seeder should run in the given environment.

        Args:
            environment: The current environment (dev, test, prod, etc.)

        Returns:
            True if the seeder should run, False otherwise
        """
        return "all" in self.environments or environment in self.environments

    def validate(self) -> bool:
        """
        Validate the seeder before running.

        Override this method to add custom validation logic.

        Returns:
            True if validation passes, False otherwise
        """
        return True

    def call(self, seeder_class: Type["BaseSeeder"]) -> None:
        """
        Call another seeder from within this seeder.

        This allows for nested seeder execution, similar to Laravel.

        Args:
            seeder_class: The seeder class to execute
        """
        if self.session:
            seeder = seeder_class(self.session)
            seeder.execute()

    def execute(self) -> Dict[str, Any]:
        """
        Execute the complete seeder lifecycle.

        Returns:
            Execution statistics and metadata
        """
        try:
            # Validation
            if not self.validate():
                raise ValueError(f"Seeder {self.name} validation failed")

            # Pre-run hook
            self.before_run()

            # Main execution
            self.run()

            # Post-run hook
            self.after_run()

            # Return execution stats
            return {
                "name": self.name,
                "status": "success",
                "start_time": self._start_time,
                "end_time": self._end_time,
                "duration": (self._end_time - self._start_time).total_seconds()
                if self._start_time and self._end_time
                else 0,
                "records_affected": self._records_affected,
            }

        except Exception as e:
            logger.error(f"Error executing seeder {self.name}: {str(e)}")
            return {
                "name": self.name,
                "status": "error",
                "error": str(e),
                "start_time": self._start_time,
                "end_time": datetime.utcnow(),
            }

    def execute_rollback(self) -> Dict[str, Any]:
        """
        Execute the complete rollback lifecycle.

        Returns:
            Rollback statistics and metadata
        """
        try:
            # Check if rollback is supported
            if not self.can_rollback:
                raise NotImplementedError(f"Seeder {self.name} does not support rollback")

            # Pre-rollback hook
            self.before_rollback()

            # Main rollback
            self.rollback()

            # Post-rollback hook
            self.after_rollback()

            return {
                "name": self.name,
                "status": "success",
                "action": "rollback",
            }

        except Exception as e:
            logger.error(f"Error rolling back seeder {self.name}: {str(e)}")
            return {
                "name": self.name,
                "status": "error",
                "action": "rollback",
                "error": str(e),
            }

    # ----------------------------
    # Idempotent helper methods
    # ----------------------------
    def get_or_create(
        self,
        model: Type[Any],
        where: Dict[str, Any],
        defaults: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Retrieve an existing instance by unique filters or create it if missing.

        Returns a dict with keys: action ("created"|"found"), instance.
        Increments records_affected when a new row is created.
        """
        if self.session is None:
            raise RuntimeError("Session is required for get_or_create")

        from alembic_seeder.core.upsert_manager import UpsertManager

        manager = UpsertManager(self.session)
        instance, created = manager.get_or_create(model, where, defaults)
        if created:
            self._records_affected += 1
            return {"action": "created", "instance": instance}
        return {"action": "found", "instance": instance}

    def upsert(
        self,
        model: Type[Any],
        where: Dict[str, Any],
        values: Dict[str, Any],
        update_existing: bool = True,
        count_update_as_affected: bool = True,
    ) -> Dict[str, Any]:
        """
        Insert a row if it doesn't exist, otherwise update it (idempotent).

        - where: fields identifying the unique row (business key)
        - values: fields to set on create/update (relationships allowed)
        - update_existing: when True, update existing rows with provided values
        - count_update_as_affected: when True, increments records_affected on update

        Returns dict with keys: action ("created"|"updated"|"unchanged"), instance.
        """
        if self.session is None:
            raise RuntimeError("Session is required for upsert")

        from alembic_seeder.core.upsert_manager import UpsertManager

        manager = UpsertManager(self.session)
        instance, action = manager.upsert(
            model=model,
            where=where,
            values=values,
            update_existing=update_existing,
        )
        if action == "created" or (action == "updated" and count_update_as_affected):
            self._records_affected += 1
        return {"action": action, "instance": instance}

    def bulk_upsert(
        self,
        model: Type[Any],
        rows: List[Dict[str, Any]],
        key_fields: List[str],
        update_fields: Optional[List[str]] = None,
        count_update_as_affected: bool = True,
    ) -> Dict[str, int]:
        """
        Idempotent bulk upsert based on business keys.

        - rows: list of dicts representing model fields
        - key_fields: list of fields forming a unique business key
        - update_fields: fields allowed to be updated; if None, updates all non-key fields

        Returns dict with counts: created, updated, unchanged.
        Increments records_affected by created + (updated if configured).
        """
        if self.session is None:
            raise RuntimeError("Session is required for bulk_upsert")

        if not rows:
            return {"created": 0, "updated": 0, "unchanged": 0}

        from alembic_seeder.core.upsert_manager import UpsertManager

        manager = UpsertManager(self.session)
        summary = manager.bulk_upsert(
            model=model,
            rows=rows,
            key_fields=key_fields,
            update_fields=update_fields,
        )
        # Track affected rows consistent with previous behavior
        self._records_affected += summary["created"]
        if count_update_as_affected:
            self._records_affected += summary["updated"]
        return summary
