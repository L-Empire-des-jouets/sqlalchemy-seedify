"""
Dedicated utilities for idempotent data operations.

This class encapsulates upsert logic to keep BaseSeeder concise and focused
on lifecycle. It operates on a provided SQLAlchemy session.
"""

from typing import Any, Dict, List, Optional, Type

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session


class UpsertManager:
    def __init__(self, session: Session):
        self.session = session

    def get_or_create(
        self,
        model: Type[Any],
        where: Dict[str, Any],
        defaults: Optional[Dict[str, Any]] = None,
    ) -> Any:
        instance = self.session.query(model).filter_by(**where).first()
        if instance:
            return instance, False

        payload: Dict[str, Any] = {}
        if defaults:
            payload.update(defaults)
        payload.update(where)

        instance = model(**payload)
        self.session.add(instance)
        self.session.flush()
        return instance, True

    def upsert(
        self,
        model: Type[Any],
        where: Dict[str, Any],
        values: Dict[str, Any],
        update_existing: bool = True,
    ) -> Any:
        instance = self.session.query(model).filter_by(**where).first()
        if not instance:
            payload = {**where, **values}
            instance = model(**payload)
            self.session.add(instance)
            self.session.flush()
            return instance, "created"

        if not update_existing:
            return instance, "unchanged"

        changed = False
        for field, new_value in values.items():
            current_value = getattr(instance, field, None)
            if current_value != new_value:
                setattr(instance, field, new_value)
                changed = True

        if changed:
            self.session.flush()
            return instance, "updated"

        return instance, "unchanged"

    def bulk_upsert(
        self,
        model: Type[Any],
        rows: List[Dict[str, Any]],
        key_fields: List[str],
        update_fields: Optional[List[str]] = None,
    ) -> Dict[str, int]:
        if not rows:
            return {"created": 0, "updated": 0, "unchanged": 0}

        # Prepare key tuples
        key_tuples = []
        for row in rows:
            key_tuples.append(tuple(row[k] for k in key_fields))

        # Build filters to fetch all existing in one go
        filters = []
        for key_values in key_tuples:
            clauses = []
            for idx, field in enumerate(key_fields):
                clauses.append(getattr(model, field) == key_values[idx])
            filters.append(and_(*clauses))

        existing_by_key: Dict[tuple, Any] = {}
        if filters:
            existing = self.session.query(model).filter(or_(*filters)).all()
            for obj in existing:
                key = tuple(getattr(obj, f) for f in key_fields)
                existing_by_key[key] = obj

        created_count = 0
        updated_count = 0
        unchanged_count = 0

        for row in rows:
            key = tuple(row[k] for k in key_fields)
            obj = existing_by_key.get(key)
            if obj is None:
                obj = model(**row)
                self.session.add(obj)
                created_count += 1
                existing_by_key[key] = obj
                continue

            # Determine fields to update
            fields_to_update = (
                [f for f in row.keys() if f not in key_fields]
                if update_fields is None
                else [f for f in update_fields if f in row]
            )

            changed = False
            for field in fields_to_update:
                new_value = row[field]
                if getattr(obj, field, None) != new_value:
                    setattr(obj, field, new_value)
                    changed = True

            if changed:
                updated_count += 1
            else:
                unchanged_count += 1

        self.session.flush()

        return {
            "created": created_count,
            "updated": updated_count,
            "unchanged": unchanged_count,
        }
