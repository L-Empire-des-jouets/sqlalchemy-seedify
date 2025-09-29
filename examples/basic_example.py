"""
Basic example of using sqlalchemy-seedify.
"""

from alembic_seeder import BaseSeeder


class RoleSeeder(BaseSeeder):
    """Seed application roles."""

    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata

        return SeederMetadata(
            name=cls.__name__,
            description="Seed application roles",
            environments=["all"],
            priority=10,  # Run early
            can_rollback=True,
        )

    def run(self):
        """Create default roles."""
        from myapp.models import Role

        rows = [
            {"name": "admin", "description": "Administrator with full access"},
            {"name": "moderator", "description": "Content moderator"},
            {"name": "user", "description": "Regular user"},
            {"name": "guest", "description": "Guest user with limited access"},
        ]
        self.bulk_upsert(
            model=Role,
            rows=rows,
            key_fields=["name"],
            update_fields=["description"],
        )

    def rollback(self):
        """Remove seeded roles."""
        from myapp.models import Role

        role_names = ["admin", "moderator", "user", "guest"]
        deleted = (
            self.session.query(Role)
            .filter(Role.name.in_(role_names))
            .delete(synchronize_session=False)
        )

        self.session.flush()
        print(f"Deleted {deleted} roles")


class UserSeeder(BaseSeeder):
    """Seed initial users."""

    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata

        return SeederMetadata(
            name=cls.__name__,
            description="Seed initial users with roles",
            environments=["development", "testing"],
            dependencies=["RoleSeeder"],  # Requires roles to exist
            priority=20,
            can_rollback=True,
        )

    def run(self):
        """Create initial users."""
        from myapp.models import Role, User

        # Get roles
        admin_role = self.session.query(Role).filter_by(name="admin").first()
        user_role = self.session.query(Role).filter_by(name="user").first()

        rows = [
            {
                "username": "admin",
                "email": "admin@example.com",
                "password": "hashed_password_here",
                "is_active": True,
            },
            {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "hashed_password_here",
                "is_active": True,
            },
            {
                "username": "jane_smith",
                "email": "jane@example.com",
                "password": "hashed_password_here",
                "is_active": True,
            },
        ]
        # Upsert users by unique email, update username/is_active; set role separately
        self.bulk_upsert(
            model=User,
            rows=rows,
            key_fields=["email"],
            update_fields=["username", "is_active", "password"],
        )
        # Assign roles idempotently via upsert on relation table if applicable
        # If using simple FK role_id on User
        for row in rows:
            user = self.session.query(User).filter_by(email=row["email"]).first()
            if user and user_role and admin_role:
                target_role = admin_role if row["email"] == "admin@example.com" else user_role
                if getattr(user, "role_id", None) != getattr(target_role, "id", None):
                    user.role = target_role
        self.session.flush()

    def rollback(self):
        """Remove seeded users."""
        from myapp.models import User

        emails = ["admin@example.com", "john@example.com", "jane@example.com"]
        deleted = (
            self.session.query(User)
            .filter(User.email.in_(emails))
            .delete(synchronize_session=False)
        )

        self.session.flush()
        print(f"Deleted {deleted} users")


