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
        # TODO: Implement your seeding logic here
        # Example:
        # from myapp.models import MyModel
        # 
        # data = [
        #     MyModel(field1="value1", field2="value2"),
        #     MyModel(field1="value3", field2="value4"),
        # ]
        # 
        # for item in data:
        #     self.session.add(item)
        # 
        # self.session.flush()
        # self._records_affected = len(data)
        
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
        
        # TODO: Implement your seeding logic here
        # Example:
        # from myapp.models import User
        # 
        # users = []
        # for _ in range(100):
        #     user = User(
        #         name=fake.name(),
        #         email=fake.unique.email(),
        #         phone=fake.phone_number(),
        #         address=fake.address(),
        #         created_at=fake.date_time_between("-1y", "now"),
        #     )
        #     users.append(user)
        # 
        # self.session.bulk_save_objects(users)
        # self.session.flush()
        # self._records_affected = len(users)
        
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
        # TODO: Implement your factory-based seeding logic
        # Example with factory_boy:
        # from myapp.factories import UserFactory, PostFactory
        # 
        # # Create users
        # users = UserFactory.create_batch(10)
        # 
        # # Create posts for each user
        # for user in users:
        #     PostFactory.create_batch(5, author=user)
        # 
        # self.session.flush()
        # self._records_affected = 10 + (10 * 5)  # users + posts
        
        # Example with custom factory:
        # from myapp.factories import DataFactory
        # 
        # factory = DataFactory(self.session)
        # factory.create_users(10)
        # factory.create_posts(50)
        # factory.create_comments(200)
        # 
        # self._records_affected = factory.total_created
        
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
        # TODO: Implement seeding for related models
        # Example:
        # from myapp.models import User, Profile, Role
        # 
        # # Get or create roles
        # admin_role = self.session.query(Role).filter_by(name="admin").first()
        # user_role = self.session.query(Role).filter_by(name="user").first()
        # 
        # # Get existing users (from previous seeder)
        # users = self.session.query(User).all()
        # 
        # # Create profiles and assign roles
        # for user in users:
        #     # Create profile
        #     profile = Profile(
        #         user_id=user.id,
        #         bio="Lorem ipsum...",
        #         avatar_url=f"https://example.com/avatar/{{user.id}}.jpg"
        #     )
        #     self.session.add(profile)
        #     
        #     # Assign role
        #     if user.email.endswith("@admin.com"):
        #         user.roles.append(admin_role)
        #     else:
        #         user.roles.append(user_role)
        # 
        # self.session.flush()
        # self._records_affected = len(users) * 2  # profiles + role assignments
        
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
    console.print(f"{3 if not with_rollback else 4}. Run the seeder: alembic-seeder run --seeder {name}")
    
    return file_path