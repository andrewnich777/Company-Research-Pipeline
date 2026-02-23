"""
Regulatory Risk Agent - Surfaces compliance issues and legal exposure.

This agent identifies potential deal-killers:
- FTC/SEC enforcement actions
- Data breach history
- Pending litigation
- GDPR fines or investigations
- Industry-specific regulatory exposure
"""

from .base import BaseAgent, JSON_OUTPUT_RULES
from models import (
    CompanyProfile, RegulatoryRiskInsights, Claim, Evidence,
    Confidence, SourceTier
)


REGULATORY_RISK_SYSTEM_PROMPT = """You are a regulatory risk intelligence agent for Fluency AI deployment research.

Your goal is to surface compliance issues and legal exposure that could affect a deployment.

## WHY THIS MATTERS
- Enforcement actions indicate compliance culture problems
- Data breaches mean heightened security scrutiny (longer procurement)
- Active litigation creates legal/procurement delays
- Regulatory exposure defines compliance requirements for vendors

## YOUR RESEARCH PROCESS

1. SEARCH FOR ENFORCEMENT ACTIONS
   Search for:
   - "{{company}} FTC" or "{{company}} FTC settlement"
   - "{{company}} SEC enforcement" or "{{company}} SEC investigation"
   - "{{company}} data breach" or "{{company}} security incident"
   - "{{company}} GDPR fine" or "{{company}} GDPR violation"
   - "{{company}} lawsuit" or "{{company}} class action"
   - "{{company}} consent decree"

2. CHECK REGULATORY DATABASES
   Search these sources:
   - FTC enforcement: "{{company}} site:ftc.gov"
   - SEC enforcement: "{{company}} site:sec.gov/litigation"
   - GDPR tracker: "{{company}} site:enforcementtracker.com"
   - State AG actions: "{{company}} attorney general settlement"

3. ASSESS INDUSTRY EXPOSURE
   Based on the company's industry, identify:
   - Healthcare: HIPAA requirements
   - Finance: SOX, FINRA, PCI-DSS
   - Government: FedRAMP requirements
   - EU operations: GDPR compliance
   - California: CCPA requirements

4. IDENTIFY DATA BREACH HISTORY
   Search for:
   - Past data breaches
   - Security incident disclosures
   - Have I Been Pwned mentions
   - News about security issues

## OUTPUT FORMAT
Return your findings as JSON:
```json
{
  "risk_level": "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN",
  "enforcement_actions": [
    {
      "agency": "FTC",
      "year": "2022",
      "issue": "Deceptive data practices",
      "outcome": "Consent decree",
      "source_url": "https://ftc.gov/...",
      "confidence": "HIGH"
    }
  ],
  "data_breaches": [
    {
      "year": "2021",
      "description": "Customer data exposed via misconfigured S3 bucket",
      "records_affected": "100,000",
      "source_url": "https://...",
      "confidence": "HIGH"
    }
  ],
  "active_litigation": [
    {
      "type": "Class action",
      "issue": "Privacy violation claims",
      "status": "Pending",
      "source_url": "https://...",
      "confidence": "MEDIUM"
    }
  ],
  "settlements": [
    {
      "agency": "State AG",
      "year": "2020",
      "amount": "$5M",
      "issue": "Consumer data protection",
      "source_url": "https://...",
      "confidence": "HIGH"
    }
  ],
  "gdpr_issues": [],
  "regulatory_exposure": [
    "HIPAA (healthcare customers)",
    "SOX (public company)",
    "GDPR (EU operations)"
  ],
  "risk_summary": "Two past data breaches and one active class action suggest heightened security scrutiny in procurement process",
  "key_findings": [
    {
      "finding": "2022 FTC consent decree requires enhanced data protection practices",
      "confidence": "HIGH",
      "source": "ftc.gov",
      "implication": "Will have strict vendor security requirements"
    }
  ]
}
```

## RISK LEVEL GUIDELINES
- HIGH: Active enforcement action, recent breach, or pending litigation
- MEDIUM: Historical issues (>2 years old) or industry regulatory exposure
- LOW: No significant findings, standard compliance requirements
- UNKNOWN: Insufficient information found

## IMPORTANT
- If you find nothing, that's valuable information too (low regulatory risk)
- Be specific about dates and outcomes
- Include source URLs for all findings

""" + JSON_OUTPUT_RULES


