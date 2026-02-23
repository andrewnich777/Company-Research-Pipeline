"""Tests for data models."""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    CompanyProfile, CompanyType, Confidence, SourceTier,
    CustomerReviewInsights, LinkedInIntelligence
)


class TestCompanyProfile:
    """Test CompanyProfile model."""

    def test_minimal_profile(self):
        """Test creating a minimal company profile."""
        profile = CompanyProfile(
            name="Test Company",
            domain="test.com",
            company_type=CompanyType.STARTUP,
            industry="Technology"
        )
        assert profile.name == "Test Company"
        assert profile.domain == "test.com"
        assert profile.company_type == CompanyType.STARTUP
        assert profile.ticker is None
        assert profile.employee_count is None

    def test_full_profile(self):
        """Test creating a full company profile."""
        profile = CompanyProfile(
            name="Test Corp",
            legal_name="Test Corporation Inc.",
            domain="test.com",
            company_type=CompanyType.PUBLIC,
            ticker="TEST",
            industry="Finance",
            hq_location="New York, NY",
            employee_count="5000-10000",
            founded_year=1990,
            description="A test company"
        )
        assert profile.ticker == "TEST"
        assert profile.founded_year == 1990


class TestEnums:
    """Test enum values."""

    def test_company_type_values(self):
        """Test CompanyType enum values."""
        assert CompanyType.PUBLIC.value == "PUBLIC"
        assert CompanyType.PRIVATE_ENTERPRISE.value == "PRIVATE_ENTERPRISE"
        assert CompanyType.STARTUP.value == "STARTUP"

    def test_confidence_values(self):
        """Test Confidence enum values."""
        assert Confidence.HIGH.value == "HIGH"
        assert Confidence.MEDIUM.value == "MEDIUM"
        assert Confidence.LOW.value == "LOW"

    def test_source_tier_values(self):
        """Test SourceTier enum values."""
        assert SourceTier.TIER_0.value == "TIER_0"
        assert SourceTier.TIER_1.value == "TIER_1"
        assert SourceTier.TIER_2.value == "TIER_2"


class TestCustomerReviewInsights:
    """Test CustomerReviewInsights model validators."""

    def test_parse_float_rating(self):
        """Test parsing float rating."""
        insights = CustomerReviewInsights(average_rating=4.5)
        assert insights.average_rating == 4.5

    def test_parse_string_rating(self):
        """Test parsing string rating."""
        insights = CustomerReviewInsights(average_rating="4.5")
        assert insights.average_rating == 4.5

    def test_parse_fraction_rating(self):
        """Test parsing fraction rating format."""
        insights = CustomerReviewInsights(average_rating="4.5/5")
        assert insights.average_rating == 4.5

    def test_parse_na_rating(self):
        """Test parsing N/A rating returns None."""
        insights = CustomerReviewInsights(average_rating="N/A")
        assert insights.average_rating is None

    def test_parse_null_rating(self):
        """Test parsing null rating returns None."""
        insights = CustomerReviewInsights(average_rating=None)
        assert insights.average_rating is None


class TestLinkedInIntelligence:
    """Test LinkedInIntelligence model validators."""

    def test_parse_int_follower_count(self):
        """Test parsing integer follower count."""
        intel = LinkedInIntelligence(follower_count=15000)
        assert intel.follower_count == 15000

    def test_parse_string_follower_count(self):
        """Test parsing string follower count."""
        intel = LinkedInIntelligence(follower_count="15000")
        assert intel.follower_count == 15000

    def test_parse_k_suffix_follower_count(self):
        """Test parsing K suffix follower count."""
        intel = LinkedInIntelligence(follower_count="15K")
        assert intel.follower_count == 15000

    def test_parse_m_suffix_follower_count(self):
        """Test parsing M suffix follower count."""
        intel = LinkedInIntelligence(follower_count="1.5M")
        assert intel.follower_count == 1500000

    def test_parse_na_follower_count(self):
        """Test parsing N/A follower count returns None."""
        intel = LinkedInIntelligence(follower_count="N/A")
        assert intel.follower_count is None
