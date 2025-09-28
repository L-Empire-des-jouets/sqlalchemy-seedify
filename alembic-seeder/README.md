# Alembic Seeder 🌱

A comprehensive seeder system for Alembic and SQLAlchemy, inspired by Laravel's seeder functionality. This package provides a robust, environment-aware seeding solution for Python applications.

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-green)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## ✨ Features

- **Laravel-like Seeders**: Familiar interface for developers coming from Laravel/PHP
- **Environment Management**: Run different seeders in development, testing, and production
- **Dependency Resolution**: Define dependencies between seeders with automatic ordering
- **Rollback Support**: Undo seeder operations when needed
- **Tracking System**: Keep track of which seeders have been executed
- **Content Hashing**: Detect changed seeders via code+metadata hash; skip up-to-date seeders
- **CLI Integration**: Seamless integration with Alembic commands
- **Batch Operations**: Execute seeders in batches for better organization
- **Dry Run Mode**: Preview what will be executed without making changes
- **Rich CLI Output**: Beautiful, informative command-line interface

## 📦 Installation

### Using pip

```bash
pip install alembic-seeder
```

### Using UV (recommended)

```bash
uv add alembic-seeder
```

### With Alembic integration

```bash
uv add alembic-seeder[alembic]
```

## 🚀 Quick Start

### 1. Initialize in your project

```bash
alembic-seeder init
```

This will:
- Create a `seeders/` directory
- Generate a configuration file
- Create an example seeder
- Set up the tracking table migration (if Alembic is detected)

### 2. Create your first seeder

```bash
alembic-seeder make UserSeeder
```

### 3. Edit the seeder

```python
from alembic_seeder import BaseSeeder
from myapp.models import User

class UserSeeder(BaseSeeder):
    """Seed initial users."""
    
    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata
        return SeederMetadata(
            name=cls.__name__,
            description="Seed initial users",
            environments=["development", "testing"],
            can_rollback=True,
        )
    
    def run(self):
        """Execute the seeder."""
        users = [
            User(name="Admin", email="admin@example.com", role="admin"),
            User(name="John Doe", email="john@example.com", role="user"),
        ]
        
        for user in users:
            self.session.add(user)
        
        self.session.flush()
        self._records_affected = len(users)
    
    def rollback(self):
        """Rollback the seeder."""
        self.session.query(User).filter(
            User.email.in_(["admin@example.com", "john@example.com"])
        ).delete()
        self.session.flush()
```

### 4. Run the seeder

```bash
# Run all seeders
alembic-seeder run

# Run specific seeder
alembic-seeder run --seeder UserSeeder

# Dry run to preview
alembic-seeder run --dry-run
```

## 📖 Documentation

### Configuration

Create a `seeder.config.json` file:

```json
{
  "database_url": null,
  "seeders_path": "seeders",
  "default_environment": "development",
  "batch_size": 1000,
  "tracking_table_name": "alembic_seeder_history",
  "require_confirmation_prod": true,
  "log_level": "INFO"
}
```

Or use environment variables:

```bash
export DATABASE_URL="postgresql://user:pass@localhost/dbname"
export SEEDER_DEFAULT_ENVIRONMENT="development"
export SEEDER_LOG_LEVEL="DEBUG"
```

### Environment Management

Seeders can be configured to run only in specific environments:

```python
@classmethod
def _get_metadata(cls):
    return SeederMetadata(
        name=cls.__name__,
        environments=["development", "testing"],  # Won't run in production
    )
```

Set the current environment:

```bash
# Via environment variable
export ENVIRONMENT="production"

# Via CLI option
alembic-seeder run --env production
```

### Dependencies

Define dependencies between seeders:

```python
@classmethod
def _get_metadata(cls):
    return SeederMetadata(
        name=cls.__name__,
        dependencies=["RoleSeeder", "PermissionSeeder"],  # Run these first
    )
```

The system automatically resolves dependencies and determines the correct execution order.

### CLI Commands

#### Initialize
```bash
alembic-seeder init
```

#### Create Seeders
```bash
# Basic seeder
alembic-seeder make MySeeder

# With Faker template
alembic-seeder make UserSeeder --template faker

# With rollback support
alembic-seeder make ProductSeeder --rollback

# For specific environments
alembic-seeder make TestSeeder --env testing --env development
```

#### Run Seeders
```bash
# Run all pending seeders
alembic-seeder run

# Run specific seeders
alembic-seeder run --seeder UserSeeder --seeder ProductSeeder

# Force re-run
alembic-seeder run --force

# Fresh run (clear tracking, then run all)
alembic-seeder run --fresh

# Dry run
alembic-seeder run --dry-run

# Run by tag
alembic-seeder run --tag essential --tag test-data
```

#### Rollback
```bash
# Rollback specific seeders
alembic-seeder rollback --seeder UserSeeder

# Rollback last batch
alembic-seeder rollback --batch 1

# Rollback all
alembic-seeder rollback --all
```

#### Status and Information
```bash
# Check status
alembic-seeder status

# Detailed status
alembic-seeder status --detailed

# List all seeders
alembic-seeder list
```

#### Refresh (Rollback + Run)
```bash
# Refresh all seeders
alembic-seeder refresh

# Dry run refresh
alembic-seeder refresh --dry-run
```

## 🎯 Advanced Usage

### Custom Seeder Templates

Create seeders with different templates:

```bash
# Faker template for test data
alembic-seeder make FakeUserSeeder --template faker

# Factory pattern template
alembic-seeder make UserFactory --template factory

# Relational data template
alembic-seeder make UserProfileSeeder --template relation
```

