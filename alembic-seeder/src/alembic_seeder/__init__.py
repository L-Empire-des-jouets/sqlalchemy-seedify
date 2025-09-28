"""
Alembic Seeder - A comprehensive seeder system for Alembic and SQLAlchemy.

This package provides a Laravel-like seeder system for Python applications
using SQLAlchemy and Alembic for database management.
"""

from alembic_seeder.core.base_seeder import BaseSeeder
from alembic_seeder.core.seeder_manager import SeederManager
from alembic_seeder.core.seeder_registry import SeederRegistry
from alembic_seeder.tracking.tracker import SeederTracker
from alembic_seeder.utils.environment import EnvironmentManager

__version__ = "1.0.0"

__all__ = [
    "BaseSeeder",
    "SeederManager",
    "SeederRegistry",
    "SeederTracker",
    "EnvironmentManager",
]