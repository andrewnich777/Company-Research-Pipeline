"""
Sales Brief Generator - Creates stakeholder-specific output for sales teams.
"""

from typing import Optional
from models import CompanyProfile, SynthesisOutput, ResearchResults
from .dedup import BriefDeduplicator
from .recommendation_engine import generate_score_based_recommendation, get_score_summary
from .evidence_classifier import classify_claim, format_badge, get_evidence_legend


# Industries that typically require BAA (Healthcare)
HEALTHCARE_INDICATORS = ["healthcare", "health", "medical", "pharma", "biotech", "hospital"]

# Industries with heavy regulatory burden
FINANCIAL_INDICATORS = ["finance", "financial", "banking", "insurance", "investment"]

# Process documentation tools we care about
PROCESS_TOOLS = ["confluence", "notion", "sharepoint", "servicenow", "jira", "monday"]


def _generate_contextual_questions(
    profile: CompanyProfile,
    research: ResearchResults
) -> list[str]:
    """
    Generate contextual discovery questions based on research findings.

    These are specific questions that fill gaps in our knowledge about the prospect.
    """
    questions = []
    industry_lower = profile.industry.lower() if profile.industry else ""

    # SSO/Identity questions
    has_sso = False
    if research.tech_stack:
        if research.tech_stack.identity_provider:
            has_sso = True
        for integration in research.tech_stack.integrations:
            if integration.category.lower() == "sso" or integration.tool_name.lower() in ["okta", "azure ad", "ping"]:
                has_sso = True
                break

    if not has_sso:
        questions.append("What identity provider do you currently use for SSO/SAML authentication?")

    # Healthcare/BAA questions
    is_healthcare = any(ind in industry_lower for ind in HEALTHCARE_INDICATORS)
    if is_healthcare:
        questions.append("Do you have a Business Associate Agreement (BAA) process we should be aware of?")
        questions.append("What HIPAA compliance requirements will apply to our deployment?")

    # Financial services questions
    is_financial = any(ind in industry_lower for ind in FINANCIAL_INDICATORS)
    if is_financial:
        questions.append("What regulatory frameworks govern your process automation initiatives (SOX, FINRA, etc.)?")

    # EU/GDPR questions - check for EU operations
    has_eu_operations = False
    if research.financials and research.financials.geographic_operations:
        for region in research.financials.geographic_operations:
            if any(eu in region.lower() for eu in ["europe", "eu", "emea", "germany", "france", "uk"]):
                has_eu_operations = True
                break

    if has_eu_operations:
        questions.append("Will works council approval be required for any EU employee-facing deployments?")
        questions.append("What data residency requirements apply to your European operations?")

    # Process tool-specific questions
    found_tools = []
    if research.tech_stack:
        for integration in research.tech_stack.integrations:
            tool_lower = integration.tool_name.lower()
            for tool in PROCESS_TOOLS:
                if tool in tool_lower:
                    found_tools.append(integration.tool_name)
                    break

    for tool in found_tools[:2]:  # Limit to 2 tool-specific questions
        questions.append(f"How are you currently documenting and maintaining workflows in {tool}?")

    # Security maturity questions
    if research.security:
        if not research.security.certifications:
            questions.append("What security certifications are you currently pursuing or planning?")

        if not research.security.trust_center_url:
            questions.append("Do you have a security questionnaire or vendor assessment process?")

    # AI/Automation readiness
    has_ai_initiatives = False
    if research.strategic and research.strategic.ai_initiatives:
        has_ai_initiatives = True

    if not has_ai_initiatives:
        questions.append("What automation or AI initiatives are currently in progress or planned?")
    else:
        questions.append("How has your organization approached AI governance and oversight so far?")

    # Data residency - if we didn't find specific info
    if research.security and not research.security.data_residency:
        questions.append("Are there specific data residency requirements for your deployment?")

    return questions


def _format_ai_talking_points(talking_points: list) -> list[str]:
    """Format AI-generated talking points."""
    lines = []
    if not talking_points:
        return lines

    lines.append("## AI-Generated Talking Points")
    lines.append("")

    for tp in talking_points[:5]:
        topic = tp.get("topic", "General")
        point = tp.get("point", "")
        source = tp.get("source", "")
        objection = tp.get("objection", "")
        response = tp.get("response", "")

        lines.append(f"### {topic}")
        lines.append("")
        lines.append(f"**Point:** {point}")
        if source:
            lines.append(f"*Source: {source}*")
        lines.append("")

        if objection and response:
            lines.append(f"**Likely Objection:** {objection}")
            lines.append(f"**Response:** {response}")
            lines.append("")

    return lines


