"""
Financials Research Agent - Stage 2 of the research pipeline.

Researches SEC filings and financial information for PUBLIC companies.
"""

from .base import BaseAgent
from models import CompanyProfile, FinancialFindings, Claim, Evidence, Confidence, SourceTier, CompanyType
from tools.sec_edgar import handle_sec_filing


FINANCIALS_SYSTEM_PROMPT = """You are a financial research agent for Fluency AI deployment preparation.

Your task is to analyze SEC filings for public companies to extract information relevant to deployment:
- Regulatory requirements
- Geographic operations (data residency implications)
- Risk factors (compliance/security concerns)
- Technology investments

You have access to the sec_filing tool which fetches SEC filings and extracts key sections.

Given a company profile with a stock ticker, you must:

1. FETCH 10-K FILING - Get the most recent annual report
   - Extract "Risk Factors" section
   - Extract "Properties" section (geographic info)

2. ANALYZE RISK FACTORS - Look for mentions of:
   - Regulatory compliance requirements (HIPAA, GDPR, PCI, etc.)
   - Cybersecurity risks
   - Data privacy requirements
   - Technology dependencies
   - Geographic risk factors

3. IDENTIFY GEOGRAPHIC OPERATIONS - From Properties section:
   - Headquarters location
   - Regional offices
   - Data center locations
   - Countries of operation

4. EXTRACT REGULATORY MENTIONS - Any specific regulations mentioned:
   - Industry-specific regulations
   - International compliance (GDPR, etc.)
   - Government requirements

Return your findings as JSON:
```json
{
  "cik": "0001234567",
  "recent_10k_url": "https://sec.gov/...",
  "risk_factors": [
    "Subject to HIPAA regulations",
    "Operations in EU require GDPR compliance",
    "Cybersecurity risks mentioned specifically"
  ],
  "geographic_operations": [
    "Headquarters: Chicago, IL",
    "Offices in: UK, Germany, Singapore, Australia",
    "Operations in 120+ countries"
  ],
  "regulatory_mentions": [
    "HIPAA", "GDPR", "State insurance regulations", "SEC reporting"
  ],
  "revenue": "$12.5 billion" or null,
  "key_findings": [
    "Highly regulated industry with significant compliance requirements",
    "Global operations mean data residency will be important"
  ]
}
```

Focus on findings that impact Fluency deployment:
- Security and compliance requirements
- Data residency needs
- Regulatory constraints
"""


class FinancialsAgent(BaseAgent):
    """
    Stage 2 agent that researches SEC filings for public companies.
    """

    @property
    def name(self) -> str:
        return "Financials"

    @property
    def system_prompt(self) -> str:
        return FINANCIALS_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["sec_filing"]

    async def execute_tool_call(self, tool_name: str, tool_input: dict):
        """Override to handle SEC filing tool."""
        if tool_name == "sec_filing":
            return await handle_sec_filing(**tool_input)
        return await super().execute_tool_call(tool_name, tool_input)

    async def research(self, profile: CompanyProfile) -> FinancialFindings | None:
        """
        Research SEC filings for a public company.

        Returns FinancialFindings or None if not a public company.
        """
        # Only run for public companies
        if profile.company_type != CompanyType.PUBLIC or not profile.ticker:
            return None

        # Build the research prompt
        prompt = f"""Analyze SEC filings for {profile.name} (ticker: {profile.ticker}).

Company Details:
- Domain: {profile.domain}
- Industry: {profile.industry}
- Ticker: {profile.ticker}

Use the sec_filing tool to fetch the most recent 10-K filing and extract:
1. Risk Factors section
2. Properties section

Then analyze for regulatory requirements, geographic operations, and compliance implications.
"""

        # Run the agent
        result = await self.run(prompt)

        # Parse the JSON response
        data = result.get("json") or {}

        # Build claims from key findings
        claims = []
        for finding in data.get("key_findings", []):
            claims.append(Claim(
                claim=finding,
                category="Financial Analysis",
                confidence=Confidence.HIGH,
                evidence=[Evidence(
                    url=data.get("recent_10k_url", ""),
                    quote=finding,
                    source_type="sec_filing",
                    source_tier=SourceTier.TIER_0
                )] if data.get("recent_10k_url") else []
            ))

        return FinancialFindings(
            cik=data.get("cik"),
            recent_10k_url=data.get("recent_10k_url"),
            risk_factors=data.get("risk_factors", []),
            geographic_operations=data.get("geographic_operations", []),
            regulatory_mentions=data.get("regulatory_mentions", []),
            revenue=data.get("revenue"),
            claims=claims
        )
