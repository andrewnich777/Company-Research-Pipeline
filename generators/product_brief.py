"""
Product Brief Generator - Creates stakeholder-specific output for product teams.
"""

from models import CompanyProfile, SynthesisOutput, ResearchResults


def generate_product_brief(
    profile: CompanyProfile,
    synthesis: SynthesisOutput,
    research: ResearchResults
) -> str:
    """
    Generate a product-focused brief for implementation planning.

    Returns markdown-formatted string.
    """
    lines = []

    # Header
    lines.append(f"# Product Brief: {profile.name}")
    lines.append("")
    lines.append(f"**Fluency AI Implementation Planning**")
    lines.append("")

    # Company Context
    lines.append("## Company Context")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| **Company** | {profile.name} |")
    lines.append(f"| **Domain** | {profile.domain} |")
    lines.append(f"| **Industry** | {profile.industry} |")
    lines.append(f"| **Type** | {profile.company_type.value} |")
    lines.append(f"| **Employees** | {profile.employee_count or 'Unknown'} |")
    lines.append("")
    lines.append(f"> {profile.description}")
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
        lines.append(f"| Component | Detected | Confidence |")
        lines.append(f"|-----------|----------|------------|")
        lines.append(f"| Identity Provider | {tech.identity_provider or 'Unknown'} | {'HIGH' if tech.identity_provider else 'N/A'} |")
        lines.append(f"| Cloud Provider | {tech.cloud_provider or 'Unknown'} | {'HIGH' if tech.cloud_provider else 'N/A'} |")
        lines.append("")

        # All Integrations
        if tech.integrations:
            lines.append("### Detected Integrations")
            lines.append("")
            lines.append(f"| Tool | Category | Confidence | Evidence |")
            lines.append(f"|------|----------|------------|----------|")
            for integration in tech.integrations:
                evidence_link = f"[Source]({integration.evidence.url})" if integration.evidence else "Inferred"
                lines.append(f"| {integration.tool_name} | {integration.category} | {integration.confidence.value} | {evidence_link} |")
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

    # AI/Automation Readiness
    lines.append("## AI/Automation Readiness")
    lines.append("")
    lines.append(f"**Strategic Alignment Score: {score.strategic_alignment}/10**")
    lines.append("")

    if research.strategic:
        strat = research.strategic

        if strat.ai_initiatives:
            lines.append("### Existing AI Initiatives")
            lines.append("")
            for initiative in strat.ai_initiatives:
                lines.append(f"- {initiative.claim}")
                if initiative.evidence:
                    lines.append(f"  - Source: {initiative.evidence[0].url}")
            lines.append("")

        if strat.partnerships:
            tech_partners = [p for p in strat.partnerships
                           if any(kw in p.claim.lower() for kw in
                                  ['technology', 'software', 'cloud', 'ai', 'digital', 'microsoft', 'google', 'aws', 'salesforce'])]
            if tech_partners:
                lines.append("### Technology Partnerships")
                lines.append("")
                for partner in tech_partners:
                    lines.append(f"- {partner.claim}")
                lines.append("")

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

    # Technical Evidence
    lines.append("## Technical Evidence Summary")
    lines.append("")
    lines.append(f"| Category | Claims | High Confidence |")
    lines.append(f"|----------|--------|-----------------|")

    tech_claims = len(synthesis.evidence_graph.technology_claims)
    tech_high = sum(1 for c in synthesis.evidence_graph.technology_claims if c.confidence.value == "HIGH")
    lines.append(f"| Technology | {tech_claims} | {tech_high} |")

    sec_claims = len(synthesis.evidence_graph.security_claims)
    sec_high = sum(1 for c in synthesis.evidence_graph.security_claims if c.confidence.value == "HIGH")
    lines.append(f"| Security | {sec_claims} | {sec_high} |")

    strat_claims = len(synthesis.evidence_graph.strategic_claims)
    strat_high = sum(1 for c in synthesis.evidence_graph.strategic_claims if c.confidence.value == "HIGH")
    lines.append(f"| Strategic | {strat_claims} | {strat_high} |")
    lines.append("")

    # Detailed Technology Claims
    if synthesis.evidence_graph.technology_claims:
        lines.append("### Technology Claims Detail")
        lines.append("")
        for claim in synthesis.evidence_graph.technology_claims:
            lines.append(f"- **{claim.claim}** [{claim.confidence.value}]")
            if claim.evidence:
                lines.append(f"  - Source: {claim.evidence[0].url}")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("*Generated by Fluency AI Research Agent*")

    return "\n".join(lines)
