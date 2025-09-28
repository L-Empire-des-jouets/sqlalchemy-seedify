"""
Manager for orchestrating seeder execution.
"""

import logging
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Type
from datetime import datetime

from sqlalchemy.orm import Session
from pydantic import BaseModel

from alembic_seeder.core.base_seeder import BaseSeeder
from alembic_seeder.core.seeder_registry import SeederRegistry
from alembic_seeder.tracking.tracker import SeederTracker
from alembic_seeder.tracking.hash import compute_seeder_content_hash
from alembic_seeder.utils.environment import EnvironmentManager

logger = logging.getLogger(__name__)


class SeederExecutionPlan(BaseModel):
    """Execution plan for seeders."""
    
    seeders: List[str]
    environment: str
    force: bool = False
    dry_run: bool = False
    parallel: bool = False
    batch_size: Optional[int] = None


class SeederExecutionResult(BaseModel):
    """Result of seeder execution."""
    
    total: int
    successful: int
    failed: int
    skipped: int
    duration: float
    results: List[Dict[str, Any]]
    errors: List[str]


class SeederManager:
    """
    Manager for orchestrating the execution of seeders.
    
    This class handles dependency resolution, execution order,
    tracking, and environment-specific execution.
    """
    
    def __init__(
        self,
        session: Session,
        registry: Optional[SeederRegistry] = None,
        tracker: Optional[SeederTracker] = None,
        environment_manager: Optional[EnvironmentManager] = None,
    ):
        """
        Initialize the seeder manager.
        
        Args:
            session: SQLAlchemy session
            registry: Seeder registry instance
            tracker: Seeder tracker instance
            environment_manager: Environment manager instance
        """
        self.session = session
        self.registry = registry or SeederRegistry()
        self.tracker = tracker or SeederTracker(session)
        self.env_manager = environment_manager or EnvironmentManager()
        
    def run_all(
        self,
        environment: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False,
        tags: Optional[List[str]] = None,
    ) -> SeederExecutionResult:
        """
        Run all seeders for the current environment.
        
        Args:
            environment: Environment to run seeders for (defaults to current)
            force: Force re-run even if already executed
            dry_run: Perform a dry run without actually executing
            tags: Only run seeders with these tags
            
        Returns:
            Execution result with statistics
        """
        environment = environment or self.env_manager.current_environment
        logger.info(f"Running all seeders for environment: {environment}")
        
        # Get seeders for environment
        seeders = self.registry.get_by_environment(environment)
        
        # Filter by tags if provided
        if tags:
            seeders = {
                name: cls
                for name, cls in seeders.items()
                if any(tag in cls._get_metadata().tags for tag in tags)
            }
        
        # Build execution plan
        seeder_names = list(seeders.keys())
        execution_order = self._resolve_dependencies(seeder_names)
        
        # Execute seeders
        return self._execute_seeders(
            execution_order, environment, force, dry_run
        )
    
    def run_specific(
        self,
        seeder_names: List[str],
        environment: Optional[str] = None,
        force: bool = False,
        dry_run: bool = False,
        with_dependencies: bool = True,
    ) -> SeederExecutionResult:
        """
        Run specific seeders.
        
        Args:
            seeder_names: Names of seeders to run
            environment: Environment to run seeders for
            force: Force re-run even if already executed
            dry_run: Perform a dry run
            with_dependencies: Include dependencies in execution
            
        Returns:
            Execution result with statistics
        """
        environment = environment or self.env_manager.current_environment
        logger.info(f"Running specific seeders: {seeder_names}")
        
        # Validate seeders exist
        for name in seeder_names:
            if name not in self.registry:
                raise ValueError(f"Seeder not found: {name}")
        
        # Resolve dependencies if needed
        if with_dependencies:
            execution_order = self._resolve_dependencies(seeder_names)
        else:
            execution_order = seeder_names
        
        # Execute seeders
        return self._execute_seeders(
            execution_order, environment, force, dry_run
        )
    
    def rollback(
        self,
        seeder_names: Optional[List[str]] = None,
        all_seeders: bool = False,
        batch: Optional[int] = None,
        dry_run: bool = False,
    ) -> SeederExecutionResult:
        """
        Rollback seeders.
        
        Args:
            seeder_names: Specific seeders to rollback
            all_seeders: Rollback all executed seeders
            batch: Rollback last N batches
            dry_run: Perform a dry run
            
        Returns:
            Rollback result with statistics
        """
        if all_seeders:
            executed = self.tracker.get_executed_seeders()
            seeder_names = [record.seeder_name for record in executed]
        elif batch:
            executed = self.tracker.get_last_batch(batch)
            seeder_names = [record.seeder_name for record in executed]
        elif not seeder_names:
            raise ValueError("Must specify seeders to rollback or use --all/--batch")
        
        # Reverse order for rollback
        seeder_names = list(reversed(seeder_names))
        
        # Execute rollbacks
        results = []
        errors = []
        successful = 0
        failed = 0
        skipped = 0
        start_time = datetime.utcnow()
        
        for name in seeder_names:
            seeder_class = self.registry.get(name)
            if not seeder_class:
                logger.warning(f"Seeder not found: {name}")
                skipped += 1
                continue
            
            if not seeder_class._get_metadata().can_rollback:
                logger.warning(f"Seeder {name} does not support rollback")
                skipped += 1
                continue
            
            if dry_run:
                logger.info(f"[DRY RUN] Would rollback: {name}")
                successful += 1
                continue
            
            try:
                seeder = seeder_class(self.session)
                result = seeder.execute_rollback()
                results.append(result)
                
                if result["status"] == "success":
                    successful += 1
                    self.tracker.mark_rolled_back(name)
                else:
                    failed += 1
                    errors.append(result.get("error", "Unknown error"))
                    
            except Exception as e:
                failed += 1
                errors.append(str(e))
                logger.error(f"Error rolling back {name}: {e}")
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        return SeederExecutionResult(
            total=len(seeder_names),
            successful=successful,
            failed=failed,
            skipped=skipped,
            duration=duration,
            results=results,
            errors=errors,
        )
    
    def refresh(
        self,
        environment: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, SeederExecutionResult]:
        """
        Refresh all seeders (rollback then re-run).
        
        Args:
            environment: Environment to refresh
            dry_run: Perform a dry run
            
        Returns:
            Dictionary with rollback and run results
        """
        environment = environment or self.env_manager.current_environment
        
        # First rollback all
        rollback_result = self.rollback(all_seeders=True, dry_run=dry_run)
        
        # Then run all
        run_result = self.run_all(
            environment=environment, force=True, dry_run=dry_run
        )
        
        return {
            "rollback": rollback_result,
            "run": run_result,
        }
    
    def status(self, detailed: bool = False) -> Dict[str, Any]:
        """
        Get the status of seeders.
        
        Args:
            detailed: Include detailed information
            
        Returns:
            Status information
        """
        all_seeders = self.registry.get_all()
        executed = self.tracker.get_executed_seeders()
        executed_names = {record.seeder_name for record in executed}
        
        pending = []
        completed = []
        
        for name in all_seeders:
            if name in executed_names:
                completed.append(name)
            else:
                pending.append(name)
        
        status = {
            "total": len(all_seeders),
            "executed": len(completed),
            "pending": len(pending),
            "completed": completed,
            "pending_list": pending,
        }
        
        # Detect changed seeders based on content hash
        changed = []
        for record in executed:
            seeder_class = self.registry.get(record.seeder_name)
            if not seeder_class:
                # Seeder no longer present; consider changed
                changed.append(record.seeder_name)
                continue
            try:
                current_hash = compute_seeder_content_hash(seeder_class)
                if (record.content_hash or "") != (current_hash or ""):
                    changed.append(record.seeder_name)
            except Exception:
                # If we cannot compute, consider potentially changed
                changed.append(record.seeder_name)

        status["changed"] = len(changed)
        status["changed_list"] = sorted(set(changed))

        if detailed:
            status["execution_history"] = [
                {
                    "name": record.seeder_name,
                    "executed_at": record.executed_at,
                    "environment": record.environment,
                    "batch": record.batch,
                    "content_hash": getattr(record, "content_hash", None),
                }
                for record in executed
            ]
        
        return status
    
    def _resolve_dependencies(self, seeder_names: List[str]) -> List[str]:
        """
        Resolve dependencies and determine execution order.
        
        Uses topological sorting to resolve dependencies.
        
        Args:
            seeder_names: Initial list of seeder names
            
        Returns:
            Ordered list of seeder names
        """
        # Build dependency graph
        graph = defaultdict(set)
        in_degree = defaultdict(int)
        all_seeders = set(seeder_names)
        
        # Process each seeder and its dependencies
        to_process = deque(seeder_names)
        processed = set()
        
        while to_process:
            name = to_process.popleft()
            if name in processed:
                continue
            processed.add(name)
            
            seeder_class = self.registry.get(name)
            if not seeder_class:
                continue
            
            metadata = seeder_class._get_metadata()
            for dep in metadata.dependencies:
                graph[dep].add(name)
                in_degree[name] += 1
                all_seeders.add(dep)
                if dep not in processed:
                    to_process.append(dep)
        
        # Topological sort
        queue = deque([s for s in all_seeders if in_degree[s] == 0])
        result = []
        
        while queue:
            # Sort by priority for deterministic order
            current_batch = []
            batch_size = len(queue)
            
            for _ in range(batch_size):
                current_batch.append(queue.popleft())
            
            # Sort batch by priority
            current_batch.sort(
                key=lambda x: self.registry.get(x)._get_metadata().priority
                if self.registry.get(x)
                else float("inf")
            )
            
            for seeder in current_batch:
                result.append(seeder)
                for dependent in graph[seeder]:
                    in_degree[dependent] -= 1
                    if in_degree[dependent] == 0:
                        queue.append(dependent)
        
        # Check for cycles
        if len(result) != len(all_seeders):
            missing = all_seeders - set(result)
            raise ValueError(f"Circular dependency detected involving: {missing}")
        
        return result
    
    def _execute_seeders(
        self,
        seeder_names: List[str],
        environment: str,
        force: bool,
        dry_run: bool,
    ) -> SeederExecutionResult:
        """
        Execute a list of seeders in order.
        
        Args:
            seeder_names: Ordered list of seeder names
            environment: Environment to execute in
            force: Force re-run
            dry_run: Perform dry run
            
        Returns:
            Execution result
        """
        results = []
        errors = []
        successful = 0
        failed = 0
        skipped = 0
        start_time = datetime.utcnow()
        batch_number = self.tracker.get_next_batch()
        
        for name in seeder_names:
            # Check if already executed
            seeder_class = self.registry.get(name)
            if not seeder_class:
                logger.warning(f"Seeder not found: {name}")
                skipped += 1
                continue

            current_hash = None
            try:
                current_hash = compute_seeder_content_hash(seeder_class)
            except Exception as e:
                logger.debug(f"Could not compute content hash for {name}: {e}")

            if not force:
                # If executed and hash matches, skip
                if self.tracker.is_up_to_date(name, environment, current_hash):
                    logger.info(f"Skipping up-to-date seeder: {name}")
                    skipped += 1
                    continue
            
            # Check environment
            metadata = seeder_class._get_metadata()
            if not ("all" in metadata.environments or environment in metadata.environments):
                logger.info(f"Skipping seeder {name} (not for environment {environment})")
                skipped += 1
                continue
            
            # Dry run
            if dry_run:
                logger.info(f"[DRY RUN] Would execute: {name}")
                successful += 1
                continue
            
            # Execute seeder
            try:
                seeder = seeder_class(self.session)
                result = seeder.execute()
                results.append(result)
                
                if result["status"] == "success":
                    successful += 1
                    self.tracker.mark_executed(
                        name,
                        environment,
                        batch_number,
                        execution_time=int(result.get("duration", 0) * 1000),
                        records_affected=result.get("records_affected"),
                        metadata={"description": metadata.description},
                        content_hash=current_hash,
                    )
                    self.session.commit()
                else:
                    failed += 1
                    errors.append(result.get("error", "Unknown error"))
                    self.session.rollback()
                    
            except Exception as e:
                failed += 1
                errors.append(str(e))
                logger.error(f"Error executing seeder {name}: {e}")
                self.session.rollback()
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        return SeederExecutionResult(
            total=len(seeder_names),
            successful=successful,
            failed=failed,
            skipped=skipped,
            duration=duration,
            results=results,
            errors=errors,
        )