def _format_ai_objection_handlers(handlers: list) -> list[str]:
    """Format AI-generated objection handlers."""
    lines = []
    if not handlers:
        return lines

    lines.append("## Objection Handlers")
    lines.append("")
    lines.append("| Objection | Response | Evidence |")
    lines.append("|-----------|----------|----------|")

    for handler in handlers[:5]:
        objection = handler.get("objection", "").replace("|", "\\|")
        response = handler.get("response", "").replace("|", "\\|")
        evidence = handler.get("evidence", "").replace("|", "\\|")
        lines.append(f"| {objection} | {response} | {evidence} |")

    lines.append("")
    return lines


def _format_ai_champion_engagement(champion: dict) -> list[str]:
    """Format AI-generated champion engagement strategy."""
    lines = []
    if not champion or not champion.get("primary"):
        return lines

    lines.append("## Champion Engagement Strategy")
    lines.append("")
    lines.append(f"**Primary Target:** {champion.get('primary', 'Unknown')}")
    lines.append("")
    if champion.get("why"):
        lines.append(f"**Why This Person:** {champion.get('why')}")
        lines.append("")
    if champion.get("approach"):
        lines.append(f"**Recommended Approach:** {champion.get('approach')}")
        lines.append("")

    return lines


def _format_ai_competitive_positioning(positioning: dict) -> list[str]:
    """Format AI-generated competitive positioning."""
    lines = []
    if not positioning:
        return lines

    competitors = positioning.get("competitors", [])
    differentiation = positioning.get("differentiation", [])
    win_themes = positioning.get("win_themes", [])

    if not (competitors or differentiation or win_themes):
        return lines

    lines.append("## Competitive Positioning")
    lines.append("")

    if competitors:
        lines.append(f"**Competitors in Play:** {', '.join(competitors)}")
        lines.append("")

    if differentiation:
        lines.append("**Key Differentiators:**")
        for diff in differentiation[:5]:
            lines.append(f"- {diff}")
        lines.append("")

    if win_themes:
        lines.append("**Win Themes:**")
        for theme in win_themes[:3]:
            lines.append(f"- {theme}")
        lines.append("")

    return lines


def _format_ai_deal_velocity(signals: dict) -> list[str]:
    """Format AI-generated deal velocity signals."""
    lines = []
    if not signals:
        return lines

    positive = signals.get("positive", [])
    negative = signals.get("negative", [])
    timeline = signals.get("recommended_timeline", "")

    if not (positive or negative or timeline):
        return lines

    lines.append("## Deal Velocity Signals")
    lines.append("")

    if positive:
        lines.append("**Positive Signals:**")
        for sig in positive[:4]:
            lines.append(f"- :green_circle: {sig}")
        lines.append("")

    if negative:
        lines.append("**Negative Signals:**")
        for sig in negative[:4]:
            lines.append(f"- :red_circle: {sig}")
        lines.append("")

    if timeline:
        lines.append(f"**Recommended Timeline:** {timeline}")
        lines.append("")

    return lines


