"""
Security Brief Generator - Creates stakeholder-specific output for security teams.
"""

from typing import Optional
from models import CompanyProfile, SynthesisOutput, ResearchResults
from .dedup import deduplicate_claims
from .evidence_classifier import (
    classify_claim, classify_certification, format_badge, get_evidence_legend
)


def _format_ai_risk_assessment(assessment: dict) -> list[str]:
    """Format AI-generated risk assessment."""
    lines = []
    if not assessment:
        return lines

    overall = assessment.get("overall", "UNKNOWN")
    factors = assessment.get("factors", [])
    mitigating = assessment.get("mitigating", [])

    lines.append("## AI Risk Assessment")
    lines.append("")
    lines.append(f"**Overall Risk Level: {overall}**")
    lines.append("")

    if factors:
        lines.append("### Risk Factors")
        lines.append("")
        for factor in factors[:6]:
            lines.append(f"- {factor}")
        lines.append("")

    if mitigating:
        lines.append("### Mitigating Factors")
        lines.append("")
        for factor in mitigating[:4]:
            lines.append(f"- {factor}")
        lines.append("")

    return lines


def _format_ai_compliance_gaps(gaps: list) -> list[str]:
    """Format AI-generated compliance gaps."""
    lines = []
    if not gaps:
        return lines

    lines.append("## Compliance Gaps Analysis")
    lines.append("")
    lines.append("| Gap | Severity | Recommended Action | Fluency Alignment |")
    lines.append("|-----|----------|-------------------|-------------------|")

    for gap in gaps[:6]:
        gap_desc = gap.get("gap", "").replace("|", "\\|")
        severity = gap.get("severity", "UNKNOWN")
        action = gap.get("action", "").replace("|", "\\|")
        alignment = gap.get("fluency_alignment", "").replace("|", "\\|")
        lines.append(f"| {gap_desc} | {severity} | {action} | {alignment} |")

    lines.append("")
    return lines


def _format_ai_certification_verification(verification: dict) -> list[str]:
    """Format AI-generated certification verification."""
    lines = []
    if not verification:
        return lines

    claimed = verification.get("claimed", [])
    verified = verification.get("verified", [])
    unverified = verification.get("unverified", [])
    actions = verification.get("actions", [])

    if not (claimed or verified or unverified):
        return lines

    lines.append("## Certification Verification Status")
    lines.append("")

    if verified:
        lines.append("**Verified Certifications:**")
        for cert in verified:
            lines.append(f"- :white_check_mark: {cert}")
        lines.append("")

    if unverified:
        lines.append("**Unverified (Needs Confirmation):**")
        for cert in unverified:
            lines.append(f"- :question: {cert}")
        lines.append("")

    if claimed and not verified and not unverified:
        lines.append("**Claimed Certifications:**")
        for cert in claimed:
            lines.append(f"- {cert}")
        lines.append("")

    if actions:
        lines.append("**Verification Actions:**")
        for action in actions[:4]:
            lines.append(f"- [ ] {action}")
        lines.append("")

    return lines


def _format_ai_remediation_priorities(priorities: list) -> list[str]:
    """Format AI-generated remediation priorities."""
    lines = []
    if not priorities:
        return lines

    lines.append("## Remediation Priorities")
    lines.append("")

    for item in priorities[:5]:
        priority = item.get("priority", "?")
        issue = item.get("issue", "Unknown issue")
        recommendation = item.get("recommendation", "")

        lines.append(f"**Priority {priority}:** {issue}")
        if recommendation:
            lines.append(f"*Recommendation:* {recommendation}")
        lines.append("")

    return lines


def _format_ai_due_diligence(checklist: list) -> list[str]:
    """Format AI-generated due diligence checklist."""
    lines = []
    if not checklist:
        return lines

    lines.append("## Due Diligence Checklist")
    lines.append("")

    for item in checklist[:8]:
        lines.append(f"- [ ] {item}")

    lines.append("")
    return lines


