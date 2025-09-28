"""
Initialize command for setting up alembic-seeder in a project.
"""

import os
from pathlib import Path
import logging

from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


ALEMBIC_ENV_TEMPLATE = '''
# Add this to your alembic/env.py file to integrate with alembic-seeder

from alembic_seeder.tracking.models import Base as SeederBase

# Add SeederBase metadata to your target_metadata
# Example:
# target_metadata = [Base.metadata, SeederBase.metadata]
'''

SEEDER_CONFIG_TEMPLATE = '''{
  "database_url": null,
  "seeders_path": "seeders",
  "default_environment": "development",
  "auto_discover": true,
  "batch_size": 1000,
  "tracking_table_name": "alembic_seeder_history",
  "require_confirmation_prod": true,
  "log_level": "INFO"
}
'''

EXAMPLE_SEEDER_TEMPLATE = '''"""
Example seeder for {name}.
"""

from alembic_seeder import BaseSeeder


class {name}(BaseSeeder):
    """Example seeder that demonstrates basic usage."""
    
    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata
        return SeederMetadata(
            name=cls.__name__,
            description="Example seeder for demonstration",
            environments=["development", "testing"],
            dependencies=[],
            priority=100,
            can_rollback=True,
        )
    
    def run(self):
        """Execute the seeder."""
        # Example: Insert data into your database
        # from myapp.models import User
        # 
        # user = User(
        #     name="John Doe",
        #     email="john@example.com"
        # )
        # self.session.add(user)
        # self.session.flush()
        
        self._records_affected = 1
        print(f"Seeder {{self.name}} executed successfully!")
    
    def rollback(self):
        """Rollback the seeder."""
        # Example: Remove the data that was inserted
        # from myapp.models import User
        # 
        # self.session.query(User).filter_by(email="john@example.com").delete()
        # self.session.flush()
        
        print(f"Seeder {{self.name}} rolled back successfully!")
'''

MIGRATION_TEMPLATE = '''"""Create alembic_seeder_history table

Revision ID: {revision_id}
Revises: 
Create Date: {create_date}

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '{revision_id}'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'alembic_seeder_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('seeder_name', sa.String(length=255), nullable=False),
        sa.Column('environment', sa.String(length=50), nullable=False),
        sa.Column('batch', sa.Integer(), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.Column('execution_time', sa.Integer(), nullable=True),
        sa.Column('records_affected', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('seeder_name', 'environment', name='uq_seeder_env')
    )
    op.create_index(op.f('ix_alembic_seeder_history_batch'), 'alembic_seeder_history', ['batch'], unique=False)
    op.create_index(op.f('ix_alembic_seeder_history_environment'), 'alembic_seeder_history', ['environment'], unique=False)
    op.create_index(op.f('ix_alembic_seeder_history_seeder_name'), 'alembic_seeder_history', ['seeder_name'], unique=False)
    op.create_index(op.f('ix_alembic_seeder_history_content_hash'), 'alembic_seeder_history', ['content_hash'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_alembic_seeder_history_content_hash'), table_name='alembic_seeder_history')
    op.drop_index(op.f('ix_alembic_seeder_history_seeder_name'), table_name='alembic_seeder_history')
    op.drop_index(op.f('ix_alembic_seeder_history_environment'), table_name='alembic_seeder_history')
    op.drop_index(op.f('ix_alembic_seeder_history_batch'), table_name='alembic_seeder_history')
    op.drop_table('alembic_seeder_history')
'''


def initialize_project(config):
    """
    Initialize alembic-seeder in the current project.
    
    Args:
        config: Configuration object
    """
    console.print("[bold]Initializing alembic-seeder...[/bold]")
    
    # Create seeders directory
    seeders_path = Path(config.seeders_path)
    if not seeders_path.exists():
        seeders_path.mkdir(parents=True, exist_ok=True)
        console.print(f"✓ Created seeders directory: {seeders_path}")
    else:
        console.print(f"• Seeders directory already exists: {seeders_path}")
    
    # Create __init__.py in seeders directory
    init_file = seeders_path / "__init__.py"
    if not init_file.exists():
        init_file.write_text('"""Seeders for the application."""\n')
        console.print(f"✓ Created {init_file}")
    
    # Create configuration file if it doesn't exist
    config_files = [
        "seeder.config.json",
        ".seederrc",
        ".seederrc.json",
    ]
    
    config_exists = any(Path(f).exists() for f in config_files)
    
    if not config_exists:
        config_path = Path("seeder.config.json")
        config_path.write_text(SEEDER_CONFIG_TEMPLATE)
        console.print(f"✓ Created configuration file: {config_path}")
    else:
        console.print("• Configuration file already exists")
    
    # Create example seeder
    example_seeder = seeders_path / "example_seeder.py"
    if not example_seeder.exists():
        example_content = EXAMPLE_SEEDER_TEMPLATE.format(name="ExampleSeeder")
        example_seeder.write_text(example_content)
        console.print(f"✓ Created example seeder: {example_seeder}")
    
    # Check for Alembic
    alembic_dir = Path("alembic")
    if alembic_dir.exists():
        console.print("\n[bold cyan]Alembic detected![/bold cyan]")
        console.print("To integrate with Alembic:")
        console.print("1. Add the following to your alembic/env.py:")
        console.print("[dim]" + ALEMBIC_ENV_TEMPLATE + "[/dim]")
        
        # Generate migration for tracking table
        migrations_dir = alembic_dir / "versions"
        if migrations_dir.exists():
            import uuid
            from datetime import datetime
            
            revision_id = uuid.uuid4().hex[:12]
            create_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            migration_content = MIGRATION_TEMPLATE.format(
                revision_id=revision_id,
                create_date=create_date,
            )
            
            migration_file = migrations_dir / f"{revision_id}_create_seeder_tracking_table.py"
            if not any(f.name.endswith("_create_seeder_tracking_table.py") 
                      for f in migrations_dir.glob("*.py")):
                migration_file.write_text(migration_content)
                console.print(f"\n✓ Created migration for tracking table: {migration_file.name}")
                console.print("  Run 'alembic upgrade head' to apply the migration")
    else:
        console.print("\n[yellow]Alembic not detected.[/yellow]")
        console.print("The tracking table will be created automatically when you run seeders.")
    
    console.print("\n[bold green]Initialization complete![/bold green]")
    console.print("\nNext steps:")
    console.print("1. Configure your database URL in seeder.config.json or set DATABASE_URL")
    console.print("2. Create seeders: alembic-seeder make MySeeder")
    console.print("3. Run seeders: alembic-seeder run")
    console.print("4. Check status: alembic-seeder status")