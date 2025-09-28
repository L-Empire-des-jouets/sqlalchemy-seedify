"""
Make command for creating new seeder files.
"""

import os
from pathlib import Path
from datetime import datetime
import logging

from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


BASIC_TEMPLATE = '''"""
{description}
"""

from alembic_seeder import BaseSeeder


class {class_name}(BaseSeeder):
    """{description}"""
    
    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata
        return SeederMetadata(
            name=cls.__name__,
            description="{description}",
            environments={environments},
            dependencies={dependencies},
            priority={priority},
            can_rollback={can_rollback},
        )
    
    def run(self):
        """Execute the seeder."""
        # Best practice: one seeder per table, idempotent by default
        # Example with upsert (idempotent insert-or-update):
        # from myapp.models import MyModel
        # rows = [
        #     {"code": "value1", "label": "Label 1"},
        #     {"code": "value2", "label": "Label 2"},
        # ]
        # for row in rows:
        #     self.upsert(
        #         model=MyModel,
        #         where={"code": row["code"]},  # business key
        #         values={"label": row["label"]},
        #         update_existing=True,
        #     )
        
        pass
    {rollback_method}
'''

ROLLBACK_TEMPLATE = '''
    def rollback(self):
        """Rollback the seeder."""
        # TODO: Implement your rollback logic here
        # Example:
        # from myapp.models import MyModel
        # 
        # self.session.query(MyModel).filter(
        #     MyModel.created_by == "seeder"
        # ).delete()
        # 
        # self.session.flush()
        
        pass'''

FAKER_TEMPLATE = '''"""
{description}
"""

from alembic_seeder import BaseSeeder


class {class_name}(BaseSeeder):
    """{description}"""
    
    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata
        return SeederMetadata(
            name=cls.__name__,
            description="{description}",
            environments={environments},
            dependencies={dependencies},
            priority={priority},
            can_rollback={can_rollback},
            batch_size=100,
        )
    
    def run(self):
        """Execute the seeder with Faker data."""
        try:
            from faker import Faker
        except ImportError:
            raise ImportError("Faker is required. Install it with: pip install faker")
        
        fake = Faker()
        
        # Best practice: idempotent seeding via bulk_upsert using a business key
        # Example:
        # from myapp.models import User
        # rows = []
        # for _ in range(100):
        #     rows.append({
        #         "email": fake.unique.email(),  # business key
        #         "name": fake.name(),
        #         "phone": fake.phone_number(),
        #         "address": fake.address(),
        #     })
        # self.bulk_upsert(
        #     model=User,
        #     rows=rows,
        #     key_fields=["email"],
        #     update_fields=["name", "phone", "address"],
        # )
        
        pass
    {rollback_method}
'''

FACTORY_TEMPLATE = '''"""
{description}
"""

from alembic_seeder import BaseSeeder


class {class_name}(BaseSeeder):
    """{description}"""
    
    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata
        return SeederMetadata(
            name=cls.__name__,
            description="{description}",
            environments={environments},
            dependencies={dependencies},
            priority={priority},
            can_rollback={can_rollback},
        )
    
    def run(self):
        """Execute the seeder using factory pattern."""
        # Ensure factories produce deterministic business keys to allow idempotent upserts
        # Example with factory_boy:
        # from myapp.factories import UserFactory
        # from myapp.models import User
        # users = UserFactory.build_batch(10)  # build, don't persist
        # for user in users:
        #     self.upsert(
        #         model=User,
        #         where={"email": user.email},
        #         values={"name": user.name},
        #     )
        
        pass
    {rollback_method}
'''

RELATION_TEMPLATE = '''"""
{description}
"""

from alembic_seeder import BaseSeeder


class {class_name}(BaseSeeder):
    """{description}"""
    
    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata
        return SeederMetadata(
            name=cls.__name__,
            description="{description}",
            environments={environments},
            dependencies={dependencies},  # Add dependent seeders here
            priority={priority},
            can_rollback={can_rollback},
        )
    
    def run(self):
        """Execute the seeder for relational data."""
        # Example with idempotent upserts across relations:
        # from myapp.models import User, Profile, Role, UserRole
        # self.upsert(Role, {"name": "admin"}, {"description": "Administrator"})
        # self.upsert(Role, {"name": "user"}, {"description": "User"})
        # users = self.session.query(User).all()
        # for user in users:
        #     # Profile by unique user_id
        #     self.upsert(
        #         Profile,
        #         where={"user_id": user.id},
        #         values={"bio": "Lorem ipsum..."},
        #     )
        #     # N-N assignment via unique composite (user_id, role_id)
        #     role_name = "admin" if user.email.endswith("@admin.com") else "user"
        #     role = self.session.query(Role).filter_by(name=role_name).first()
        #     if role:
        #         self.upsert(
        #             UserRole,
        #             where={"user_id": user.id, "role_id": role.id},
        #             values={},
        #             update_existing=False,
        #         )
        
        pass
    {rollback_method}
'''

TEMPLATES = {
    "basic": BASIC_TEMPLATE,
    "faker": FAKER_TEMPLATE,
    "factory": FACTORY_TEMPLATE,
    "relation": RELATION_TEMPLATE,
}


def create_seeder(
    name: str,
    template: str = "basic",
    environments: list = None,
    with_rollback: bool = False,
    config = None,
    dependencies: list = None,
    priority: int = 100,
) -> Path:
    """
    Create a new seeder file from template.
    
    Args:
        name: Name of the seeder class
        template: Template to use
        environments: Environments this seeder should run in
        with_rollback: Include rollback method
        config: Configuration object
        dependencies: List of seeder dependencies
        priority: Execution priority
        
    Returns:
        Path to the created seeder file
    """
    # Ensure name is a valid class name
    if not name[0].isupper():
        name = name[0].upper() + name[1:]
    
    if not name.endswith("Seeder"):
        name = name + "Seeder"
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{name.lower()}.py"
    
    # Get seeders path
    seeders_path = Path(config.seeders_path if config else "seeders")
    seeders_path.mkdir(parents=True, exist_ok=True)
    
    # Prepare template variables
    environments = environments or ["all"]
    dependencies = dependencies or []
    
    template_vars = {
        "class_name": name,
        "description": f"Seeder for {name}",
        "environments": repr(environments),
        "dependencies": repr(dependencies),
        "priority": priority,
        "can_rollback": str(with_rollback),
        "rollback_method": ROLLBACK_TEMPLATE if with_rollback else "",
    }
    
    # Get template
    template_content = TEMPLATES.get(template, BASIC_TEMPLATE)
    
    # Generate content
    content = template_content.format(**template_vars)
    
    # Write file
    file_path = seeders_path / filename
    file_path.write_text(content)
    
    console.print(f"[green]✓[/green] Created seeder: {file_path}")
    
    # Provide next steps
    console.print("\nNext steps:")
    console.print(f"1. Edit the seeder: {file_path}")
    console.print("2. Implement the run() method")
    if with_rollback:
        console.print("3. Implement the rollback() method")
    console.print(f"{3 if not with_rollback else 4}. Run the seeder: sqlalchemy-seedify run --seeder {name}")
    
    return file_path