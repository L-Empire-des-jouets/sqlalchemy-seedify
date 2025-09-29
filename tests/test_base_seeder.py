"""
Tests for BaseSeeder class.
"""

from unittest.mock import Mock

from src import BaseSeeder
from src.core.base_seeder import SeederMetadata


class TestSeeder(BaseSeeder):
    """Test seeder implementation."""

    @classmethod
    def _get_metadata(cls):
        return SeederMetadata(
            name="TestSeeder",
            description="Test seeder for unit tests",
            environments=["testing"],
            dependencies=["DependencySeeder"],
            priority=100,
            can_rollback=True,
        )

    def run(self):
        """Test run implementation."""
        self._records_affected = 5

    def rollback(self):
        """Test rollback implementation."""
        pass


class NoRollbackSeeder(BaseSeeder):
    """Seeder without rollback support."""

    @classmethod
    def _get_metadata(cls):
        return SeederMetadata(
            name="NoRollbackSeeder",
            can_rollback=False,
        )

    def run(self):
        """Test run implementation."""
        pass


class TestBaseSeeder:
    """Test suite for BaseSeeder."""

    def test_initialization(self):
        """Test seeder initialization."""
        session = Mock()
        seeder = TestSeeder(session)

        assert seeder.session == session
        assert seeder.name == "TestSeeder"
        assert seeder.description == "Test seeder for unit tests"
        assert seeder.environments == ["testing"]
        assert seeder.dependencies == ["DependencySeeder"]
        assert seeder.priority == 100
        assert seeder.can_rollback is True

    def test_should_run(self):
        """Test environment checking."""
        seeder = TestSeeder()

        assert seeder.should_run("testing") is True
        assert seeder.should_run("production") is False

        # Test with "all" environment
        seeder._metadata.environments = ["all"]
        assert seeder.should_run("production") is True
        assert seeder.should_run("development") is True

    def test_execute_success(self):
        """Test successful execution."""
        session = Mock()
        seeder = TestSeeder(session)

        result = seeder.execute()

        assert result["name"] == "TestSeeder"
        assert result["status"] == "success"
        assert result["records_affected"] == 5
        assert "duration" in result
        assert result["duration"] >= 0

    def test_execute_failure(self):
        """Test execution failure."""
        session = Mock()
        seeder = TestSeeder(session)
        seeder.run = Mock(side_effect=Exception("Test error"))

        result = seeder.execute()

        assert result["name"] == "TestSeeder"
        assert result["status"] == "error"
        assert result["error"] == "Test error"

    def test_execute_rollback_success(self):
        """Test successful rollback."""
        session = Mock()
        seeder = TestSeeder(session)

        result = seeder.execute_rollback()

        assert result["name"] == "TestSeeder"
        assert result["status"] == "success"
        assert result["action"] == "rollback"

    def test_execute_rollback_not_supported(self):
        """Test rollback when not supported."""
        session = Mock()
        seeder = NoRollbackSeeder(session)

        result = seeder.execute_rollback()

        assert result["status"] == "error"
        assert "does not support rollback" in result["error"]

    def test_validate(self):
        """Test validation method."""
        seeder = TestSeeder()
        assert seeder.validate() is True

    def test_hooks(self):
        """Test before/after hooks."""
        session = Mock()
        seeder = TestSeeder(session)

        # Mock the hooks
        seeder.before_run = Mock()
        seeder.after_run = Mock()

        seeder.execute()

        seeder.before_run.assert_called_once()
        seeder.after_run.assert_called_once()

    def test_call_other_seeder(self):
        """Test calling another seeder."""
        session = Mock()
        seeder = TestSeeder(session)

        # Create a mock seeder class
        MockSeeder = Mock()
        mock_instance = Mock()
        MockSeeder.return_value = mock_instance

        seeder.call(MockSeeder)

        MockSeeder.assert_called_once_with(session)
        mock_instance.execute.assert_called_once()

    def test_metadata_defaults(self):
        """Test metadata default values."""

        class MinimalSeeder(BaseSeeder):
            def run(self):
                pass

        seeder = MinimalSeeder()

        assert seeder.name == "MinimalSeeder"
        assert seeder.environments == ["all"]
        assert seeder.dependencies == []
        assert seeder.priority == 100
        assert seeder.can_rollback is False


class TestSeederMetadata:
    """Test suite for SeederMetadata."""

    def test_metadata_creation(self):
        """Test creating metadata."""
        metadata = SeederMetadata(
            name="TestSeeder",
            description="Test description",
            environments=["dev", "test"],
            dependencies=["OtherSeeder"],
            priority=50,
            batch_size=500,
            can_rollback=True,
            tags=["test", "example"],
        )

        assert metadata.name == "TestSeeder"
        assert metadata.description == "Test description"
        assert metadata.environments == ["dev", "test"]
        assert metadata.dependencies == ["OtherSeeder"]
        assert metadata.priority == 50
        assert metadata.batch_size == 500
        assert metadata.can_rollback is True
        assert metadata.tags == ["test", "example"]

    def test_metadata_defaults(self):
        """Test metadata default values."""
        metadata = SeederMetadata(name="TestSeeder")

        assert metadata.name == "TestSeeder"
        assert metadata.description is None
        assert metadata.environments == ["all"]
        assert metadata.dependencies == []
        assert metadata.priority == 100
        assert metadata.batch_size == 1000
        assert metadata.can_rollback is False
        assert metadata.tags == []
