"""
Implementation Risk Agent - Identifies signals that predict implementation challenges.

Analyzes past implementation failures, tech debt, change management culture,
and industry-specific risks to set realistic deployment expectations.
"""

from .base import BaseAgent, JSON_OUTPUT_RULES
from models import (
    CompanyProfile, ImplementationRiskInsights, Claim, Evidence,
    Confidence, SourceTier
)


IMPLEMENTATION_RISK_SYSTEM_PROMPT = """You are an implementation risk assessment agent for Fluency AI deployment research.

Your goal is to identify signals that predict implementation challenges.

## WHY THIS MATTERS
- Past implementation failures predict future ones
- Tech debt signals integration complexity
- Change management culture affects adoption
- Industry-specific risks need mitigation planning

## SIGNALS TO LOOK FOR

### Past Implementation Failures
- Customer reviews mentioning "implementation", "onboarding", "migration"
- News about failed IT projects or delays
- Glassdoor reviews about "new tools" or "system changes"
- High turnover in IT/Engineering leadership

### Tech Debt Signals
- Job postings mentioning "legacy", "migration", "modernization"
- Multiple competing tools in same category
- "Technical debt reduction" as stated priority
- "Digital transformation" initiatives (often = big mess)

### Change Management Culture
- LinkedIn posts about organizational change
- News about restructuring or layoffs
- Rapid growth (>50% headcount) = chaotic adoption
- High IT/Engineering turnover
- "Change management" roles being hired

### Integration Complexity Indicators
- Many siloed systems
- Multiple ERP instances
- Complex data architecture
- Lots of custom integrations mentioned

### Industry-Specific Risks
- Healthcare: HIPAA validation requirements, clinical workflow sensitivity
- Finance: Audit trail requirements, SOX compliance
- Manufacturing: Downtime sensitivity, shift schedules
- Government: Procurement delays, security clearances

## RECOMMENDED APPROACH MAPPING
- Standard: Simple integration, mature change culture
- Phased: Complex integration, multiple stakeholders
- Pilot-first: Risk-averse culture, past failures, regulated industry

## YOUR RESEARCH PROCESS

1. Search customer reviews on G2/Capterra for "implementation" mentions
2. Search Glassdoor for "system" or "tools" or "IT" complaints
3. Search news for "{{company}} IT project" or "{{company}} implementation"
4. Search job postings for "change management" or "transformation"
5. Look for leadership turnover signals
6. Assess industry-specific risks

## OUTPUT FORMAT
```json
{
  "risk_level": "HIGH" | "MEDIUM" | "LOW",
  "past_implementation_issues": [
    {
      "issue": "2022 ERP migration delayed 6 months",
      "source": "https://...",
      "confidence": "MEDIUM"
    }
  ],
  "tech_debt_signals": [
    "Multiple job posts mention 'legacy system modernization'",
    "3 different project management tools in use"
  ],
  "change_management_concerns": [
    "25% IT team turnover last year",
    "Active 'digital transformation' initiative = competing priorities"
  ],
  "integration_complexity": "Simple" | "Moderate" | "Complex",
  "recommended_approach": "Standard" | "Phased" | "Pilot-first",
  "success_factors": [
    "Executive sponsor commitment",
    "Dedicated integration resource",
    "Realistic timeline expectations"
  ],
  "risk_mitigations": [
    "Start with single department pilot",
    "Budget 2x standard implementation time",
    "Assign dedicated change management resource"
  ]
}
```

Be specific about risk mitigations - these directly inform implementation planning.

""" + JSON_OUTPUT_RULES


class ImplementationRiskAgent(BaseAgent):
    """
    Agent that assesses implementation risk factors.
    """

    @property
    def name(self) -> str:
        return "ImplementationRisk"

    @property
    def system_prompt(self) -> str:
        return IMPLEMENTATION_RISK_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search"]

    async def research(self, profile: CompanyProfile) -> ImplementationRiskInsights:
        """
        Research implementation risk factors.
        """
        prompt = f"""Assess implementation risk factors for deploying Fluency at {profile.name}.

Company Context:
- Domain: {profile.domain}
- Industry: {profile.industry}
- Type: {profile.company_type.value}
- Size: {profile.employee_count or 'Unknown'}

Research in this order:
1. Search G2/Capterra reviews for "{profile.name}" mentioning implementation
2. Search Glassdoor for "{profile.name}" reviews about IT systems or tools
3. Search "{profile.name} IT project" or "{profile.name} digital transformation" for news
4. Search job postings for "change management" or "transformation" roles
5. Look for IT/Engineering leadership changes
6. Assess industry-specific risks for {profile.industry}

Consider what could go wrong and how to mitigate it.
Return comprehensive JSON with your findings."""

        result = await self.run(prompt)
        data = result.get("json") or {}

        # Build claims from past issues
        claims = []
        for item in data.get("past_implementation_issues", []):
            if isinstance(item, dict):
                claims.append(Claim(
                    claim=item.get("issue", ""),
                    category="Implementation Risk",
                    confidence=Confidence(item.get("confidence", "MEDIUM")),
                    evidence=[Evidence(
                        url=item.get("source", profile.domain),
                        quote="",
                        source_type="review",
                        source_tier=SourceTier.TIER_2
                    )] if item.get("source") else []
                ))

        return ImplementationRiskInsights(
            risk_level=data.get("risk_level", "MEDIUM"),
            past_implementation_issues=claims,
            tech_debt_signals=data.get("tech_debt_signals", []),
            change_management_concerns=data.get("change_management_concerns", []),
            integration_complexity=data.get("integration_complexity", "Moderate"),
            recommended_approach=data.get("recommended_approach", "Standard"),
            success_factors=data.get("success_factors", []),
            risk_mitigations=data.get("risk_mitigations", []),
            claims=claims
        )
