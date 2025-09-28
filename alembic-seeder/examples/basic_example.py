"""
Basic example of using alembic-seeder.
"""

from datetime import datetime
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
        
        roles = [
            Role(name="admin", description="Administrator with full access"),
            Role(name="moderator", description="Content moderator"),
            Role(name="user", description="Regular user"),
            Role(name="guest", description="Guest user with limited access"),
        ]
        
        for role in roles:
            # Check if role already exists
            existing = self.session.query(Role).filter_by(name=role.name).first()
            if not existing:
                self.session.add(role)
                self._records_affected += 1
        
        self.session.flush()
    
    def rollback(self):
        """Remove seeded roles."""
        from myapp.models import Role
        
        role_names = ["admin", "moderator", "user", "guest"]
        deleted = self.session.query(Role).filter(
            Role.name.in_(role_names)
        ).delete(synchronize_session=False)
        
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
        from myapp.models import User, Role
        
        # Get roles
        admin_role = self.session.query(Role).filter_by(name="admin").first()
        user_role = self.session.query(Role).filter_by(name="user").first()
        
        users = [
            {
                "username": "admin",
                "email": "admin@example.com",
                "password": "hashed_password_here",  # Use proper password hashing!
                "role": admin_role,
                "is_active": True,
            },
            {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "hashed_password_here",
                "role": user_role,
                "is_active": True,
            },
            {
                "username": "jane_smith",
                "email": "jane@example.com",
                "password": "hashed_password_here",
                "role": user_role,
                "is_active": True,
            },
        ]
        
        for user_data in users:
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                password=user_data["password"],
                is_active=user_data["is_active"],
                created_at=datetime.utcnow(),
            )
            user.role = user_data["role"]
            
            # Check if user already exists
            existing = self.session.query(User).filter_by(email=user.email).first()
            if not existing:
                self.session.add(user)
                self._records_affected += 1
        
        self.session.flush()
    
    def rollback(self):
        """Remove seeded users."""
        from myapp.models import User
        
        emails = ["admin@example.com", "john@example.com", "jane@example.com"]
        deleted = self.session.query(User).filter(
            User.email.in_(emails)
        ).delete(synchronize_session=False)
        
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
            {"name": "Electronics", "slug": "electronics", "parent": None},
            {"name": "Books", "slug": "books", "parent": None},
            {"name": "Clothing", "slug": "clothing", "parent": None},
            {"name": "Home & Garden", "slug": "home-garden", "parent": None},
            {"name": "Sports", "slug": "sports", "parent": None},
        ]
        
        # Create main categories
        for cat_data in categories:
            category = Category(
                name=cat_data["name"],
                slug=cat_data["slug"],
                description=f"Products in {cat_data['name']} category",
                is_active=True,
            )
            self.session.add(category)
            self._records_affected += 1
        
        self.session.flush()
        
        # Create subcategories
        electronics = self.session.query(Category).filter_by(slug="electronics").first()
        if electronics:
            subcategories = [
                Category(name="Laptops", slug="laptops", parent_id=electronics.id),
                Category(name="Smartphones", slug="smartphones", parent_id=electronics.id),
                Category(name="Tablets", slug="tablets", parent_id=electronics.id),
            ]
            
            for subcat in subcategories:
                self.session.add(subcat)
                self._records_affected += 1
        
        self.session.flush()
    
    def rollback(self):
        """Remove seeded categories."""
        from myapp.models import Category
        
        # Delete subcategories first (due to foreign key constraints)
        slugs = ["laptops", "smartphones", "tablets"]
        self.session.query(Category).filter(
            Category.slug.in_(slugs)
        ).delete(synchronize_session=False)
        
        # Delete main categories
        main_slugs = ["electronics", "books", "clothing", "home-garden", "sports"]
        deleted = self.session.query(Category).filter(
            Category.slug.in_(main_slugs)
        ).delete(synchronize_session=False)
        
        self.session.flush()
        print(f"Deleted categories")


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
        
        for setting_data in settings:
            setting = Setting(
                key=setting_data["key"],
                value=setting_data["value"],
                type=setting_data["type"],
                description=f"Setting for {setting_data['key'].replace('_', ' ')}",
            )
            
            # Check if setting already exists
            existing = self.session.query(Setting).filter_by(key=setting.key).first()
            if not existing:
                self.session.add(setting)
                self._records_affected += 1
            else:
                # Update existing setting
                existing.value = setting.value
                existing.type = setting.type
        
        self.session.flush()
    
    def rollback(self):
        """Remove seeded settings."""
        from myapp.models import Setting
        
        keys = [
            "app_name", "app_description", "maintenance_mode",
            "email_from_address", "email_from_name",
            "feature_registration", "feature_social_login", "feature_two_factor",
            "max_upload_size", "rate_limit_requests", "rate_limit_window",
        ]
        
        deleted = self.session.query(Setting).filter(
            Setting.key.in_(keys)
        ).delete(synchronize_session=False)
        
        self.session.flush()
        print(f"Deleted {deleted} settings")