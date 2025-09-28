"""
Example of integrating alembic-seeder with a FastAPI application.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from pydantic import BaseModel

from alembic_seeder import SeederManager, SeederRegistry, SeederTracker
from alembic_seeder.utils import Config, EnvironmentManager


# Configuration
config = Config()
env_manager = EnvironmentManager()

# Database setup
engine = create_engine(config.database_url or "sqlite:///./test.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Dependency for database sessions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic models for API
class SeederRunRequest(BaseModel):
    seeders: list[str] = []
    force: bool = False
    dry_run: bool = False
    environment: str = "development"


class SeederRollbackRequest(BaseModel):
    seeders: list[str] = []
    all_seeders: bool = False
    batch: int = None


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Manage application lifecycle.
    
    Can run seeders on startup if configured.
    """
    # Startup
    print("Starting application...")
    
    # Optionally run seeders on startup
    if config.get("auto_seed_on_startup", False):
        db = SessionLocal()
        try:
            registry = SeederRegistry(config.seeders_path)
            tracker = SeederTracker(db)
            manager = SeederManager(db, registry, tracker, env_manager)
            
            # Run seeders for current environment
            result = manager.run_all(environment=env_manager.current_environment)
            print(f"Seeding completed: {result.successful} successful, {result.failed} failed")
            
            db.commit()
        except Exception as e:
            print(f"Error running seeders on startup: {e}")
            db.rollback()
        finally:
            db.close()
    
    yield
    
    # Shutdown
    print("Shutting down application...")


# Create FastAPI app
app = FastAPI(
    title="Alembic Seeder API",
    description="API for managing database seeders",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": "Alembic Seeder API",
        "environment": env_manager.current_environment,
        "seeders_path": config.seeders_path,
    }


@app.get("/seeders")
def list_seeders(db: Session = Depends(get_db)):
    """List all available seeders."""
    registry = SeederRegistry(config.seeders_path)
    registry.discover()
    
    seeders = []
    for name, seeder_class in registry.get_all().items():
        metadata = seeder_class._get_metadata()
        seeders.append({
            "name": name,
            "description": metadata.description,
            "environments": metadata.environments,
            "dependencies": metadata.dependencies,
            "priority": metadata.priority,
            "can_rollback": metadata.can_rollback,
            "tags": metadata.tags,
        })
    
    return {"seeders": seeders, "total": len(seeders)}


@app.get("/seeders/status")
def get_status(detailed: bool = False, db: Session = Depends(get_db)):
    """Get seeder execution status."""
    registry = SeederRegistry(config.seeders_path)
    tracker = SeederTracker(db)
    manager = SeederManager(db, registry, tracker, env_manager)
    
    status = manager.status(detailed=detailed)
    
    return status


@app.post("/seeders/run")
def run_seeders(request: SeederRunRequest, db: Session = Depends(get_db)):
    """Run seeders."""
    # Set environment
    env_manager.current_environment = request.environment
    
    # Check production safety
    if env_manager.is_production() and not request.dry_run:
        if not config.get("allow_production_api_seeding", False):
            raise HTTPException(
                status_code=403,
                detail="Production seeding via API is disabled for safety"
            )
    
    registry = SeederRegistry(config.seeders_path)
    tracker = SeederTracker(db)
    manager = SeederManager(db, registry, tracker, env_manager)
    
    try:
        if request.seeders:
            result = manager.run_specific(
                request.seeders,
                environment=request.environment,
                force=request.force,
                dry_run=request.dry_run,
            )
        else:
            result = manager.run_all(
                environment=request.environment,
                force=request.force,
                dry_run=request.dry_run,
            )
        
        if not request.dry_run and result.failed == 0:
            db.commit()
        else:
            db.rollback()
        
        return {
            "success": result.failed == 0,
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "skipped": result.skipped,
            "duration": result.duration,
            "errors": result.errors,
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/seeders/rollback")
def rollback_seeders(request: SeederRollbackRequest, db: Session = Depends(get_db)):
    """Rollback seeders."""
    registry = SeederRegistry(config.seeders_path)
    tracker = SeederTracker(db)
    manager = SeederManager(db, registry, tracker, env_manager)
    
    try:
        result = manager.rollback(
            seeder_names=request.seeders if request.seeders else None,
            all_seeders=request.all_seeders,
            batch=request.batch,
            dry_run=False,
        )
        
        if result.failed == 0:
            db.commit()
        else:
            db.rollback()
        
        return {
            "success": result.failed == 0,
            "total": result.total,
            "successful": result.successful,
            "failed": result.failed,
            "skipped": result.skipped,
            "duration": result.duration,
            "errors": result.errors,
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/seeders/refresh")
def refresh_seeders(environment: str = "development", db: Session = Depends(get_db)):
    """Refresh all seeders (rollback then re-run)."""
    env_manager.current_environment = environment
    
    registry = SeederRegistry(config.seeders_path)
    tracker = SeederTracker(db)
    manager = SeederManager(db, registry, tracker, env_manager)
    
    try:
        results = manager.refresh(dry_run=False)
        
        db.commit()
        
        return {
            "success": True,
            "rollback": {
                "total": results["rollback"].total,
                "successful": results["rollback"].successful,
                "failed": results["rollback"].failed,
            },
            "run": {
                "total": results["run"].total,
                "successful": results["run"].successful,
                "failed": results["run"].failed,
            },
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/seeders/history")
def get_history(environment: str = None, db: Session = Depends(get_db)):
    """Get seeder execution history."""
    tracker = SeederTracker(db)
    
    executed = tracker.get_executed_seeders(environment=environment)
    
    history = []
    for record in executed:
        history.append({
            "seeder_name": record.seeder_name,
            "environment": record.environment,
            "batch": record.batch,
            "executed_at": record.executed_at.isoformat(),
            "execution_time": record.execution_time,
            "records_affected": record.records_affected,
            "status": record.status,
        })
    
    return {"history": history, "total": len(history)}


@app.get("/seeders/statistics")
def get_statistics(environment: str = None, db: Session = Depends(get_db)):
    """Get seeder execution statistics."""
    tracker = SeederTracker(db)
    
    stats = tracker.get_statistics(environment=environment)
    
    return stats


# Health check endpoint
@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
        "environment": env_manager.current_environment,
    }


# Example of using seeders in background tasks
from fastapi import BackgroundTasks


@app.post("/seeders/run-async")
def run_seeders_async(
    request: SeederRunRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Run seeders in the background."""
    
    def run_in_background():
        db_session = SessionLocal()
        try:
            registry = SeederRegistry(config.seeders_path)
            tracker = SeederTracker(db_session)
            manager = SeederManager(db_session, registry, tracker, env_manager)
            
            if request.seeders:
                result = manager.run_specific(
                    request.seeders,
                    environment=request.environment,
                    force=request.force,
                    dry_run=request.dry_run,
                )
            else:
                result = manager.run_all(
                    environment=request.environment,
                    force=request.force,
                    dry_run=request.dry_run,
                )
            
            if not request.dry_run and result.failed == 0:
                db_session.commit()
                print(f"Background seeding completed successfully")
            else:
                db_session.rollback()
                print(f"Background seeding failed with {result.failed} errors")
                
        except Exception as e:
            db_session.rollback()
            print(f"Error in background seeding: {e}")
        finally:
            db_session.close()
    
    background_tasks.add_task(run_in_background)
    
    return {
        "message": "Seeding started in background",
        "environment": request.environment,
        "seeders": request.seeders if request.seeders else "all",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)