"""
Database models for seeder tracking.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class SeederRecord(Base):
    """
    Model for tracking executed seeders.
    
    This table keeps track of which seeders have been executed,
    when they were executed, and in which environment.
    """
    
    __tablename__ = "alembic_seeder_history"
    __table_args__ = (
        UniqueConstraint("seeder_name", "environment", name="uq_seeder_env"),
    )
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    seeder_name = Column(String(255), nullable=False, index=True)
    environment = Column(String(50), nullable=False, index=True)
    batch = Column(Integer, nullable=False, index=True)
    executed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    execution_time = Column(Integer, nullable=True)  # in milliseconds
    records_affected = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="completed")
    error_message = Column(Text, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON string for additional metadata
    
    def __repr__(self) -> str:
        return (
            f"<SeederRecord(name={self.seeder_name}, "
            f"env={self.environment}, batch={self.batch})>"
        )