class CategorySeeder(BaseSeeder):
    """Seed product categories."""

    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata

        return SeederMetadata(
            name=cls.__name__,
            description="Seed product categories",
            environments=["all"],
            priority=30,
            can_rollback=True,
            tags=["products", "catalog"],
        )

    def run(self):
        """Create product categories."""
        from myapp.models import Category

        categories = [
            {
                "name": "Electronics",
                "slug": "electronics",
                "description": "Products in Electronics category",
                "is_active": True,
            },
            {
                "name": "Books",
                "slug": "books",
                "description": "Products in Books category",
                "is_active": True,
            },
            {
                "name": "Clothing",
                "slug": "clothing",
                "description": "Products in Clothing category",
                "is_active": True,
            },
            {
                "name": "Home & Garden",
                "slug": "home-garden",
                "description": "Products in Home & Garden category",
                "is_active": True,
            },
            {
                "name": "Sports",
                "slug": "sports",
                "description": "Products in Sports category",
                "is_active": True,
            },
        ]
        self.bulk_upsert(
            model=Category,
            rows=categories,
            key_fields=["slug"],
            update_fields=["name", "description", "is_active"],
        )
        electronics = self.session.query(Category).filter_by(slug="electronics").first()
        if electronics:
            subcategories = [
                {"name": "Laptops", "slug": "laptops", "parent_id": electronics.id},
                {"name": "Smartphones", "slug": "smartphones", "parent_id": electronics.id},
                {"name": "Tablets", "slug": "tablets", "parent_id": electronics.id},
            ]
            self.bulk_upsert(
                model=Category,
                rows=subcategories,
                key_fields=["slug"],
                update_fields=["name", "parent_id"],
            )

    def rollback(self):
        """Remove seeded categories."""
        from myapp.models import Category

        # Delete subcategories first (due to foreign key constraints)
        slugs = ["laptops", "smartphones", "tablets"]
        self.session.query(Category).filter(Category.slug.in_(slugs)).delete(
            synchronize_session=False
        )

        # Delete main categories
        main_slugs = ["electronics", "books", "clothing", "home-garden", "sports"]
        deleted = (
            self.session.query(Category)
            .filter(Category.slug.in_(main_slugs))
            .delete(synchronize_session=False)
        )

        self.session.flush()
        print("Deleted categories")


class SettingsSeeder(BaseSeeder):
    """Seed application settings."""

    @classmethod
    def _get_metadata(cls):
        from alembic_seeder.core.base_seeder import SeederMetadata

        return SeederMetadata(
            name=cls.__name__,
            description="Seed application configuration settings",
            environments=["all"],
            priority=5,  # Run very early
            can_rollback=True,
            tags=["configuration", "essential"],
        )

    def run(self):
        """Create default application settings."""
        from myapp.models import Setting

        settings = [
            # General settings
            {"key": "app_name", "value": "My Application", "type": "string"},
            {"key": "app_description", "value": "A sample application", "type": "string"},
            {"key": "maintenance_mode", "value": "false", "type": "boolean"},
            # Email settings
            {"key": "email_from_address", "value": "noreply@example.com", "type": "string"},
            {"key": "email_from_name", "value": "My App", "type": "string"},
            # Feature flags
            {"key": "feature_registration", "value": "true", "type": "boolean"},
            {"key": "feature_social_login", "value": "false", "type": "boolean"},
            {"key": "feature_two_factor", "value": "false", "type": "boolean"},
            # Limits
            {"key": "max_upload_size", "value": "10485760", "type": "integer"},
            {"key": "rate_limit_requests", "value": "100", "type": "integer"},
            {"key": "rate_limit_window", "value": "3600", "type": "integer"},
        ]

        rows = []
        for s in settings:
            rows.append(
                {
                    "key": s["key"],
                    "value": s["value"],
                    "type": s["type"],
                    "description": f"Setting for {s['key'].replace('_', ' ')}",
                }
            )
        self.bulk_upsert(
            model=Setting,
            rows=rows,
            key_fields=["key"],
            update_fields=["value", "type", "description"],
        )

    def rollback(self):
        """Remove seeded settings."""
        from myapp.models import Setting

        keys = [
            "app_name",
            "app_description",
            "maintenance_mode",
            "email_from_address",
            "email_from_name",
            "feature_registration",
            "feature_social_login",
            "feature_two_factor",
            "max_upload_size",
            "rate_limit_requests",
            "rate_limit_window",
        ]

        deleted = (
            self.session.query(Setting)
            .filter(Setting.key.in_(keys))
            .delete(synchronize_session=False)
        )

        self.session.flush()
        print(f"Deleted {deleted} settings")
