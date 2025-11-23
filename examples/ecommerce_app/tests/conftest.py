"""Pytest configuration and fixtures for tests."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="testpass123",  # gitleaks:allow
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="admin123",  # gitleaks:allow
        first_name="Admin",
        last_name="User",
    )
