"""
Tech Stack Research Agent - Stage 2 of the research pipeline.

Researches technology integrations, app marketplaces, and infrastructure.
"""

from .base import BaseAgent
from models import CompanyProfile, TechStackFindings, Integration, Claim, Evidence, Confidence, SourceTier


TECH_STACK_SYSTEM_PROMPT = """You are a technology stack research agent for Fluency AI deployment preparation.

Your task is to research a company's technology ecosystem to understand integration opportunities and technical fit.

Given a company profile, you must:

1. CHECK APP MARKETPLACES - Look for the company in:
   - Okta Integration Network: Search for them at okta.com/integrations
   - Salesforce AppExchange: appexchange.salesforce.com
   - AWS Marketplace: aws.amazon.com/marketplace
   - Azure Marketplace: azuremarketplace.microsoft.com
   - Google Workspace Marketplace

2. IDENTIFY INTEGRATIONS - Look for evidence of:
   - SSO/Identity: Okta, Azure AD, OneLogin, Ping Identity
   - CRM: Salesforce, HubSpot, Microsoft Dynamics
   - Cloud: AWS, Azure, GCP
   - Collaboration: Slack, Microsoft Teams
   - Process Mining: Celonis, UiPath, Blue Prism
   - Documentation: Confluence, Notion, SharePoint

3. SUBDOMAIN ANALYSIS - Use crt_sh_lookup to find subdomains that reveal:
   - Identity providers (sso.*, okta.*, auth.*)
   - Regional presence (eu.*, apac.*, uk.*)
   - Infrastructure (api.*, cdn.*, staging.*)

4. JOB POSTINGS - Search for job postings that mention specific technologies

For each integration found, record:
- Tool name and category
- Source URL
- Confidence: HIGH (official listing), MEDIUM (job posting), LOW (inferred)

Return your findings as JSON:
```json
{
  "integrations": [
    {
      "tool_name": "Salesforce",
      "category": "CRM",
      "confidence": "HIGH",
      "source_url": "https://appexchange...",
      "quote": "Listed on AppExchange"
    }
  ],
  "identity_provider": "Okta" or null,
  "cloud_provider": "AWS" or null,
  "subdomains": {
    "identity": ["sso.example.com", "okta.example.com"],
    "regional": ["eu.example.com"],
    "infrastructure": ["api.example.com"]
  }
}
```

Focus on HIGH confidence integrations from official sources. These are most valuable for Fluency deployment planning.
"""


class TechStackAgent(BaseAgent):
    """
    Stage 2 agent that researches technology stack and integrations.
    """

    @property
    def name(self) -> str:
        return "TechStack"

    @property
    def system_prompt(self) -> str:
        return TECH_STACK_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search", "crt_sh_lookup"]

    async def research(self, profile: CompanyProfile) -> TechStackFindings:
        """
        Research technology stack for a company.

        Returns TechStackFindings with integrations and infrastructure info.
        """
        # Build the research prompt
        prompt = f"""Research the technology stack and integrations of {profile.name}.

Company Details:
- Domain: {profile.domain}
- Type: {profile.company_type.value}
- Industry: {profile.industry}

Start with a subdomain lookup using crt_sh_lookup, then check app marketplaces for integrations.
"""

        # Run the agent
        result = await self.run(prompt)

        # Parse the JSON response
        data = result.get("json") or {}

        # Build integrations list
        integrations = []
        for int_data in data.get("integrations", []):
            confidence = Confidence.MEDIUM
            try:
                confidence = Confidence(int_data.get("confidence", "MEDIUM"))
            except ValueError:
                pass

            evidence = None
            if int_data.get("source_url"):
                source_tier = SourceTier.TIER_0 if confidence == Confidence.HIGH else SourceTier.TIER_1
                evidence = Evidence(
                    url=int_data["source_url"],
                    quote=int_data.get("quote", ""),
                    source_type="marketplace" if "appexchange" in int_data["source_url"].lower() or "marketplace" in int_data["source_url"].lower() else "web",
                    source_tier=source_tier
                )

            integrations.append(Integration(
                tool_name=int_data.get("tool_name", "Unknown"),
                category=int_data.get("category", "Unknown"),
                confidence=confidence,
                evidence=evidence
            ))

        # Extract subdomains
        subdomains = data.get("subdomains", {})
        all_subdomains = []
        for category_subs in subdomains.values():
            if isinstance(category_subs, list):
                all_subdomains.extend(category_subs)

        return TechStackFindings(
            integrations=integrations,
            identity_provider=data.get("identity_provider"),
            cloud_provider=data.get("cloud_provider"),
            subdomains_found=all_subdomains,
            claims=[]
        )