def generate_sales_brief(
    profile: CompanyProfile,
    synthesis: SynthesisOutput,
    research: ResearchResults,
    ai_refinements: Optional[dict] = None
) -> str:
    """
    Generate a sales-focused brief with talking points and discovery questions.

    Args:
        profile: Company profile data
        synthesis: Synthesis output with scores and recommendations
        research: Research results from all agents
        ai_refinements: Optional AI-generated refinements from BriefRefinerAgent

    Returns markdown-formatted string.
    """
    lines = []

    # Header
    lines.append(f"# Sales Brief: {profile.name}")
    lines.append("")
    lines.append(f"**Fluency AI Pre-Sales Positioning**")
    lines.append("")
    lines.append(f"*See Executive Brief for full company intelligence, blockers, and discovery questions.*")
    lines.append("")

    # Deployment Readiness Score
    score = synthesis.deployment_score
    lines.append("## Deployment Readiness Score")
    lines.append("")
    lines.append(f"### Overall: {score.overall:.1f}/10")
    lines.append("")
    lines.append(f"| Factor | Score | Notes |")
    lines.append(f"|--------|-------|-------|")
    lines.append(f"| Security Maturity | {score.security_maturity}/10 | Weight: 25% |")
    lines.append(f"| Integration Fit | {score.integration_fit}/10 | Weight: 25% |")
    lines.append(f"| Compliance Complexity | {score.compliance_complexity}/10 | Weight: 20% |")
    lines.append(f"| Strategic Alignment | {score.strategic_alignment}/10 | Weight: 15% |")
    lines.append(f"| Deal Complexity | {score.deal_complexity}/10 | Weight: 15% |")
    lines.append("")
    lines.append(f"**Rationale:** {score.rationale}")
    lines.append("")

    # Key Opportunities
    lines.append("## Key Opportunities")
    lines.append("")
    if synthesis.opportunities:
        for opp in synthesis.opportunities:
            lines.append(f"- {opp}")
    else:
        lines.append("- No specific opportunities identified")
    lines.append("")

    # AI-Generated Sections (if available)
    if ai_refinements:
        # Talking Points
        lines.extend(_format_ai_talking_points(ai_refinements.get("talking_points", [])))

        # Objection Handlers
        lines.extend(_format_ai_objection_handlers(ai_refinements.get("objection_handlers", [])))

        # Champion Engagement
        lines.extend(_format_ai_champion_engagement(ai_refinements.get("champion_engagement", {})))

        # Competitive Positioning
        lines.extend(_format_ai_competitive_positioning(ai_refinements.get("competitive_positioning", {})))

        # Deal Velocity Signals
        lines.extend(_format_ai_deal_velocity(ai_refinements.get("deal_velocity_signals", {})))

    # Recommended Approach - Score-based first, then AI-generated context
    lines.append("## Recommended Sales Approach")
    lines.append("")

    # Primary: Score-based recommendation with explicit score references
    score_recommendation = generate_score_based_recommendation(synthesis.deployment_score)
    lines.append(f"**Based on Scores:** {score_recommendation}")
    lines.append("")

    # Secondary: AI-generated context if available
    if synthesis.recommended_approach:
        lines.append(f"**Additional Context:** {synthesis.recommended_approach}")
        lines.append("")

    # Score summary for quick reference
    lines.append(f"*{get_score_summary(synthesis.deployment_score)}*")
    lines.append("")

    # Strategic Context - with within-document deduplication
    lines.append("## Strategic Context")
    lines.append("")

    # Use deduplicator to track seen claims within this brief
    with BriefDeduplicator() as dedup:
        # AI Initiatives (deduplicated)
        if research.strategic and research.strategic.ai_initiatives:
            lines.append("### AI/Automation Initiatives")
            lines.append("")
            unique_initiatives = dedup.claims(research.strategic.ai_initiatives[:5])
            for claim in unique_initiatives:
                ev_class, has_conflict = classify_claim(claim)
                badge = format_badge(ev_class, has_conflict)
                lines.append(f"- {claim.claim} {badge}")
                if claim.evidence:
                    lines.append(f"  - Source: {claim.evidence[0].url}")
            lines.append("")

        # Executive Quotes (deduplicated)
        if research.strategic and research.strategic.executive_quotes:
            lines.append("### Executive Quotes")
            lines.append("")
            unique_quotes = dedup.claims(research.strategic.executive_quotes[:3])
            for quote in unique_quotes:
                ev_class, has_conflict = classify_claim(quote)
                badge = format_badge(ev_class, has_conflict)
                lines.append(f"> {quote.claim} {badge}")
                if quote.evidence:
                    lines.append(f"> — Source: {quote.evidence[0].url}")
                lines.append("")

        # Recent News (deduplicated)
        if research.strategic and research.strategic.recent_news:
            lines.append("### Recent News")
            lines.append("")
            unique_news = dedup.claims(research.strategic.recent_news[:5])
            for news in unique_news:
                ev_class, has_conflict = classify_claim(news)
                badge = format_badge(ev_class, has_conflict)
                lines.append(f"- {news.claim} {badge}")
                if news.evidence:
                    lines.append(f"  - Source: {news.evidence[0].url}")
            lines.append("")

    # Technology Fit (summary only - see Product Brief for full integration details)
    lines.append("## Technology Fit")
    lines.append("")
    if research.tech_stack:
        tech = research.tech_stack
        if tech.identity_provider:
            lines.append(f"**Identity Provider:** {tech.identity_provider}")
        if tech.cloud_provider:
            lines.append(f"**Cloud Provider:** {tech.cloud_provider}")
        if tech.integrations:
            lines.append(f"**Integrations Found:** {len(tech.integrations)} *(see Product Brief for details)*")
        lines.append("")
    else:
        lines.append("*Tech stack details pending - see Product Brief*")
        lines.append("")

    # Contradictions
    if synthesis.contradictions:
        lines.append("## Contradictions/Uncertainties")
        lines.append("")
        for contradiction in synthesis.contradictions:
            lines.append(f"- **{contradiction.get('claim_a', 'Claim A')}** vs **{contradiction.get('claim_b', 'Claim B')}**")
            lines.append(f"  - Status: {contradiction.get('resolution', 'Unknown')}")
            if contradiction.get('note'):
                lines.append(f"  - Note: {contradiction['note']}")
        lines.append("")

    # Evidence Legend
    lines.extend(get_evidence_legend())

    # Footer
    lines.append("*Generated by Fluency AI Research Agent*")

    return "\n".join(lines)
