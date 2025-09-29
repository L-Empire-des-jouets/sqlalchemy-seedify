"""
Alembic Seeder - A comprehensive seeder system for Alembic and SQLAlchemy.

This package provides a Laravel-like seeder system for Python applications
using SQLAlchemy and Alembic for database management.
"""

from src.sqlalchemy_seedify.core.base_seeder import BaseSeeder
from src.sqlalchemy_seedify.core.seeder_manager import SeederManager
from src.sqlalchemy_seedify.core.seeder_registry import SeederRegistry
from src.sqlalchemy_seedify.core.upsert_manager import UpsertManager
from src.sqlalchemy_seedify.tracking.tracker import SeederTracker
from src.sqlalchemy_seedify.utils.environment import EnvironmentManager

__version__ = "1.1.0"

__all__ = [
    "BaseSeeder",
    "SeederManager",
    "SeederRegistry",
    "SeederTracker",
    "EnvironmentManager",
    "UpsertManager",
]
