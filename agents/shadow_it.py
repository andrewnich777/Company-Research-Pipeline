"""
Shadow IT & Legacy Discovery Agent - Finds the "unspoken" tech stack.

Generic tools see the official stack. This agent finds the connective tissue -
legacy systems still in use that marketing doesn't mention but Fluency needs
to integrate with.
"""

from .base import BaseAgent, JSON_OUTPUT_RULES
from models import (
    CompanyProfile, ShadowITInsights, Claim, Evidence,
    Confidence, SourceTier
)


SHADOW_IT_SYSTEM_PROMPT = """You are a shadow IT and legacy systems intelligence agent for Fluency AI deployment research.

Your goal is to find the "unspoken" stack - legacy systems that Fluency will need to integrate with.

## WHY THIS MATTERS
- Companies market themselves as "modern" but often still have legacy dependencies
- Job postings reveal what they're ACTUALLY maintaining vs. what they claim
- Shadow IT (tools used outside official stack) can block or complicate deployments
- Understanding tech debt level helps set realistic implementation timelines

## SIGNALS TO LOOK FOR

### Legacy System Signals in Job Postings
- "Maintaining legacy X while migrating to Y"
- "Experience with Oracle/Mainframe/COBOL alongside modern stack"
- "Help modernize our X system"
- "Bridge between legacy and cloud"
- "Support existing Oracle/SAP/mainframe systems"

### Shadow IT Indicators
- Multiple tools in same category (Jira AND Monday AND Asana)
- Department-specific tools mentioned in different postings
- "Standardization" or "consolidation" initiatives mentioned
- Different teams using different tools for same purpose

### Tech Debt Confession Signals
- Job postings for "modernization" roles
- News about "digital transformation" initiatives
- Customer reviews mentioning integration difficulties
- "Technical debt reduction" in job descriptions

### Hidden Dependencies
- On-prem infrastructure mentioned alongside cloud
- Database migration projects (reveals current state)
- "Hybrid cloud" language
- VPN requirements for internal systems

## LEGACY SYSTEMS TO WATCH FOR
- Oracle (DB, EBS, Fusion)
- SAP (ECC, S/4HANA)
- IBM mainframe/AS400
- Microsoft Dynamics (older versions)
- Salesforce Classic
- On-premise SharePoint
- Custom-built internal tools
- Legacy data warehouses (Teradata, Netezza)

## YOUR RESEARCH PROCESS

1. Search job postings for "legacy" and "migration" mentions
2. Look for "modernization" or "digital transformation" roles
3. Search for infrastructure job posts mentioning on-prem + cloud
4. Check for mentions of specific legacy systems
5. Analyze Glassdoor reviews for tech debt complaints
6. Search news for transformation initiatives

## OUTPUT FORMAT
```json
{
  "legacy_systems_detected": [
    {
      "system": "Oracle EBS",
      "evidence": "Job posting requires 'Oracle EBS experience for ongoing support while migrating to cloud ERP'",
      "migration_status": "In progress",
      "source": "https://..."
    }
  ],
  "shadow_it_tools": ["Notion (marketing)", "Confluence (engineering)", "SharePoint (finance)"],
  "tech_debt_level": "HIGH" | "MEDIUM" | "LOW",
  "modernization_in_progress": true,
  "hidden_dependencies": ["Oracle EBS", "On-prem Active Directory", "Legacy data warehouse"],
  "integration_story": "Legacy Connector - emphasize hybrid capabilities, not pure cloud",
  "deal_risk": "May need custom integration work for Oracle EBS connection. Budget 2-4 weeks additional implementation time."
}
```

Be specific about what Fluency needs to integrate with - this directly impacts implementation planning.

""" + JSON_OUTPUT_RULES


class ShadowITAgent(BaseAgent):
    """
    Agent that discovers legacy systems and shadow IT in the organization.
    """

    @property
    def name(self) -> str:
        return "ShadowIT"

    @property
    def system_prompt(self) -> str:
        return SHADOW_IT_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search"]

    async def research(self, profile: CompanyProfile) -> ShadowITInsights:
        """
        Research shadow IT and legacy systems.
        """
        prompt = f"""Research legacy systems and shadow IT at {profile.name}.

Company Context:
- Domain: {profile.domain}
- Industry: {profile.industry}
- Type: {profile.company_type.value}
- Size: {profile.employee_count or 'Unknown'}

Research in this order:
1. Search "{profile.name} jobs legacy" and "{profile.name} jobs migration"
2. Search "{profile.name} jobs Oracle" and "{profile.name} jobs SAP"
3. Search "{profile.name} digital transformation" or "{profile.name} modernization"
4. Search "{profile.name} jobs mainframe" and "{profile.name} jobs AS400"
5. Check Glassdoor reviews for tech debt mentions
6. Search "{profile.name} hybrid cloud" or "{profile.name} on-premise"

Focus on finding:
- What legacy systems are they maintaining?
- Are they in active migration or steady state?
- What integration challenges might Fluency face?

Return comprehensive JSON with your findings."""

        result = await self.run(prompt)
        data = result.get("json") or {}

        # Build claims from legacy systems detected
        claims = []
        for item in data.get("legacy_systems_detected", []):
            claims.append(Claim(
                claim=f"Legacy system detected: {item.get('system', 'Unknown')} - {item.get('migration_status', 'Unknown status')}",
                category="Shadow IT",
                confidence=Confidence.MEDIUM,
                evidence=[Evidence(
                    url=item.get("source", profile.domain),
                    quote=item.get("evidence", ""),
                    source_type="job_posting",
                    source_tier=SourceTier.TIER_1
                )] if item.get("source") else []
            ))

        return ShadowITInsights(
            legacy_systems_detected=data.get("legacy_systems_detected", []),
            shadow_it_tools=data.get("shadow_it_tools", []),
            tech_debt_level=data.get("tech_debt_level", "MEDIUM"),
            modernization_in_progress=data.get("modernization_in_progress", False),
            hidden_dependencies=data.get("hidden_dependencies", []),
            integration_story=data.get("integration_story", "Standard"),
            deal_risk=data.get("deal_risk", ""),
            claims=claims
        )
