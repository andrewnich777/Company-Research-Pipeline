"""
Sales Brief Generator - Creates stakeholder-specific output for sales teams.
"""

from models import CompanyProfile, SynthesisOutput, ResearchResults


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


def generate_sales_brief(
    profile: CompanyProfile,
    synthesis: SynthesisOutput,
    research: ResearchResults
) -> str:
    """
    Generate a sales-focused brief with talking points and discovery questions.

    Returns markdown-formatted string.
    """
    lines = []

    # Header
    lines.append(f"# Sales Brief: {profile.name}")
    lines.append("")
    lines.append(f"**Generated for Fluency AI Pre-Sales**")
    lines.append("")

    # Company Snapshot
    lines.append("## Company Snapshot")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| **Company** | {profile.name} |")
    lines.append(f"| **Industry** | {profile.industry} |")
    lines.append(f"| **Type** | {profile.company_type.value} |")
    lines.append(f"| **Headquarters** | {profile.hq_location or 'Unknown'} |")
    lines.append(f"| **Employees** | {profile.employee_count or 'Unknown'} |")
    if profile.ticker:
        lines.append(f"| **Ticker** | {profile.ticker} |")
    lines.append("")
    lines.append(f"> {profile.description}")
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

    # Potential Blockers
    lines.append("## Potential Blockers")
    lines.append("")
    if synthesis.blockers:
        for blocker in synthesis.blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- No significant blockers identified")
    lines.append("")

    # Recommended Approach
    lines.append("## Recommended Sales Approach")
    lines.append("")
    lines.append(synthesis.recommended_approach or "Standard enterprise approach recommended.")
    lines.append("")

    # Discovery Questions (Enhanced with contextual questions)
    lines.append("## Discovery Call Questions")
    lines.append("")

    discovery_questions = []

    # Start with synthesized questions
    if synthesis.discovery_questions:
        discovery_questions.extend(synthesis.discovery_questions)

    # Add contextual questions based on findings
    contextual_questions = _generate_contextual_questions(profile, research)
    for q in contextual_questions:
        if q not in discovery_questions:
            discovery_questions.append(q)

    # Default questions if still empty
    if not discovery_questions:
        discovery_questions = [
            "What are your current process documentation challenges?",
            "How do you ensure compliance with regulatory requirements?",
            "What automation initiatives are currently in progress?",
        ]

    for i, question in enumerate(discovery_questions[:10], 1):
        lines.append(f"{i}. {question}")
    lines.append("")

    # Strategic Context
    lines.append("## Strategic Context")
    lines.append("")

    # AI Initiatives
    if research.strategic and research.strategic.ai_initiatives:
        lines.append("### AI/Automation Initiatives")
        lines.append("")
        for claim in research.strategic.ai_initiatives[:5]:
            lines.append(f"- {claim.claim}")
            if claim.evidence:
                lines.append(f"  - Source: {claim.evidence[0].url}")
        lines.append("")

    # Executive Quotes
    if research.strategic and research.strategic.executive_quotes:
        lines.append("### Executive Quotes")
        lines.append("")
        for quote in research.strategic.executive_quotes[:3]:
            lines.append(f"> {quote.claim}")
            if quote.evidence:
                lines.append(f"> — Source: {quote.evidence[0].url}")
            lines.append("")

    # Recent News
    if research.strategic and research.strategic.recent_news:
        lines.append("### Recent News")
        lines.append("")
        for news in research.strategic.recent_news[:5]:
            lines.append(f"- {news.claim}")
            if news.evidence:
                lines.append(f"  - Source: {news.evidence[0].url}")
        lines.append("")

    # Technology Fit
    lines.append("## Technology Fit")
    lines.append("")
    if research.tech_stack:
        tech = research.tech_stack
        if tech.identity_provider:
            lines.append(f"**Identity Provider:** {tech.identity_provider}")
        if tech.cloud_provider:
            lines.append(f"**Cloud Provider:** {tech.cloud_provider}")
        lines.append("")

        if tech.integrations:
            lines.append("### Confirmed Integrations")
            lines.append("")
            for integration in tech.integrations:
                confidence_badge = "HIGH" if integration.confidence.value == "HIGH" else integration.confidence.value
                lines.append(f"- **{integration.tool_name}** ({integration.category}) - {confidence_badge}")
            lines.append("")

    # Evidence Summary
    lines.append("## Evidence Summary")
    lines.append("")
    lines.append(f"| Category | Claims | High Confidence |")
    lines.append(f"|----------|--------|-----------------|")

    sec_claims = len(synthesis.evidence_graph.security_claims)
    sec_high = sum(1 for c in synthesis.evidence_graph.security_claims if c.confidence.value == "HIGH")
    lines.append(f"| Security | {sec_claims} | {sec_high} |")

    tech_claims = len(synthesis.evidence_graph.technology_claims)
    tech_high = sum(1 for c in synthesis.evidence_graph.technology_claims if c.confidence.value == "HIGH")
    lines.append(f"| Technology | {tech_claims} | {tech_high} |")

    strat_claims = len(synthesis.evidence_graph.strategic_claims)
    strat_high = sum(1 for c in synthesis.evidence_graph.strategic_claims if c.confidence.value == "HIGH")
    lines.append(f"| Strategic | {strat_claims} | {strat_high} |")

    fin_claims = len(synthesis.evidence_graph.financial_claims)
    fin_high = sum(1 for c in synthesis.evidence_graph.financial_claims if c.confidence.value == "HIGH")
    lines.append(f"| Financial | {fin_claims} | {fin_high} |")
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

    # Footer
    lines.append("---")
    lines.append("*Generated by Fluency AI Research Agent*")

    return "\n".join(lines)
