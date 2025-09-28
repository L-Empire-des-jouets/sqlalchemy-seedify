"""
Custom exceptions for sqlalchemy-seedify
"""


class SeederError(Exception):
    """Base exception for seeder-related errors"""
    pass


class DuplicateSeederError(SeederError):
    """Raised when attempting to register a seeder with an existing name"""
    pass


class SeederNotFoundError(SeederError):
    """Raised when attempting to run a seeder that doesn't exist"""
    pass