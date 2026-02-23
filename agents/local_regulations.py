"""
Local Regulations Agent - Identifies region-specific compliance requirements.

Detects operating regions and maps them to applicable regulations like GDPR,
CCPA, works councils, and data localization requirements.
"""

from .base import BaseAgent, JSON_OUTPUT_RULES
from models import (
    CompanyProfile, LocalRegulationsInsights, Claim, Evidence,
    Confidence, SourceTier
)


LOCAL_REGULATIONS_SYSTEM_PROMPT = """You are a regional compliance intelligence agent for Fluency AI deployment research.

Your goal is to identify operating regions and applicable regulations for Fluency deployment.

## WHY THIS MATTERS
- Different regions have different compliance requirements
- EU requires works council approval for employee-facing tools
- GDPR, CCPA, and other regulations affect data handling
- Some regions require data localization
- Missing regional requirements can block or delay deployment

## REGION-TO-REGULATION MAPPING

### European Union (EU/EEA)
- GDPR: Data protection, consent, DPO requirement
- Works Councils: Germany, France, Netherlands require works council approval for employee-facing software
- Data Localization: Some sectors require EU data residency
- Right to be forgotten, data portability

### United Kingdom (UK)
- UK GDPR (post-Brexit version)
- Similar to EU but separate enforcement
- ICO oversight

### California (US-CA)
- CCPA/CPRA: Consumer privacy rights
- Right to deletion, opt-out of sale
- Applies to companies meeting thresholds

### Healthcare (Any Region)
- HIPAA (US): PHI protection, BAA required
- Patient data handling requirements

### Financial Services (Any Region)
- SOX: Public company financial controls
- PCI-DSS: Payment card data
- GLBA: Financial privacy
- SEC/FINRA: Regulatory requirements

### Government/Defense (US)
- FedRAMP: Cloud security for federal agencies
- ITAR: Defense-related data controls
- CMMC: Defense contractor cybersecurity

### China
- PIPL: Personal Information Protection Law
- Data localization requirements
- Cross-border transfer restrictions

## YOUR RESEARCH PROCESS

1. DETECT OPERATING REGIONS
   - Check job posting locations
   - Look for office addresses on careers/about page
   - Check SEC filings for geographic segments (public companies)
   - Look for regional subdomains (eu.*, uk.*, apac.*)

2. MAP TO REGULATIONS
   - Industry-specific regulations (healthcare → HIPAA, finance → SOX)
   - Region-specific regulations (EU → GDPR, California → CCPA)
   - Check privacy policy for compliance statements

3. IDENTIFY SPECIAL REQUIREMENTS
   - Works council mentions in EU job postings
   - Data residency mentions
   - Cross-border transfer restrictions

## OUTPUT FORMAT
```json
{
  "operating_regions": ["US", "EU", "UK", "US-CA"],
  "applicable_regulations": [
    {
      "regulation": "GDPR",
      "region": "EU",
      "requirements": "Data processing agreement, DPO notification, consent management",
      "source": "https://..."
    },
    {
      "regulation": "Works Council",
      "region": "Germany",
      "requirements": "Works council approval required for employee-facing deployment",
      "source": "https://..."
    }
  ],
  "data_localization_required": true,
  "works_council_required": true,
  "cross_border_restrictions": ["EU data must stay in EU/EEA or approved countries"],
  "compliance_actions": [
    "Prepare DPA for EU deployment",
    "Budget 4-6 weeks for German works council approval",
    "Confirm EU data residency option"
  ]
}
```

Be specific about compliance actions - these directly impact deployment timeline.

""" + JSON_OUTPUT_RULES


class LocalRegulationsAgent(BaseAgent):
    """
    Agent that identifies regional compliance requirements.
    """

    @property
    def name(self) -> str:
        return "LocalRegulations"

    @property
    def system_prompt(self) -> str:
        return LOCAL_REGULATIONS_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search", "crt_sh_lookup"]

    async def research(self, profile: CompanyProfile) -> LocalRegulationsInsights:
        """
        Research regional presence and compliance requirements.
        """
        # Determine if public company (has financials agent data)
        prompt = f"""Research the geographic presence and regulatory requirements for {profile.name}.

Company Context:
- Domain: {profile.domain}
- Industry: {profile.industry}
- Type: {profile.company_type.value}
- Size: {profile.employee_count or 'Unknown'}

Research in this order:
1. Use crt_sh_lookup to find regional subdomains (eu.*, uk.*, apac.*)
2. Search "{profile.name} careers" to find office locations
3. Check {profile.domain}/about or {profile.domain}/locations for office addresses
4. Search "{profile.name} GDPR" and "{profile.name} privacy policy"
5. Search "{profile.name} works council" (for EU employee-facing deployments)
6. Check if industry triggers specific regulations (healthcare → HIPAA, finance → SOX)

Identify all regions they operate in and what regulations apply.
Return comprehensive JSON with your findings."""

        result = await self.run(prompt)
        data = result.get("json") or {}

        # Build claims from regulations
        claims = []
        for reg in data.get("applicable_regulations", []):
            claims.append(Claim(
                claim=f"{reg.get('regulation', 'Unknown')} compliance required for {reg.get('region', 'Unknown')}",
                category="Regulatory",
                confidence=Confidence.MEDIUM,
                evidence=[Evidence(
                    url=reg.get("source", profile.domain),
                    quote=reg.get("requirements", ""),
                    source_type="regulatory",
                    source_tier=SourceTier.TIER_1
                )] if reg.get("source") else []
            ))

        return LocalRegulationsInsights(
            operating_regions=data.get("operating_regions", []),
            applicable_regulations=data.get("applicable_regulations", []),
            data_localization_required=data.get("data_localization_required", False),
            works_council_required=data.get("works_council_required", False),
            cross_border_restrictions=data.get("cross_border_restrictions", []),
            compliance_actions=data.get("compliance_actions", []),
            claims=claims
        )
