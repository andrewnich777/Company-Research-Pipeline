"""Pytest configuration and fixtures."""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def reset_config():
    """Reset configuration before each test."""
    import config
    config._config = None
    yield
    config._config = None


@pytest.fixture
def sample_company_profile():
    """Create a sample company profile for testing."""
    from models import CompanyProfile, CompanyType

    return CompanyProfile(
        name="Test Company",
        domain="test.com",
        company_type=CompanyType.STARTUP,
        industry="Technology",
        description="A test company for unit testing"
    )


@pytest.fixture
def sample_public_company_profile():
    """Create a sample public company profile for testing."""
    from models import CompanyProfile, CompanyType

    return CompanyProfile(
        name="Public Corp",
        legal_name="Public Corporation Inc.",
        domain="public.com",
        company_type=CompanyType.PUBLIC,
        ticker="PUB",
        industry="Finance",
        hq_location="New York, NY",
        employee_count="10000+",
        founded_year=1980,
        description="A large public company"
    )
