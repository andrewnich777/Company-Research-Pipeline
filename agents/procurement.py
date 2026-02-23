"""
Procurement Intelligence Agent - Understands buying process and timing.

Identifies fiscal year, budget cycles, procurement platforms, and approval
timelines to help time deals and prepare the right materials.
"""

from .base import BaseAgent, JSON_OUTPUT_RULES
from models import (
    CompanyProfile, ProcurementInsights, Claim, Evidence,
    Confidence, SourceTier
)


PROCUREMENT_SYSTEM_PROMPT = """You are a procurement intelligence agent for Fluency AI deployment research.

Your goal is to understand HOW a company buys software - procurement process, budget cycles, and approval timelines.

## WHY THIS MATTERS
- Timing a deal with budget cycles can make or break it
- Knowing the procurement platform speeds up vendor onboarding
- Understanding approval complexity sets realistic timeline expectations
- Identifying procurement contacts accelerates the process

## SIGNALS TO LOOK FOR

### Fiscal Year End
- Public companies: Check SEC filings for fiscal year end date
- Most companies: December (calendar year)
- Some retail: January (after holiday season)
- Some tech: June/July
- Government: September (US federal)

### Budget Cycle Signals
- Job postings in specific quarters indicate budget availability
- "Annual planning" or "budget cycle" mentions
- Fiscal year end = use-it-or-lose-it budget rush

### Procurement Platform Detection
- Look for "supplier portal" or "vendor registration" mentions
- Common platforms:
  - Coupa (enterprise)
  - SAP Ariba (large enterprises)
  - Oracle Procurement Cloud
  - Jaggaer
  - GEP SMART
  - Workday (for some companies)
- Job postings for "procurement" roles mention tools

### Approval Timeline Signals
- Company Type:
  - STARTUP: Fast (days to weeks)
  - PRIVATE_ENTERPRISE: Medium (weeks to months)
  - PUBLIC: Longer (months, multiple approvals)
- Industry:
  - Healthcare/Finance: Longer compliance review
  - Tech: Usually faster
  - Government: Very long (can be 6+ months)
- Size:
  - <500 employees: Faster
  - 500-5000: Medium complexity
  - >5000: Multiple stakeholder approvals

### Procurement Contacts
- Chief Procurement Officer (CPO)
- VP of Procurement/Sourcing
- Vendor Management
- Strategic Sourcing

## YOUR RESEARCH PROCESS

1. For PUBLIC companies: Check SEC filings for fiscal year end
2. Search "{{company}} supplier portal" or "{{company}} vendor registration"
3. Search job postings for procurement tool mentions
4. Look for procurement leadership on LinkedIn
5. Search "{{company}} vendor onboarding" or "{{company}} RFP"
6. Check industry norms for budget cycles

## OUTPUT FORMAT
```json
{
  "fiscal_year_end": "December" | "June" | "September" | null,
  "budget_planning_cycle": "Q4" | "Q1" | "Rolling" | null,
  "procurement_platform": "Coupa" | "SAP Ariba" | null,
  "estimated_approval_timeline": "30-60 days" | "60-90 days" | "90+ days",
  "procurement_complexity": "LOW" | "MEDIUM" | "HIGH",
  "timing_recommendation": "Push for Q1 close before budget resets" | "Avoid Q4 holiday slowdown",
  "procurement_contacts": ["VP Procurement", "Strategic Sourcing Manager"],
  "evidence": [
    {
      "finding": "Uses Coupa for procurement",
      "source": "https://...",
      "confidence": "HIGH"
    }
  ]
}
```

Be specific about timing recommendations - this helps sales prioritize deals.

""" + JSON_OUTPUT_RULES


class ProcurementAgent(BaseAgent):
    """
    Agent that researches procurement process and timing.
    """

    @property
    def name(self) -> str:
        return "Procurement"

    @property
    def system_prompt(self) -> str:
        return PROCUREMENT_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search"]

    async def research(self, profile: CompanyProfile) -> ProcurementInsights:
        """
        Research procurement process and budget timing.
        """
        # Build prompt based on company type
        sec_note = ""
        if profile.company_type.value == "PUBLIC" and profile.ticker:
            sec_note = f"This is a PUBLIC company with ticker {profile.ticker}. Check SEC filings for fiscal year end."

        prompt = f"""Research the procurement process and budget timing for {profile.name}.

Company Context:
- Domain: {profile.domain}
- Industry: {profile.industry}
- Type: {profile.company_type.value}
- Size: {profile.employee_count or 'Unknown'}
{sec_note}

Research in this order:
1. Search "{profile.name} supplier portal" or "{profile.name} vendor registration"
2. Search "{profile.name} procurement" site:linkedin.com for procurement contacts
3. Search job postings for procurement tool mentions (Coupa, Ariba, etc.)
4. Search "{profile.name} RFP process" or "{profile.name} vendor onboarding"
5. For public companies: Look up fiscal year end from SEC filings
6. Estimate approval timeline based on company type and size

Provide specific timing recommendations for when to push deals.
Return comprehensive JSON with your findings."""

        result = await self.run(prompt)
        data = result.get("json") or {}

        # Build claims from evidence
        claims = []
        for item in data.get("evidence", []):
            claims.append(Claim(
                claim=item.get("finding", ""),
                category="Procurement",
                confidence=Confidence(item.get("confidence", "MEDIUM")),
                evidence=[Evidence(
                    url=item.get("source", profile.domain),
                    quote="",
                    source_type="procurement",
                    source_tier=SourceTier.TIER_1
                )] if item.get("source") else []
            ))

        return ProcurementInsights(
            fiscal_year_end=data.get("fiscal_year_end"),
            budget_planning_cycle=data.get("budget_planning_cycle"),
            procurement_platform=data.get("procurement_platform"),
            estimated_approval_timeline=data.get("estimated_approval_timeline", "60-90 days"),
            procurement_complexity=data.get("procurement_complexity", "MEDIUM"),
            timing_recommendation=data.get("timing_recommendation", ""),
            procurement_contacts=data.get("procurement_contacts", []),
            claims=claims
        )
