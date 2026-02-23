"""
Product Brief Generator - Creates stakeholder-specific output for product teams.
"""

from typing import Optional
from models import CompanyProfile, SynthesisOutput, ResearchResults
from .dedup import deduplicate_by_field
from .evidence_classifier import classify_integration, format_badge, get_evidence_legend


def _format_ai_integration_complexity(complexity: dict) -> list[str]:
    """Format AI-generated integration complexity assessment."""
    lines = []
    if not complexity:
        return lines

    overall = complexity.get("overall", "Unknown")
    factors = complexity.get("factors", [])

    lines.append("## Integration Complexity Assessment")
    lines.append("")
    lines.append(f"**Overall Complexity: {overall}**")
    lines.append("")

    if factors:
        lines.append("| System | Complexity | Notes |")
        lines.append("|--------|------------|-------|")
        for factor in factors[:8]:
            system = factor.get("system", "Unknown").replace("|", "\\|")
            comp = factor.get("complexity", "Unknown")
            notes = factor.get("notes", "").replace("|", "\\|")
            lines.append(f"| {system} | {comp} | {notes} |")
        lines.append("")

    return lines


def _format_ai_tech_compatibility(compatibility: dict) -> list[str]:
    """Format AI-generated tech stack compatibility."""
    lines = []
    if not compatibility:
        return lines

    compatible = compatibility.get("compatible", [])
    needs_verification = compatibility.get("needs_verification", [])
    blockers = compatibility.get("blockers", [])

    if not (compatible or needs_verification or blockers):
        return lines

    lines.append("## Tech Stack Compatibility")
    lines.append("")

    if compatible:
        lines.append("**Compatible Technologies:**")
        for tech in compatible[:6]:
            lines.append(f"- :white_check_mark: {tech}")
        lines.append("")

    if needs_verification:
        lines.append("**Needs Verification:**")
        for tech in needs_verification[:4]:
            lines.append(f"- :question: {tech}")
        lines.append("")

    if blockers:
        lines.append("**Potential Blockers:**")
        for blocker in blockers[:3]:
            lines.append(f"- :x: {blocker}")
        lines.append("")

    return lines


def _format_ai_implementation_roadmap(roadmap: dict) -> list[str]:
    """Format AI-generated implementation roadmap."""
    lines = []
    if not roadmap:
        return lines

    approach = roadmap.get("approach", "Unknown")
    phases = roadmap.get("phases", [])

    if not phases:
        return lines

    lines.append("## Recommended Implementation Roadmap")
    lines.append("")
    lines.append(f"**Approach: {approach}**")
    lines.append("")

    for phase in phases[:4]:
        phase_num = phase.get("phase", "?")
        duration = phase.get("duration", "TBD")
        scope = phase.get("scope", "")

        lines.append(f"### Phase {phase_num} ({duration})")
        lines.append("")
        if scope:
            lines.append(f"{scope}")
            lines.append("")

    return lines


def _format_ai_deployment_risks(risks: list) -> list[str]:
    """Format AI-generated deployment risks."""
    lines = []
    if not risks:
        return lines

    lines.append("## Deployment Risks")
    lines.append("")
    lines.append("| Risk | Probability | Impact | Mitigation |")
    lines.append("|------|-------------|--------|------------|")

    for risk in risks[:6]:
        risk_desc = risk.get("risk", "").replace("|", "\\|")
        probability = risk.get("probability", "UNKNOWN")
        impact = risk.get("impact", "UNKNOWN")
        mitigation = risk.get("mitigation", "").replace("|", "\\|")
        lines.append(f"| {risk_desc} | {probability} | {impact} | {mitigation} |")

    lines.append("")
    return lines


def _format_ai_success_factors(factors: list) -> list[str]:
    """Format AI-generated success factors."""
    lines = []
    if not factors:
        return lines

    lines.append("## Critical Success Factors")
    lines.append("")

    for i, factor in enumerate(factors[:6], 1):
        lines.append(f"{i}. {factor}")

    lines.append("")
    return lines