def generate_security_brief(
    profile: CompanyProfile,
    synthesis: SynthesisOutput,
    research: ResearchResults,
    ai_refinements: Optional[dict] = None
) -> str:
    """
    Generate a security-focused brief for deployment preparation.

    Args:
        profile: Company profile data
        synthesis: Synthesis output with scores and recommendations
        research: Research results from all agents
        ai_refinements: Optional AI-generated refinements from BriefRefinerAgent

    Returns markdown-formatted string.
    """
    lines = []

    # Header
    lines.append(f"# Security Brief: {profile.name}")
    lines.append("")
    lines.append(f"**Fluency AI Deployment Security Assessment**")
    lines.append("")

    # Company Overview (minimal - see Executive Brief for full intel)
    lines.append("## Company Overview")
    lines.append("")
    lines.append(f"| Field | Value |")
    lines.append(f"|-------|-------|")
    lines.append(f"| Company | {profile.name} |")
    lines.append(f"| Domain | {profile.domain} |")
    lines.append(f"| Industry | {profile.industry} |")
    lines.append(f"| Type | {profile.company_type.value} |")
    lines.append("")

    # Security Maturity Assessment
    score = synthesis.deployment_score
    lines.append("## Security Maturity Assessment")
    lines.append("")
    lines.append(f"**Overall Security Score: {score.security_maturity}/10**")
    lines.append("")

    if research.security:
        sec = research.security
        lines.append(f"**Security Maturity Level:** {sec.security_maturity}")
        lines.append("")

        # Trust Center
        lines.append("### Trust Center")
        lines.append("")
        if sec.trust_center_url:
            lines.append(f"Trust Center URL: [{sec.trust_center_url}]({sec.trust_center_url})")
        else:
            lines.append("No dedicated trust center found.")
        lines.append("")

        # Certifications
        lines.append("### Certifications")
        lines.append("")
        if sec.certifications:
            lines.append("| Certification | Status | Evidence | Source |")
            lines.append("|---------------|--------|----------|--------|")
            for cert in sec.certifications:
                ev_class, has_conflict = classify_certification(cert)
                badge = format_badge(ev_class, has_conflict)
                source = cert.evidence.url if cert.evidence else "Not verified"
                lines.append(f"| {cert.name} | {cert.status} | {badge} | {source} |")
        else:
            lines.append("No certifications found. [U]")
        lines.append("")

        # Data Residency
        lines.append("### Data Residency")
        lines.append("")
        if sec.data_residency:
            lines.append(f"Identified data residency regions: {', '.join(sec.data_residency)}")
        else:
            lines.append("Data residency information not found.")
        lines.append("")

        # Privacy Requirements
        lines.append("### Privacy Requirements")
        lines.append("")
        if sec.privacy_requirements:
            for req in sec.privacy_requirements:
                lines.append(f"- {req}")
        else:
            lines.append("No specific privacy requirements identified.")
        lines.append("")

        # Security Incidents (deduplicated)
        lines.append("### Security Incident History")
        lines.append("")
        if sec.security_incidents:
            unique_incidents = deduplicate_claims(sec.security_incidents)
            for incident in unique_incidents:
                ev_class, has_conflict = classify_claim(incident)
                badge = format_badge(ev_class, has_conflict)
                lines.append(f"- {incident.claim} {badge}")
                if incident.evidence:
                    lines.append(f"  - Source: {incident.evidence[0].url}")
        else:
            lines.append("No security incidents found in public records. [U]")
        lines.append("")

    # AI-Generated Sections (if available)
    if ai_refinements:
        # Risk Assessment
        lines.extend(_format_ai_risk_assessment(ai_refinements.get("risk_assessment", {})))

        # Compliance Gaps
        lines.extend(_format_ai_compliance_gaps(ai_refinements.get("compliance_gaps", [])))

        # Certification Verification
        lines.extend(_format_ai_certification_verification(ai_refinements.get("certification_verification", {})))

        # Remediation Priorities
        lines.extend(_format_ai_remediation_priorities(ai_refinements.get("remediation_priorities", [])))

        # Due Diligence Checklist
        lines.extend(_format_ai_due_diligence(ai_refinements.get("due_diligence_checklist", [])))

    # Compliance Requirements
    lines.append("## Compliance Requirements")
    lines.append("")
    lines.append(f"**Compliance Complexity Score: {score.compliance_complexity}/10**")
    lines.append("")

    # From financial findings (SEC filings)
    if research.financials and research.financials.regulatory_mentions:
        lines.append("### Regulatory Framework (from SEC Filings)")
        lines.append("")
        for reg in research.financials.regulatory_mentions:
            lines.append(f"- {reg}")
        lines.append("")

        if research.financials.risk_factors:
            lines.append("### Compliance-Related Risk Factors")
            lines.append("")
            for risk in research.financials.risk_factors[:10]:
                lines.append(f"- {risk}")
            lines.append("")

    # Technology Security Considerations
    lines.append("## Technology Security Considerations")
    lines.append("")
    lines.append(f"**Integration Fit Score: {score.integration_fit}/10**")
    lines.append("")

    if research.tech_stack:
        tech = research.tech_stack

        # Identity Provider
        lines.append("### Identity & Access Management")
        lines.append("")
        if tech.identity_provider:
            lines.append(f"**Primary Identity Provider:** {tech.identity_provider}")
            lines.append("")
            lines.append("SSO integration considerations:")
            if tech.identity_provider.lower() in ["okta", "azure ad", "onelogin"]:
                lines.append("- Standard SAML/OIDC integration should be straightforward")
            else:
                lines.append(f"- Custom integration may be required for {tech.identity_provider}")
        else:
            lines.append("Identity provider not identified. Discovery call should clarify SSO requirements.")
        lines.append("")

        # Cloud Provider
        lines.append("### Cloud Infrastructure")
        lines.append("")
        if tech.cloud_provider:
            lines.append(f"**Primary Cloud Provider:** {tech.cloud_provider}")
        else:
            lines.append("Cloud provider not identified.")
        lines.append("")

        # Subdomains (security-relevant)
        if tech.subdomains_found:
            security_subdomains = [s for s in tech.subdomains_found
                                   if any(keyword in s.lower() for keyword in
                                          ['sso', 'auth', 'login', 'identity', 'okta', 'vpn', 'secure'])]
            if security_subdomains:
                lines.append("### Security-Related Subdomains")
                lines.append("")
                for subdomain in security_subdomains[:10]:
                    lines.append(f"- {subdomain}")
                lines.append("")

    # Deployment Blockers
    lines.append("## Potential Security Blockers")
    lines.append("")
    security_blockers = [b for b in synthesis.blockers
                         if any(keyword in b.lower() for keyword in
                                ['security', 'compliance', 'hipaa', 'gdpr', 'soc', 'iso', 'fedramp',
                                 'baa', 'data', 'privacy', 'audit', 'certification'])]
    if security_blockers:
        for blocker in security_blockers:
            lines.append(f"- {blocker}")
    else:
        lines.append("- No significant security blockers identified")
    lines.append("")

    # Deployment Checklist
    lines.append("## Pre-Deployment Security Checklist")
    lines.append("")
    lines.append("| Item | Status | Notes |")
    lines.append("|------|--------|-------|")

    # Determine checklist items based on findings
    has_soc2 = any(c.name.lower().startswith("soc 2") for c in (research.security.certifications if research.security else []))
    has_iso = any("iso 27001" in c.name.lower() for c in (research.security.certifications if research.security else []))
    has_hipaa = any("hipaa" in c.name.lower() for c in (research.security.certifications if research.security else []))
    has_trust_center = research.security and research.security.trust_center_url

    lines.append(f"| SOC 2 Type II verification | {'Verified' if has_soc2 else 'Pending'} | {'Found in trust center' if has_soc2 else 'Verify during procurement'} |")
    lines.append(f"| ISO 27001 verification | {'Verified' if has_iso else 'Pending'} | {'Found in trust center' if has_iso else 'May not be required'} |")
    lines.append(f"| HIPAA BAA required | {'Yes - verify' if has_hipaa else 'TBD'} | Based on industry: {profile.industry} |")
    lines.append(f"| SSO/SAML configuration | Pending | IdP: {research.tech_stack.identity_provider if research.tech_stack and research.tech_stack.identity_provider else 'TBD'} |")
    lines.append(f"| Data residency requirements | Pending | Regions: {', '.join(research.security.data_residency) if research.security and research.security.data_residency else 'TBD'} |")
    lines.append(f"| Security questionnaire | Pending | {f'Trust center available: {research.security.trust_center_url}' if has_trust_center else 'No trust center - may require manual review'} |")
    lines.append("")

    # Evidence Legend
    lines.extend(get_evidence_legend())

    # Footer
    lines.append("*Generated by Fluency AI Research Agent*")

    return "\n".join(lines)
