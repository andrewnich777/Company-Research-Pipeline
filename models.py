"""
Pydantic models for the Fluency AI Deployment Research Agent.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class CompanyType(str, Enum):
    PUBLIC = "PUBLIC"
    PRIVATE_ENTERPRISE = "PRIVATE_ENTERPRISE"
    STARTUP = "STARTUP"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class SourceTier(str, Enum):
    TIER_0 = "TIER_0"  # Primary sources (company domain, SEC, official)
    TIER_1 = "TIER_1"  # Strong secondary (major news, analysts)
    TIER_2 = "TIER_2"  # Weak sources (blogs, forums)


# ============================================================================
# Stage 1: Discovery
# ============================================================================

class CompanyProfile(BaseModel):
    """Output from Discovery Agent - basic company identification."""

    name: str = Field(description="Official company name")
    legal_name: Optional[str] = Field(default=None, description="Legal entity name if different")
    domain: str = Field(description="Primary website domain")
    company_type: CompanyType = Field(description="Classification: PUBLIC, PRIVATE_ENTERPRISE, or STARTUP")
    ticker: Optional[str] = Field(default=None, description="Stock ticker if public company")
    industry: str = Field(description="Primary industry vertical")
    hq_location: Optional[str] = Field(default=None, description="Headquarters location")
    employee_count: Optional[str] = Field(default=None, description="Estimated employee count or range")
    founded_year: Optional[int] = Field(default=None, description="Year founded")
    description: str = Field(default="", description="Brief company description")


# ============================================================================
# Stage 2: Research Findings
# ============================================================================

class Evidence(BaseModel):
    """A piece of evidence supporting a claim."""

    url: str = Field(description="Source URL")
    quote: str = Field(default="", description="Relevant quote or excerpt")
    source_type: str = Field(description="Type of source (trust_center, news, sec_filing, etc.)")
    source_tier: SourceTier = Field(default=SourceTier.TIER_2, description="Quality tier of the source")
    fetched_at: datetime = Field(default_factory=datetime.now)


class Claim(BaseModel):
    """A factual claim with supporting evidence."""

    claim: str = Field(description="The factual claim")
    category: str = Field(description="Category: Security, Tech Stack, Strategic, Financial")
    confidence: Confidence = Field(default=Confidence.MEDIUM, description="Confidence level")
    evidence: list[Evidence] = Field(default_factory=list)


class Certification(BaseModel):
    """A security/compliance certification."""

    name: str = Field(description="Certification name (SOC 2, ISO 27001, etc.)")
    status: str = Field(default="claimed", description="certified, in_progress, claimed")
    evidence: Optional[Evidence] = None


class Integration(BaseModel):
    """A confirmed or inferred technology integration."""

    tool_name: str = Field(description="Name of the tool/platform")
    category: str = Field(description="Category: SSO, CRM, Cloud, etc.")
    confidence: Confidence = Field(default=Confidence.MEDIUM, description="Confidence level")
    evidence: Optional[Evidence] = None


class SecurityFindings(BaseModel):
    """Output from Security Research Agent."""

    trust_center_url: Optional[str] = None
    certifications: list[Certification] = Field(default_factory=list)
    data_residency: list[str] = Field(default_factory=list, description="Regions where data is stored")
    security_incidents: list[Claim] = Field(default_factory=list)
    privacy_requirements: list[str] = Field(default_factory=list)
    security_maturity: str = Field(default="UNKNOWN", description="HIGH, MEDIUM, LOW, UNKNOWN")
    claims: list[Claim] = Field(default_factory=list)


class TechStackFindings(BaseModel):
    """Output from Tech Stack Research Agent."""

    integrations: list[Integration] = Field(default_factory=list)
    identity_provider: Optional[str] = None
    cloud_provider: Optional[str] = None
    subdomains_found: list[str] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)


class StrategicFindings(BaseModel):
    """Output from Strategic Research Agent."""

    recent_news: list[Claim] = Field(default_factory=list)
    ai_initiatives: list[Claim] = Field(default_factory=list)
    partnerships: list[Claim] = Field(default_factory=list)
    mna_activity: list[Claim] = Field(default_factory=list)
    executive_quotes: list[Claim] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)


class FinancialFindings(BaseModel):
    """Output from Financials Research Agent (PUBLIC companies only)."""

    cik: Optional[str] = None
    recent_10k_url: Optional[str] = None
    risk_factors: list[str] = Field(default_factory=list)
    geographic_operations: list[str] = Field(default_factory=list)
    regulatory_mentions: list[str] = Field(default_factory=list)
    revenue: Optional[str] = None
    claims: list[Claim] = Field(default_factory=list)


class JobPostingInsights(BaseModel):
    """Output from Job Postings Agent - reveals real tech stack and hiring signals."""

    total_open_roles: int = Field(default=0, description="Total number of open positions found")
    engineering_roles: int = Field(default=0, description="Number of engineering/technical roles")
    technologies_mentioned: list[str] = Field(default_factory=list, description="Technologies found in job requirements")
    tech_stack_signals: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Tech categorized by type: {infrastructure: [], languages: [], tools: []}"
    )
    hiring_velocity: str = Field(default="UNKNOWN", description="HIGH, MEDIUM, LOW, UNKNOWN")
    team_growth_areas: list[str] = Field(default_factory=list, description="Departments with most hiring")
    seniority_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Count by level: {senior: 5, mid: 10, junior: 3}"
    )
    process_tools_mentioned: list[str] = Field(default_factory=list, description="Confluence, Jira, ServiceNow, etc.")
    remote_policy: Optional[str] = Field(default=None, description="Remote, Hybrid, On-site, Unknown")
    job_board_sources: list[str] = Field(default_factory=list, description="Where jobs were found")
    claims: list[Claim] = Field(default_factory=list)


class CustomerReviewInsights(BaseModel):
    """Output from Customer Reviews Agent - real pain points from G2/Capterra."""

    overall_sentiment: str = Field(default="UNKNOWN", description="POSITIVE, MIXED, NEGATIVE, UNKNOWN")
    average_rating: Optional[float] = Field(default=None, description="Average star rating if available")
    total_reviews_analyzed: int = Field(default=0)

    @field_validator('average_rating', mode='before')
    @classmethod
    def parse_rating(cls, v):
        """Handle various rating formats: 4.5, '4.5', '4.5/5', 'N/A', None."""
        if v is None or v == "" or v == "N/A" or v == "null":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            # Handle "4.5/5" format
            if "/" in v:
                v = v.split("/")[0]
            try:
                return float(v.strip())
            except ValueError:
                return None
        return None
    pain_points: list[str] = Field(default_factory=list, description="Negative themes from reviews")
    integration_challenges: list[str] = Field(default_factory=list, description="Integration issues mentioned")
    competitor_mentions: list[dict] = Field(
        default_factory=list,
        description="[{competitor: 'X', context: 'switched from X because...'}]"
    )
    implementation_signals: list[str] = Field(default_factory=list, description="Time-to-value, onboarding mentions")
    positive_themes: list[str] = Field(default_factory=list, description="What customers like")
    review_sources: list[str] = Field(default_factory=list, description="G2, Capterra, TrustRadius, etc.")
    claims: list[Claim] = Field(default_factory=list)


class RegulatoryRiskInsights(BaseModel):
    """Output from Regulatory Risk Agent - compliance issues and legal exposure."""

    enforcement_actions: list[Claim] = Field(default_factory=list, description="FTC, SEC, state AG actions")
    data_breaches: list[Claim] = Field(default_factory=list, description="Known data breach history")
    active_litigation: list[Claim] = Field(default_factory=list, description="Pending lawsuits")
    settlements: list[Claim] = Field(default_factory=list, description="Past settlements or consent decrees")
    gdpr_issues: list[Claim] = Field(default_factory=list, description="GDPR fines or investigations")
    regulatory_exposure: list[str] = Field(
        default_factory=list,
        description="Industries/regulations that apply: HIPAA, SOX, PCI, etc."
    )
    risk_level: str = Field(default="UNKNOWN", description="HIGH, MEDIUM, LOW, UNKNOWN")
    claims: list[Claim] = Field(default_factory=list)


class Stakeholder(BaseModel):
    """Individual stakeholder/decision maker record."""

    name: str = Field(description="Full name")
    title: str = Field(description="Job title")
    department: Optional[str] = Field(default=None, description="Engineering, IT, Operations, etc.")
    linkedin_url: Optional[str] = Field(default=None)
    background: Optional[str] = Field(default=None, description="Previous companies, expertise areas")
    relevance: str = Field(
        default="UNKNOWN",
        description="CHAMPION, DECISION_MAKER, INFLUENCER, BLOCKER, UNKNOWN"
    )
    champion_signals: list[str] = Field(default_factory=list, description="Why they might advocate")
    evidence: Optional[Evidence] = None


class StakeholderIntelligence(BaseModel):
    """Output from Stakeholder Intelligence Agent - decision maker mapping."""

    technical_leaders: list[Stakeholder] = Field(default_factory=list, description="CTO, VP Eng, etc.")
    executive_team: list[Stakeholder] = Field(default_factory=list, description="C-suite identified")
    procurement_contacts: list[Stakeholder] = Field(default_factory=list, description="CPO, vendor management")
    potential_champions: list[Stakeholder] = Field(default_factory=list, description="Likely internal advocates")
    org_structure_signals: list[str] = Field(
        default_factory=list,
        description="Centralized IT, federated buying, etc."
    )
    recent_executive_changes: list[Claim] = Field(default_factory=list, description="New hires, departures")
    conference_speakers: list[Stakeholder] = Field(
        default_factory=list,
        description="Executives who speak at events"
    )
    github_contributors: list[str] = Field(default_factory=list, description="Active OSS contributors from company")
    claims: list[Claim] = Field(default_factory=list)


class LinkedInIntelligence(BaseModel):
    """Output from LinkedIn Intelligence Agent - company/executive social presence."""

    company_linkedin_url: Optional[str] = Field(default=None, description="Company LinkedIn page URL")
    follower_count: Optional[int] = Field(default=None, description="Company follower count if available")

    @field_validator('follower_count', mode='before')
    @classmethod
    def parse_follower_count(cls, v):
        """Handle various follower count formats: 15000, '15000', '15K', '1.5M', None."""
        if v is None or v == "" or v == "N/A" or v == "null" or v == "Unknown":
            return None
        if isinstance(v, int):
            return v
        if isinstance(v, float):
            return int(v)
        if isinstance(v, str):
            v = v.strip().replace(",", "")
            # Handle K/M suffixes
            if v.upper().endswith("K"):
                try:
                    return int(float(v[:-1]) * 1000)
                except ValueError:
                    return None
            elif v.upper().endswith("M"):
                try:
                    return int(float(v[:-1]) * 1000000)
                except ValueError:
                    return None
            try:
                return int(v)
            except ValueError:
                return None
        return None

    # Executive profiles
    executives_found: list[dict] = Field(
        default_factory=list,
        description="[{name, title, linkedin_url, recent_topics}]"
    )

    # Content analysis
    posts_analyzed: int = Field(default=0, description="Number of posts analyzed")
    recent_post_themes: list[str] = Field(
        default_factory=list,
        description="Key topics from company/exec posts"
    )

    # Strategic signals
    strategic_initiatives: list[str] = Field(
        default_factory=list,
        description="Announced priorities, transformations"
    )
    hiring_announcements: list[str] = Field(
        default_factory=list,
        description="Hiring/growth announcements from posts"
    )
    thought_leadership_topics: list[str] = Field(
        default_factory=list,
        description="What executives publicly discuss"
    )

    # Culture signals
    culture_signals: list[str] = Field(
        default_factory=list,
        description="Values, remote/hybrid, diversity mentions"
    )

    claims: list[Claim] = Field(default_factory=list)


class ResearchResults(BaseModel):
    """Combined research from all Stage 2 agents."""

    security: Optional[SecurityFindings] = None
    tech_stack: Optional[TechStackFindings] = None
    strategic: Optional[StrategicFindings] = None
    financials: Optional[FinancialFindings] = None
    # Deep intelligence agents
    job_postings: Optional[JobPostingInsights] = None
    customer_reviews: Optional[CustomerReviewInsights] = None
    regulatory_risk: Optional[RegulatoryRiskInsights] = None
    stakeholders: Optional[StakeholderIntelligence] = None
    linkedin_intel: Optional[LinkedInIntelligence] = None


# ============================================================================
# Stage 3: Synthesis
# ============================================================================

class EvidenceGraph(BaseModel):
    """Complete evidence graph from synthesis."""

    security_claims: list[Claim] = Field(default_factory=list)
    technology_claims: list[Claim] = Field(default_factory=list)
    strategic_claims: list[Claim] = Field(default_factory=list)
    financial_claims: list[Claim] = Field(default_factory=list)
    # Deep intelligence claims
    hiring_claims: list[Claim] = Field(default_factory=list)
    customer_sentiment_claims: list[Claim] = Field(default_factory=list)
    regulatory_claims: list[Claim] = Field(default_factory=list)
    stakeholder_claims: list[Claim] = Field(default_factory=list)


class DeploymentScore(BaseModel):
    """Deployment readiness assessment."""

    security_maturity: int = Field(default=5, ge=0, le=10)
    integration_fit: int = Field(default=5, ge=0, le=10)
    compliance_complexity: int = Field(default=5, ge=0, le=10)
    strategic_alignment: int = Field(default=5, ge=0, le=10)
    deal_complexity: int = Field(default=5, ge=0, le=10)
    # New scoring dimensions from deep intelligence
    champion_identified: int = Field(default=5, ge=0, le=10, description="Have we identified potential internal champions?")
    procurement_clarity: int = Field(default=5, ge=0, le=10, description="How clear is the procurement process?")
    regulatory_risk: int = Field(default=5, ge=0, le=10, description="Level of regulatory/legal exposure")
    overall: float = Field(default=5.0, ge=0, le=10)
    rationale: str = Field(default="")


class SynthesisOutput(BaseModel):
    """Output from Synthesis Agent."""

    evidence_graph: EvidenceGraph = Field(default_factory=EvidenceGraph)
    contradictions: list[dict] = Field(default_factory=list)
    deployment_score: DeploymentScore = Field(default_factory=DeploymentScore)
    opportunities: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    recommended_approach: str = Field(default="")
    discovery_questions: list[str] = Field(default_factory=list)


# ============================================================================
# Final Output
# ============================================================================

class ResearchOutput(BaseModel):
    """Complete research output for a company."""

    profile: CompanyProfile
    research: ResearchResults
    synthesis: SynthesisOutput
    sales_brief: str = Field(default="")
    security_brief: str = Field(default="")
    product_brief: str = Field(default="")
    executive_brief: str = Field(default="", description="Overall deal intelligence brief")
    generated_at: datetime = Field(default_factory=datetime.now)
    duration_seconds: float = Field(default=0.0)