def generate_product_brief(
    profile: CompanyProfile,
    synthesis: SynthesisOutput,
    research: ResearchResults,
    ai_refinements: Optional[dict] = None
) -> str:
    """
    Generate a product-focused brief for implementation planning.

    Args:
        profile: Company profile data
        synthesis: Synthesis output with scores and recommendations
        research: Research results from all agents
        ai_refinements: Optional AI-generated refinements from BriefRefinerAgent

    Returns markdown-formatted string.
    """
    lines = []

    # Header
    lines.append(f"# Product Brief: {profile.name}")
    lines.append("")
    lines.append(f"**Fluency AI Implementation Planning**")
    lines.append("")

    # Company Context (minimal - see Executive Brief for full intel)
    lines.append("## Company Context")
    lines.append("")
    lines.append(f"**{profile.name}** | {profile.company_type.value} | {profile.employee_count or 'Unknown'} employees")
    lines.append("")

    # Integration Landscape
    lines.append("## Integration Landscape")
    lines.append("")
    score = synthesis.deployment_score
    lines.append(f"**Integration Fit Score: {score.integration_fit}/10**")
    lines.append("")

    if research.tech_stack:
        tech = research.tech_stack

        # Core Infrastructure
        lines.append("### Core Infrastructure")
        lines.append("")
        lines.append(f"| Component | Detected | Evidence |")
        lines.append(f"|-----------|----------|----------|")
        lines.append(f"| Identity Provider | {tech.identity_provider or 'Unknown'} | {'[V]' if tech.identity_provider else '[U]'} |")
        lines.append(f"| Cloud Provider | {tech.cloud_provider or 'Unknown'} | {'[V]' if tech.cloud_provider else '[U]'} |")
        lines.append("")

        # All Integrations (deduplicated by tool name)
        if tech.integrations:
            lines.append("### Detected Integrations")
            lines.append("")
            lines.append(f"| Tool | Category | Evidence | Source |")
            lines.append(f"|------|----------|----------|--------|")
            unique_integrations = deduplicate_by_field(tech.integrations, "tool_name")
            for integration in unique_integrations:
                ev_class, has_conflict = classify_integration(integration)
                badge = format_badge(ev_class, has_conflict)
                evidence_link = integration.evidence.url if integration.evidence else "N/A"
                lines.append(f"| {integration.tool_name} | {integration.category} | {badge} | {evidence_link} |")
            lines.append("")

        # Subdomains Analysis
        if tech.subdomains_found:
            lines.append("### Subdomain Analysis")
            lines.append("")

            # Categorize subdomains
            categories = {
                "Identity/Auth": [],
                "Regional": [],
                "API/Infrastructure": [],
                "Other": []
            }

            for subdomain in tech.subdomains_found:
                lower = subdomain.lower()
                if any(kw in lower for kw in ['sso', 'auth', 'login', 'identity', 'okta', 'saml']):
                    categories["Identity/Auth"].append(subdomain)
                elif any(kw in lower for kw in ['eu', 'uk', 'apac', 'asia', 'emea', 'us-', 'ca-']):
                    categories["Regional"].append(subdomain)
                elif any(kw in lower for kw in ['api', 'cdn', 'static', 'app', 'staging', 'dev']):
                    categories["API/Infrastructure"].append(subdomain)
                else:
                    categories["Other"].append(subdomain)

            for category, subs in categories.items():
                if subs:
                    lines.append(f"**{category}:** {len(subs)} subdomains")
                    for sub in subs[:5]:
                        lines.append(f"- {sub}")
                    if len(subs) > 5:
                        lines.append(f"- ... and {len(subs) - 5} more")
                    lines.append("")

    # Fluency Integration Opportunities
    lines.append("## Fluency Integration Opportunities")
    lines.append("")

    # Analyze based on detected stack
    opportunities = []
    considerations = []

    if research.tech_stack:
        tech = research.tech_stack

        # Identity provider integration
        if tech.identity_provider:
            idp = tech.identity_provider.lower()
            if "okta" in idp:
                opportunities.append("**Okta SSO Integration**: Customer uses Okta - leverage SCIM provisioning and SAML 2.0")
            elif "azure" in idp:
                opportunities.append("**Azure AD Integration**: Customer uses Azure AD - consider Microsoft Graph API integration")
            elif "onelogin" in idp:
                opportunities.append("**OneLogin Integration**: Standard SAML integration path")
            else:
                considerations.append(f"**Custom IdP ({tech.identity_provider})**: May require additional integration work")

        # Cloud provider
        if tech.cloud_provider:
            cloud = tech.cloud_provider.lower()
            if "aws" in cloud:
                opportunities.append("**AWS Deployment**: Customer is AWS-native - consider AWS Marketplace listing")
            elif "azure" in cloud:
                opportunities.append("**Azure Deployment**: Customer uses Azure - consider Azure Marketplace listing")
            elif "gcp" in cloud:
                opportunities.append("**GCP Deployment**: Customer uses GCP - consider Google Cloud Marketplace")

        # Look for process tools
        process_tools = [i for i in tech.integrations if i.category.lower() in ['process mining', 'automation', 'bpm', 'workflow']]
        if process_tools:
            tools_list = ", ".join(i.tool_name for i in process_tools)
            opportunities.append(f"**Existing Process Tools ({tools_list})**: Potential integration or replacement opportunity")

        # Collaboration tools
        collab_tools = [i for i in tech.integrations if i.category.lower() in ['collaboration', 'communication']]
        if collab_tools:
            tools_list = ", ".join(i.tool_name for i in collab_tools)
            opportunities.append(f"**Collaboration Integration ({tools_list})**: Workflow notifications and approvals")

    if opportunities:
        lines.append("### Opportunities")
        lines.append("")
        for opp in opportunities:
            lines.append(f"- {opp}")
        lines.append("")

    if considerations:
        lines.append("### Considerations")
        lines.append("")
        for cons in considerations:
            lines.append(f"- {cons}")
        lines.append("")

    # AI-Generated Sections (if available)
    if ai_refinements:
        # Integration Complexity
        lines.extend(_format_ai_integration_complexity(ai_refinements.get("integration_complexity", {})))

        # Tech Stack Compatibility
        lines.extend(_format_ai_tech_compatibility(ai_refinements.get("tech_stack_compatibility", {})))

        # Implementation Roadmap
        lines.extend(_format_ai_implementation_roadmap(ai_refinements.get("implementation_roadmap", {})))

        # Deployment Risks
        lines.extend(_format_ai_deployment_risks(ai_refinements.get("deployment_risks", [])))

        # Success Factors
        lines.extend(_format_ai_success_factors(ai_refinements.get("success_factors", [])))

    # Implementation Considerations
    lines.append("## Implementation Considerations")
    lines.append("")

    # Compliance requirements affecting implementation
    lines.append("### Compliance Impact")
    lines.append("")
    lines.append(f"**Compliance Complexity Score: {score.compliance_complexity}/10**")
    lines.append("")

    compliance_items = []
    if research.financials and research.financials.regulatory_mentions:
        for reg in research.financials.regulatory_mentions[:5]:
            compliance_items.append(f"- {reg} compliance required")

    if research.security and research.security.privacy_requirements:
        for req in research.security.privacy_requirements[:5]:
            compliance_items.append(f"- {req}")

    if compliance_items:
        for item in compliance_items:
            lines.append(item)
    else:
        lines.append("- No specific compliance requirements identified")
    lines.append("")

    # Geographic considerations
    lines.append("### Geographic Considerations")
    lines.append("")

    geo_items = []
    if research.security and research.security.data_residency:
        geo_items.append(f"Data residency regions: {', '.join(research.security.data_residency)}")
    if research.financials and research.financials.geographic_operations:
        for geo in research.financials.geographic_operations[:3]:
            geo_items.append(geo)

    if geo_items:
        for item in geo_items:
            lines.append(f"- {item}")
    else:
        lines.append("- No specific geographic requirements identified")
    lines.append("")

    # Deal Complexity
    lines.append("### Deal Complexity Factors")
    lines.append("")
    lines.append(f"**Deal Complexity Score: {score.deal_complexity}/10**")
    lines.append("")

    complexity_factors = []
    if profile.company_type.value == "PUBLIC":
        complexity_factors.append("Public company - expect longer procurement process and security reviews")
    if profile.employee_count:
        try:
            emp = profile.employee_count.replace(",", "").replace("+", "")
            if "-" in emp:
                emp = emp.split("-")[1]
            if int(emp) > 5000:
                complexity_factors.append("Large enterprise - expect multiple stakeholder approvals")
        except (ValueError, IndexError):
            pass
    if profile.industry.lower() in ["healthcare", "finance", "insurance", "banking", "government"]:
        complexity_factors.append(f"Regulated industry ({profile.industry}) - additional compliance requirements likely")

    if complexity_factors:
        for factor in complexity_factors:
            lines.append(f"- {factor}")
    else:
        lines.append("- Standard complexity expected")
    lines.append("")

    # Evidence Legend
    lines.extend(get_evidence_legend())

    # Footer
    lines.append("*Generated by Fluency AI Research Agent*")

    return "\n".join(lines)
