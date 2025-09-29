"""
Utilities to compute deterministic content hashes for seeders.
"""

import hashlib
import inspect
import json
from typing import Type

from src.core.base_seeder import BaseSeeder


def compute_seeder_content_hash(seeder_class: Type[BaseSeeder]) -> str:
    """
    Compute a stable hash representing the seeder's effective content.

    The hash includes:
    - Source of the seeder class `run` method
    - Source of the optional `rollback` method if supported
    - Seeder metadata returned by `_get_metadata()` (as a sorted JSON)

    Returns a lowercase hex digest (sha256).
    """
    sha = hashlib.sha256()

    # Method sources
    try:
        run_src = inspect.getsource(seeder_class.run)
    except Exception:
        run_src = ""
    sha.update(run_src.encode("utf-8"))

    # Include rollback method source if overridden
    try:
        # Only include if the class overrides BaseSeeder.rollback
        if seeder_class.rollback is not BaseSeeder.rollback:
            rb_src = inspect.getsource(seeder_class.rollback)
            sha.update(rb_src.encode("utf-8"))
    except Exception:
        pass

    # Metadata (sorted JSON for stability)
    try:
        metadata = seeder_class._get_metadata()
        # Pydantic v2: model_dump
        meta_dict = metadata.model_dump(exclude_none=True)
    except Exception:
        meta_dict = {
            "name": seeder_class.__name__,
            "description": seeder_class.__doc__,
        }

    meta_json = json.dumps(meta_dict, sort_keys=True, ensure_ascii=False)
    sha.update(meta_json.encode("utf-8"))

    return sha.hexdigest()
