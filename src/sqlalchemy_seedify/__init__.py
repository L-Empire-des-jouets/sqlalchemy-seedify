"""
Alembic Seeder - A comprehensive seeder system for Alembic and SQLAlchemy.

This package provides a Laravel-like seeder system for Python applications
using SQLAlchemy and Alembic for database management.
"""

from sqlalchemy_seedify.core.base_seeder import BaseSeeder
from sqlalchemy_seedify.core.seeder_manager import SeederManager
from sqlalchemy_seedify.core.seeder_registry import SeederRegistry
from sqlalchemy_seedify.core.upsert_manager import UpsertManager
from sqlalchemy_seedify.tracking.tracker import SeederTracker
from sqlalchemy_seedify.utils.environment import EnvironmentManager

__version__ = "1.1.0"

__all__ = [
    "BaseSeeder",
    "SeederManager",
    "SeederRegistry",
    "SeederTracker",
    "EnvironmentManager",
    "UpsertManager",
]
