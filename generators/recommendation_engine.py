"""
Score-based recommendation engine.

Generates deployment recommendations based on score relationships,
not just individual values. Each recommendation explicitly references
the relevant scores and explains WHY the combination produces the advice.
"""

from models import DeploymentScore


def generate_score_based_recommendation(scores: DeploymentScore) -> str:
    """
    Generate recommendation based on score relationships, not just values.

    Detects score tensions and combinations to produce specific,
    actionable recommendations that reference the actual scores.

    Args:
        scores: DeploymentScore with 8 dimensions + overall

    Returns:
        Recommendation string with score references
    """
    recommendations = []

    # Pattern 1: High strategic alignment + Low compliance complexity
    # Tension: They WANT to buy but compliance will slow them down
    if scores.strategic_alignment > 7 and scores.compliance_complexity < 4:
        recommendations.append(
            f"High intent ({scores.strategic_alignment}/10), slow procurement ({scores.compliance_complexity}/10). "
            "Strategy: Secure executive sponsor early to push through compliance bottleneck."
        )

    # Pattern 2: High integration fit + Low deal complexity = Accelerated timeline
    # Opportunity: Easy technical fit AND easy buying process
    if scores.integration_fit > 7 and scores.deal_complexity > 6:
        recommendations.append(
            f"Strong tech fit ({scores.integration_fit}/10) with streamlined buying ({scores.deal_complexity}/10). "
            "Recommend accelerated 30-day POC timeline."
        )

    # Pattern 3: Champion identified but low procurement clarity
    # Tension: Have internal advocate but unclear path to purchase
    if scores.champion_identified > 6 and scores.procurement_clarity < 4:
        recommendations.append(
            f"Champion found ({scores.champion_identified}/10) but procurement opaque ({scores.procurement_clarity}/10). "
            "Arm champion with ROI materials to navigate internal approvals."
        )

    # Pattern 4: High security maturity + Low regulatory risk score
    # Tension: They're security-conscious but have regulatory exposure
    if scores.security_maturity > 7 and scores.regulatory_risk < 4:
        recommendations.append(
            f"Security-mature ({scores.security_maturity}/10) but regulatory exposure ({scores.regulatory_risk}/10). "
            "Lead with compliance certifications and BAA/DPA readiness."
        )

    # Pattern 5: Low strategic alignment = Education needed first
    if scores.strategic_alignment < 4:
        recommendations.append(
            f"Low AI/automation awareness ({scores.strategic_alignment}/10). "
            "Recommend discovery workshop to build business case before demo."
        )

    # Pattern 6: Integration mismatch = Custom work needed
    if scores.integration_fit < 4:
        recommendations.append(
            f"Integration gaps detected ({scores.integration_fit}/10). "
            "Scope custom connector work in proposal; consider professional services."
        )

    # Pattern 7: High champion + High strategic = Fast track
    if scores.champion_identified > 7 and scores.strategic_alignment > 7:
        recommendations.append(
            f"Strong champion ({scores.champion_identified}/10) + high AI intent ({scores.strategic_alignment}/10). "
            "Fast-track: Go direct to technical POC, skip extended discovery."
        )

    # Pattern 8: Low procurement clarity + Low deal complexity
    # Startup/SMB pattern - may not have formal process
    if scores.procurement_clarity < 4 and scores.deal_complexity > 7:
        recommendations.append(
            f"Informal buying process ({scores.procurement_clarity}/10) but simple org ({scores.deal_complexity}/10). "
            "Direct founder/exec engagement; skip procurement formalities."
        )

    # Pattern 9: High security + High compliance = Enterprise-ready
    if scores.security_maturity > 7 and scores.compliance_complexity > 7:
        recommendations.append(
            f"Enterprise-ready ({scores.security_maturity}/10 security, {scores.compliance_complexity}/10 compliance). "
            "Lead with technical architecture review; security won't be a blocker."
        )

    # Pattern 10: Low regulatory risk + High integration = Quick win
    if scores.regulatory_risk > 7 and scores.integration_fit > 7:
        recommendations.append(
            f"Clean regulatory ({scores.regulatory_risk}/10) + strong fit ({scores.integration_fit}/10). "
            "Optimize for speed: 2-week POC to paid pilot."
        )

    # Default recommendations based on overall score if no patterns match
    if not recommendations:
        if scores.overall >= 7:
            recommendations.append(
                f"Strong overall fit ({scores.overall:.1f}/10). "
                "Standard enterprise sales motion recommended."
            )
        elif scores.overall >= 5:
            recommendations.append(
                f"Moderate fit ({scores.overall:.1f}/10). "
                "Focus discovery on addressing identified gaps before demo."
            )
        else:
            recommendations.append(
                f"Challenging fit ({scores.overall:.1f}/10). "
                "Recommend qualification call before investing resources."
            )

    # Join multiple recommendations with separators
    return " | ".join(recommendations)


def get_score_summary(scores: DeploymentScore) -> str:
    """
    Generate a brief score summary showing the key dimensions.

    Returns a compact string showing scores that deviate from average.
    """
    summary_parts = []

    # Highlight scores that are notably high or low
    dimensions = [
        ("Security", scores.security_maturity),
        ("Integration", scores.integration_fit),
        ("Compliance", scores.compliance_complexity),
        ("Strategic", scores.strategic_alignment),
        ("Deal", scores.deal_complexity),
        ("Champion", scores.champion_identified),
        ("Procurement", scores.procurement_clarity),
        ("Regulatory", scores.regulatory_risk),
    ]

    high_scores = [(name, score) for name, score in dimensions if score >= 7]
    low_scores = [(name, score) for name, score in dimensions if score <= 3]

    if high_scores:
        high_str = ", ".join(f"{name}:{score}" for name, score in high_scores)
        summary_parts.append(f"Strengths: {high_str}")

    if low_scores:
        low_str = ", ".join(f"{name}:{score}" for name, score in low_scores)
        summary_parts.append(f"Gaps: {low_str}")

    if not summary_parts:
        summary_parts.append(f"Balanced profile (overall: {scores.overall:.1f}/10)")

    return " | ".join(summary_parts)
