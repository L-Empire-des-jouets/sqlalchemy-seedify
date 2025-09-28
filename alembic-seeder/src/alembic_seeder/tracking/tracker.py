"""
Tracker for managing seeder execution history.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from alembic_seeder.tracking.models import SeederRecord

logger = logging.getLogger(__name__)


class SeederTracker:
    """
    Tracks the execution history of seeders.
    
    This class manages the database table that keeps track of which
    seeders have been executed, when, and in which environment.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the seeder tracker.
        
        Args:
            session: SQLAlchemy session
        """
        self.session = session
        self._ensure_tracking_table()
    
    def _ensure_tracking_table(self) -> None:
        """Ensure the tracking table exists."""
        # This would typically be handled by a migration, but we provide
        # a method to create it programmatically if needed
        try:
            from alembic_seeder.tracking.models import Base
            Base.metadata.create_all(bind=self.session.bind, checkfirst=True)
        except Exception as e:
            logger.warning(f"Could not ensure tracking table exists: {e}")
    
    def mark_executed(
        self,
        seeder_name: str,
        environment: str,
        batch: int,
        execution_time: Optional[int] = None,
        records_affected: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        content_hash: Optional[str] = None,
    ) -> SeederRecord:
        """
        Mark a seeder as executed.
        
        Args:
            seeder_name: Name of the seeder
            environment: Environment it was executed in
            batch: Batch number
            execution_time: Execution time in milliseconds
            records_affected: Number of records affected
            metadata: Additional metadata to store
            
        Returns:
            The created SeederRecord
        """
        try:
            record = SeederRecord(
                seeder_name=seeder_name,
                environment=environment,
                batch=batch,
                executed_at=datetime.utcnow(),
                execution_time=execution_time,
                records_affected=records_affected,
                status="completed",
                metadata_json=json.dumps(metadata) if metadata else None,
                content_hash=content_hash,
            )
            
            self.session.add(record)
            self.session.flush()
            
            logger.info(
                f"Marked seeder {seeder_name} as executed "
                f"in environment {environment} (batch {batch})"
            )
            
            return record
            
        except IntegrityError:
            self.session.rollback()
            # Update existing record
            existing = self.get_record(seeder_name, environment)
            if existing:
                existing.batch = batch
                existing.executed_at = datetime.utcnow()
                existing.execution_time = execution_time
                existing.records_affected = records_affected
                existing.status = "completed"
                existing.error_message = None
                existing.metadata_json = json.dumps(metadata) if metadata else None
                if content_hash:
                    existing.content_hash = content_hash
                self.session.flush()
                return existing
            raise
    
    def mark_failed(
        self,
        seeder_name: str,
        environment: str,
        batch: int,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SeederRecord:
        """
        Mark a seeder as failed.
        
        Args:
            seeder_name: Name of the seeder
            environment: Environment it failed in
            batch: Batch number
            error_message: Error message
            metadata: Additional metadata
            
        Returns:
            The created SeederRecord
        """
        record = SeederRecord(
            seeder_name=seeder_name,
            environment=environment,
            batch=batch,
            executed_at=datetime.utcnow(),
            status="failed",
            error_message=error_message,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        
        self.session.add(record)
        self.session.flush()
        
        logger.error(
            f"Marked seeder {seeder_name} as failed "
            f"in environment {environment}: {error_message}"
        )
        
        return record
    
    def mark_rolled_back(self, seeder_name: str) -> None:
        """
        Mark a seeder as rolled back.
        
        Args:
            seeder_name: Name of the seeder
        """
        records = (
            self.session.query(SeederRecord)
            .filter_by(seeder_name=seeder_name)
            .all()
        )
        
        for record in records:
            self.session.delete(record)
        
        self.session.flush()
        logger.info(f"Marked seeder {seeder_name} as rolled back")
    
    def is_executed(self, seeder_name: str, environment: str) -> bool:
        """
        Check if a seeder has been executed in an environment.
        
        Args:
            seeder_name: Name of the seeder
            environment: Environment to check
            
        Returns:
            True if executed, False otherwise
        """
        record = self.get_record(seeder_name, environment)
        return record is not None and record.status == "completed"

    def is_up_to_date(
        self, seeder_name: str, environment: str, current_hash: Optional[str]
    ) -> bool:
        """
        Check if a seeder has been executed and matches the current content hash.

        Returns False if no record or hashes mismatch (or unknown current hash).
        """
        record = self.get_record(seeder_name, environment)
        if not record or record.status != "completed":
            return False
        if current_hash is None:
            return False
        return (record.content_hash or "") == current_hash
    
    def get_record(
        self, seeder_name: str, environment: str
    ) -> Optional[SeederRecord]:
        """
        Get the execution record for a seeder.
        
        Args:
            seeder_name: Name of the seeder
            environment: Environment
            
        Returns:
            The SeederRecord or None
        """
        return (
            self.session.query(SeederRecord)
            .filter_by(seeder_name=seeder_name, environment=environment)
            .first()
        )
    
    def get_executed_seeders(
        self, environment: Optional[str] = None
    ) -> List[SeederRecord]:
        """
        Get all executed seeders.
        
        Args:
            environment: Filter by environment (optional)
            
        Returns:
            List of SeederRecords
        """
        query = self.session.query(SeederRecord).filter_by(status="completed")
        
        if environment:
            query = query.filter_by(environment=environment)
        
        return query.order_by(SeederRecord.batch, SeederRecord.executed_at).all()
    
    def get_pending_seeders(
        self, all_seeders: List[str], environment: str
    ) -> List[str]:
        """
        Get seeders that haven't been executed yet.
        
        Args:
            all_seeders: List of all available seeders
            environment: Environment to check
            
        Returns:
            List of pending seeder names
        """
        executed = (
            self.session.query(SeederRecord.seeder_name)
            .filter_by(environment=environment, status="completed")
            .all()
        )
        
        executed_names = {record[0] for record in executed}
        return [name for name in all_seeders if name not in executed_names]
    
    def get_last_batch(self, count: int = 1) -> List[SeederRecord]:
        """
        Get seeders from the last N batches.
        
        Args:
            count: Number of batches to retrieve
            
        Returns:
            List of SeederRecords
        """
        # Get the last N batch numbers
        batch_numbers = (
            self.session.query(SeederRecord.batch)
            .distinct()
            .order_by(desc(SeederRecord.batch))
            .limit(count)
            .all()
        )
        
        if not batch_numbers:
            return []
        
        batch_numbers = [b[0] for b in batch_numbers]
        
        return (
            self.session.query(SeederRecord)
            .filter(SeederRecord.batch.in_(batch_numbers))
            .order_by(desc(SeederRecord.batch), desc(SeederRecord.executed_at))
            .all()
        )
    
    def get_next_batch(self) -> int:
        """
        Get the next batch number.
        
        Returns:
            The next batch number
        """
        max_batch = (
            self.session.query(func.max(SeederRecord.batch)).scalar() or 0
        )
        return max_batch + 1
    
    def get_statistics(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Args:
            environment: Filter by environment (optional)
            
        Returns:
            Dictionary with statistics
        """
        query = self.session.query(SeederRecord)
        
        if environment:
            query = query.filter_by(environment=environment)
        
        total = query.count()
        completed = query.filter_by(status="completed").count()
        failed = query.filter_by(status="failed").count()
        
        # Get average execution time
        avg_time = (
            self.session.query(func.avg(SeederRecord.execution_time))
            .filter_by(status="completed")
            .scalar()
        )
        
        # Get total records affected
        total_records = (
            self.session.query(func.sum(SeederRecord.records_affected))
            .filter_by(status="completed")
            .scalar()
        )
        
        return {
            "total_executions": total,
            "completed": completed,
            "failed": failed,
            "average_execution_time_ms": avg_time,
            "total_records_affected": total_records or 0,
            "environments": self._get_environment_stats(),
        }
    
    def _get_environment_stats(self) -> Dict[str, Dict[str, int]]:
        """Get statistics per environment."""
        results = (
            self.session.query(
                SeederRecord.environment,
                SeederRecord.status,
                func.count(SeederRecord.id),
            )
            .group_by(SeederRecord.environment, SeederRecord.status)
            .all()
        )
        
        stats = {}
        for env, status, count in results:
            if env not in stats:
                stats[env] = {"completed": 0, "failed": 0}
            stats[env][status] = count
        
        return stats
    
    def clear_history(
        self, environment: Optional[str] = None, force: bool = False
    ) -> int:
        """
        Clear execution history.
        
        Args:
            environment: Clear only for specific environment
            force: Force clear without confirmation
            
        Returns:
            Number of records deleted
        """
        if not force:
            logger.warning(
                "Clearing history requires force=True to prevent accidental deletion"
            )
            return 0
        
        query = self.session.query(SeederRecord)
        
        if environment:
            query = query.filter_by(environment=environment)
        
        count = query.count()
        query.delete()
        self.session.flush()
        
        logger.info(f"Cleared {count} seeder history records")
        return count