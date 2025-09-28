"""
Registry for discovering and managing seeders.
"""

import importlib
import inspect
import os
from pathlib import Path
from typing import Dict, List, Optional, Type
import logging

from alembic_seeder.core.base_seeder import BaseSeeder

logger = logging.getLogger(__name__)


class SeederRegistry:
    """
    Registry for discovering and managing seeder classes.
    
    This class automatically discovers seeder classes in a project
    and provides methods to access and manage them.
    """
    
    def __init__(self, seeders_path: Optional[str] = None):
        """
        Initialize the seeder registry.
        
        Args:
            seeders_path: Path to the directory containing seeder files
        """
        self.seeders_path = seeders_path or "seeders"
        self._seeders: Dict[str, Type[BaseSeeder]] = {}
        self._discovered = False
    
    def discover(self, force: bool = False) -> None:
        """
        Discover all seeder classes in the seeders directory.
        
        Args:
            force: Force re-discovery even if already discovered
        """
        if self._discovered and not force:
            return
        
        self._seeders.clear()
        seeders_dir = Path(self.seeders_path)
        
        if not seeders_dir.exists():
            logger.warning(f"Seeders directory not found: {seeders_dir}")
            return
        
        # Find all Python files in the seeders directory
        for file_path in seeders_dir.glob("**/*.py"):
            if file_path.name.startswith("_"):
                continue
            
            try:
                self._load_seeder_from_file(file_path)
            except Exception as e:
                logger.error(f"Error loading seeder from {file_path}: {e}")
        
        self._discovered = True
        logger.info(f"Discovered {len(self._seeders)} seeders")
    
    def _load_seeder_from_file(self, file_path: Path) -> None:
        """
        Load seeder classes from a Python file.
        
        Args:
            file_path: Path to the Python file
        """
        # Convert file path to module name; fall back to direct path import
        try:
            relative_path = file_path.relative_to(Path.cwd())
            module_path = str(relative_path.with_suffix("")).replace(os.sep, ".")
        except Exception:
            module_path = None
        
        # Import the module
        try:
            if module_path:
                module = importlib.import_module(module_path)
            else:
                # Load from absolute path (seeders outside sys.path)
                import importlib.util
                spec = importlib.util.spec_from_file_location(file_path.stem, str(file_path))
                if not spec or not spec.loader:
                    raise ImportError(f"Cannot load spec for {file_path}")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)  # type: ignore
        except ImportError as e:
            logger.error(f"Failed to import seeder module from {file_path}: {e}")
            return
        
        # Find all seeder classes in the module
        for name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseSeeder)
                and obj is not BaseSeeder
                and not inspect.isabstract(obj)
            ):
                self.register(obj)
    
    def register(self, seeder_class: Type[BaseSeeder]) -> None:
        """
        Register a seeder class.
        
        Args:
            seeder_class: The seeder class to register
        """
        name = seeder_class.__name__
        
        if name in self._seeders:
            logger.warning(f"Seeder {name} is already registered, overwriting")
        
        self._seeders[name] = seeder_class
        logger.debug(f"Registered seeder: {name}")
    
    def unregister(self, name: str) -> None:
        """
        Unregister a seeder by name.
        
        Args:
            name: Name of the seeder to unregister
        """
        if name in self._seeders:
            del self._seeders[name]
            logger.debug(f"Unregistered seeder: {name}")
    
    def get(self, name: str) -> Optional[Type[BaseSeeder]]:
        """
        Get a seeder class by name.
        
        Args:
            name: Name of the seeder
            
        Returns:
            The seeder class or None if not found
        """
        if not self._discovered:
            self.discover()
        
        return self._seeders.get(name)
    
    def get_all(self) -> Dict[str, Type[BaseSeeder]]:
        """
        Get all registered seeders.
        
        Returns:
            Dictionary of seeder names to classes
        """
        if not self._discovered:
            self.discover()
        
        return self._seeders.copy()
    
    def get_names(self) -> List[str]:
        """
        Get all registered seeder names.
        
        Returns:
            List of seeder names
        """
        if not self._discovered:
            self.discover()
        
        return list(self._seeders.keys())
    
    def get_by_environment(self, environment: str) -> Dict[str, Type[BaseSeeder]]:
        """
        Get seeders that should run in a specific environment.
        
        Args:
            environment: The environment name
            
        Returns:
            Dictionary of seeder names to classes
        """
        if not self._discovered:
            self.discover()
        
        result = {}
        for name, seeder_class in self._seeders.items():
            metadata = seeder_class._get_metadata()
            if "all" in metadata.environments or environment in metadata.environments:
                result[name] = seeder_class
        
        return result
    
    def get_by_tag(self, tag: str) -> Dict[str, Type[BaseSeeder]]:
        """
        Get seeders with a specific tag.
        
        Args:
            tag: The tag to filter by
            
        Returns:
            Dictionary of seeder names to classes
        """
        if not self._discovered:
            self.discover()
        
        result = {}
        for name, seeder_class in self._seeders.items():
            metadata = seeder_class._get_metadata()
            if tag in metadata.tags:
                result[name] = seeder_class
        
        return result
    
    def clear(self) -> None:
        """Clear all registered seeders."""
        self._seeders.clear()
        self._discovered = False
    
    def __len__(self) -> int:
        """Get the number of registered seeders."""
        if not self._discovered:
            self.discover()
        return len(self._seeders)
    
    def __contains__(self, name: str) -> bool:
        """Check if a seeder is registered."""
        if not self._discovered:
            self.discover()
        return name in self._seeders