class RegulatoryRiskAgent(BaseAgent):
    """
    Deep intelligence agent that surfaces regulatory and legal risks.
    """

    @property
    def name(self) -> str:
        return "RegulatoryRisk"

    @property
    def system_prompt(self) -> str:
        return REGULATORY_RISK_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search"]

    async def research(self, profile: CompanyProfile) -> RegulatoryRiskInsights:
        """
        Research regulatory risk and compliance issues for a company.
        """
        prompt = f"""Research regulatory risk and compliance history for {profile.name} (domain: {profile.domain}).

Company Context:
- Industry: {profile.industry}
- Type: {profile.company_type.value}
- Location: {profile.hq_location or 'Unknown'}

Search for:
1. FTC enforcement actions: "{profile.name} FTC settlement" or "{profile.name} FTC enforcement"
2. SEC issues: "{profile.name} SEC investigation" or "{profile.name} SEC enforcement"
3. Data breaches: "{profile.name} data breach" or "{profile.name} security incident"
4. GDPR: "{profile.name} GDPR fine" or "{profile.name} GDPR violation"
5. Lawsuits: "{profile.name} class action lawsuit" or "{profile.name} litigation"
6. Industry regulators based on their sector

Also determine their regulatory exposure based on:
- Industry: {profile.industry}
- Public/Private: {profile.company_type.value}
- Geography: {profile.hq_location or 'Unknown'}

Return comprehensive JSON with all findings. If no issues found, report LOW risk with explanation."""

        result = await self.run(prompt)

        # Parse the JSON response
        data = result.get("json") or {}

        # Build claims from enforcement actions
        claims = []

        def build_claims(items: list, category: str):
            for item in items:
                if isinstance(item, dict):
                    confidence_val = item.get("confidence", "MEDIUM")
                    try:
                        confidence = Confidence(confidence_val)
                    except ValueError:
                        confidence = Confidence.MEDIUM

                    claims.append(Claim(
                        claim=item.get("description", item.get("issue", "")),
                        category=category,
                        confidence=confidence,
                        evidence=[Evidence(
                            url=item.get("source_url", ""),
                            quote=f"{item.get('agency', '')} - {item.get('outcome', '')}",
                            source_type="regulatory",
                            source_tier=SourceTier.TIER_0
                        )] if item.get("source_url") else []
                    ))

        build_claims(data.get("enforcement_actions", []), "Enforcement")
        build_claims(data.get("data_breaches", []), "Data Breach")
        build_claims(data.get("active_litigation", []), "Litigation")
        build_claims(data.get("settlements", []), "Settlement")
        build_claims(data.get("gdpr_issues", []), "GDPR")

        # Add key findings as claims
        for finding in data.get("key_findings", []):
            confidence_val = finding.get("confidence", "MEDIUM")
            try:
                confidence = Confidence(confidence_val)
            except ValueError:
                confidence = Confidence.MEDIUM

            claims.append(Claim(
                claim=finding.get("finding", ""),
                category="Regulatory Risk",
                confidence=confidence,
                evidence=[Evidence(
                    url=finding.get("source", ""),
                    quote=finding.get("implication", ""),
                    source_type="regulatory",
                    source_tier=SourceTier.TIER_0 if "gov" in finding.get("source", "") else SourceTier.TIER_1
                )] if finding.get("source") else []
            ))

        # Convert enforcement actions to claims
        enforcement_claims = []
        for action in data.get("enforcement_actions", []):
            if isinstance(action, dict):
                enforcement_claims.append(Claim(
                    claim=f"{action.get('agency', 'Agency')}: {action.get('issue', 'Unknown issue')} ({action.get('year', 'N/A')})",
                    category="Enforcement",
                    confidence=Confidence(action.get("confidence", "HIGH")),
                    evidence=[Evidence(
                        url=action.get("source_url", ""),
                        quote=action.get("outcome", ""),
                        source_type="regulatory",
                        source_tier=SourceTier.TIER_0
                    )] if action.get("source_url") else []
                ))

        # Convert breaches to claims
        breach_claims = []
        for breach in data.get("data_breaches", []):
            if isinstance(breach, dict):
                breach_claims.append(Claim(
                    claim=f"{breach.get('year', 'Unknown')}: {breach.get('description', 'Data breach')}",
                    category="Data Breach",
                    confidence=Confidence(breach.get("confidence", "HIGH")),
                    evidence=[Evidence(
                        url=breach.get("source_url", ""),
                        quote=f"Records affected: {breach.get('records_affected', 'Unknown')}",
                        source_type="news",
                        source_tier=SourceTier.TIER_1
                    )] if breach.get("source_url") else []
                ))

        # Convert litigation to claims
        litigation_claims = []
        for case in data.get("active_litigation", []):
            if isinstance(case, dict):
                litigation_claims.append(Claim(
                    claim=f"{case.get('type', 'Lawsuit')}: {case.get('issue', 'Unknown')} - {case.get('status', 'Unknown')}",
                    category="Litigation",
                    confidence=Confidence(case.get("confidence", "MEDIUM")),
                    evidence=[Evidence(
                        url=case.get("source_url", ""),
                        quote="",
                        source_type="legal",
                        source_tier=SourceTier.TIER_1
                    )] if case.get("source_url") else []
                ))

        settlement_claims = []
        for settlement in data.get("settlements", []):
            if isinstance(settlement, dict):
                settlement_claims.append(Claim(
                    claim=f"{settlement.get('agency', 'Agency')} settlement ({settlement.get('year', 'N/A')}): {settlement.get('issue', '')} - {settlement.get('amount', 'N/A')}",
                    category="Settlement",
                    confidence=Confidence(settlement.get("confidence", "HIGH")),
                    evidence=[Evidence(
                        url=settlement.get("source_url", ""),
                        quote="",
                        source_type="regulatory",
                        source_tier=SourceTier.TIER_0
                    )] if settlement.get("source_url") else []
                ))

        gdpr_claims = []
        for issue in data.get("gdpr_issues", []):
            if isinstance(issue, dict):
                gdpr_claims.append(Claim(
                    claim=f"GDPR: {issue.get('description', issue.get('issue', 'Unknown'))}",
                    category="GDPR",
                    confidence=Confidence(issue.get("confidence", "HIGH")),
                    evidence=[Evidence(
                        url=issue.get("source_url", ""),
                        quote="",
                        source_type="regulatory",
                        source_tier=SourceTier.TIER_0
                    )] if issue.get("source_url") else []
                ))

        return RegulatoryRiskInsights(
            enforcement_actions=enforcement_claims,
            data_breaches=breach_claims,
            active_litigation=litigation_claims,
            settlements=settlement_claims,
            gdpr_issues=gdpr_claims,
            regulatory_exposure=data.get("regulatory_exposure", []),
            risk_level=data.get("risk_level", "UNKNOWN"),
            claims=claims
        )