### Batch Processing

Process large datasets efficiently:

```python
def run(self):
    batch_size = self._metadata.batch_size
    
    for i in range(0, 10000, batch_size):
        batch = []
        for j in range(batch_size):
            batch.append(MyModel(data=f"Item {i+j}"))
        
        self.session.bulk_insert_mappings(MyModel, batch)
        self.session.flush()
```

### Calling Other Seeders

```python
def run(self):
    # Call another seeder from within this seeder
    self.call(RoleSeeder)
    self.call(PermissionSeeder)
    
    # Your seeder logic here
    # ...
```

### Hooks and Events

```python
class MySeeder(BaseSeeder):
    def before_run(self):
        """Called before run()"""
        super().before_run()
        print("Preparing to seed...")
    
    def after_run(self):
        """Called after run()"""
        super().after_run()
        print(f"Seeded {self._records_affected} records")
    
    def validate(self):
        """Validate before execution"""
        if not self.session.bind:
            return False
        return True
```

## 🔧 Integration with Alembic

### Automatic Integration

If Alembic is detected, the initialization command will:
1. Generate a migration for the tracking table
2. Provide instructions for updating `alembic/env.py`

### Manual Integration

Add to your `alembic/env.py`:

```python
from alembic_seeder.tracking.models import Base as SeederBase

# Include SeederBase in your metadata
target_metadata = [Base.metadata, SeederBase.metadata]
```

### Using with Alembic Commands

```bash
# Run migrations and seeders together
alembic upgrade head && alembic-seeder run

# Rollback migrations and seeders
alembic-seeder rollback --all && alembic downgrade -1
```

## 🏗️ Architecture

### Components

- **BaseSeeder**: Abstract base class for all seeders
- **SeederManager**: Orchestrates seeder execution
- **SeederRegistry**: Discovers and manages seeder classes
- **SeederTracker**: Tracks execution history
- **EnvironmentManager**: Manages environment-specific configurations

### Database Schema

The tracking table (`alembic_seeder_history`) stores:
- Seeder name and environment
- Execution timestamp and duration
- Batch number
- Records affected
- Status and error messages
 - Content hash (sha256) for change detection

## 🧪 Testing

### Test Seeders

Create test-specific seeders:

```python
@classmethod
def _get_metadata(cls):
    return SeederMetadata(
        name=cls.__name__,
        environments=["testing"],  # Only runs in test environment
        tags=["test-data"],
    )
```

### Running Tests

```bash
# Set test environment
export ENVIRONMENT=testing

# Run test seeders
alembic-seeder run --tag test-data

# Run your tests
pytest

# Clean up
alembic-seeder rollback --all
```

## 🔒 Production Safety

### Confirmation Prompts

Production operations require confirmation by default:

```bash
$ alembic-seeder run --env production
⚠️  You are about to run seeders in PRODUCTION. Continue? [y/N]:
```

### Restricted Seeders

Prevent certain seeders from running in production:

```python
@classmethod
def _get_metadata(cls):
    return SeederMetadata(
        name=cls.__name__,
        environments=["development", "testing"],  # Excludes production
    )
```

## 📝 Best Practices

1. **One seeder per table**: structure seeders so that each table has its own seeder.
2. **Idempotent by default**: use the built-in helpers `upsert`, `bulk_upsert`, `get_or_create` to ensure safe reruns.
3. **Use a business key**: pick a stable unique key (e.g. `email`, `slug`, `(user_id, role_id)`) and add a unique constraint in your DB.
4. **Environment-specific seeders**: separate development, testing, and production data.
5. **Implement rollback**: always implement rollback for production seeders.
6. **Set dependencies**: use dependencies to ensure correct execution order.
7. **Batch large operations**: process large datasets in batches.
8. **Use transactions**: the manager handles commits/rollbacks around each seeder.
9. **Tag seeders**: group related seeders with tags.
10. **Document seeders**: add clear descriptions to your seeders.
11. **Test seeders**: test in development before production.
12. **Monitor execution**: check status and logs regularly.

### Idempotence helpers

`BaseSeeder` exposes helpers to make idempotent seeding trivial:

```python
result = self.get_or_create(Model, where={"code": "books"}, defaults={"label": "Books"})

result = self.upsert(
    model=Category,
    where={"slug": "books"},
    values={"name": "Books", "is_active": True},
    update_existing=True,
)

stats = self.bulk_upsert(
    model=Category,
    rows=[
        {"slug": "electronics", "name": "Electronics"},
        {"slug": "books", "name": "Books"},
    ],
    key_fields=["slug"],
    update_fields=["name"],
)
```

These helpers increment `records_affected` for created rows (and, optionally, updated rows) and `flush()` changes for consistency.

## 🤝 Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by [Laravel's Seeder System](https://laravel.com/docs/seeding)
- Built on top of [SQLAlchemy](https://www.sqlalchemy.org/) and [Alembic](https://alembic.sqlalchemy.org/)
- CLI powered by [Click](https://click.palletsprojects.com/) and [Rich](https://rich.readthedocs.io/)

## 📞 Support

- 📧 Email: support@alembic-seeder.dev
- 🐛 Issues: [GitHub Issues](https://github.com/alembic-seeder/alembic-seeder/issues)
- 💬 Discussions: [GitHub Discussions](https://github.com/alembic-seeder/alembic-seeder/discussions)

---

Made with ❤️ by the Alembic Seeder Team