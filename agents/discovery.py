"""
Discovery Agent - Stage 1 of the research pipeline.

Extracts company identity, classifies company type, and gathers basic information.
"""

from .base import BaseAgent
from models import CompanyProfile, CompanyType


DISCOVERY_SYSTEM_PROMPT = """You are a company research agent. Your task is to identify and classify companies based on their website.

Given a URL, you must:

1. Fetch the homepage and /about page to understand the company
2. Extract the company's official name (and legal name if different)
3. Determine the company type:
   - PUBLIC: Has a stock ticker, traded on stock exchange, has SEC filings
   - PRIVATE_ENTERPRISE: Large company (500+ employees), not publicly traded
   - STARTUP: Venture-backed, founded recently (last 10 years), smaller company
4. Identify the industry vertical (e.g., Insurance, SaaS, Healthcare, Finance, etc.)
5. Find the headquarters location
6. Estimate employee count if visible
7. Find the founding year if visible

Use the web_fetch tool to retrieve pages. Look for:
- "About" or "Company" pages
- Footer information (copyright, addresses)
- Leadership/team pages
- "Investor Relations" (indicates PUBLIC)
- Funding announcements (indicates STARTUP)
- Stock ticker symbols in headers/footers (indicates PUBLIC)

Return your findings as JSON in the following format:
```json
{
  "name": "Company Name",
  "legal_name": "Legal Entity Name Inc." or null,
  "domain": "example.com",
  "company_type": "PUBLIC" | "PRIVATE_ENTERPRISE" | "STARTUP",
  "ticker": "TICK" or null,
  "industry": "Industry Name",
  "hq_location": "City, Country" or null,
  "employee_count": "1000-5000" or null,
  "founded_year": 2015 or null,
  "description": "Brief description of what the company does"
}
```

Be thorough but efficient - don't fetch more than 3-4 pages.
"""


class DiscoveryAgent(BaseAgent):
    """
    Stage 1 agent that identifies and classifies companies.
    """

    @property
    def name(self) -> str:
        return "Discovery"

    @property
    def system_prompt(self) -> str:
        return DISCOVERY_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch"]

    async def discover(self, url: str) -> CompanyProfile:
        """
        Discover and classify a company from its URL.

        Returns a CompanyProfile with basic company information.
        """
        # Normalize URL
        if not url.startswith("http"):
            url = f"https://{url}"

        # Extract domain for reference
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "")

        # Run the agent
        result = await self.run(f"Research the company at: {url}")

        # Parse the JSON response
        if result.get("json"):
            data = result["json"]
        else:
            # Try to extract from text if JSON parsing failed
            data = {
                "name": domain.split(".")[0].title(),
                "domain": domain,
                "company_type": "PRIVATE_ENTERPRISE",
                "industry": "Unknown",
                "description": "Could not extract company information"
            }

        # Convert to CompanyProfile
        company_type_str = data.get("company_type", "PRIVATE_ENTERPRISE")
        try:
            company_type = CompanyType(company_type_str)
        except ValueError:
            company_type = CompanyType.PRIVATE_ENTERPRISE

        return CompanyProfile(
            name=data.get("name", domain),
            legal_name=data.get("legal_name"),
            domain=data.get("domain", domain),
            company_type=company_type,
            ticker=data.get("ticker"),
            industry=data.get("industry", "Unknown"),
            hq_location=data.get("hq_location"),
            employee_count=data.get("employee_count"),
            founded_year=data.get("founded_year"),
            description=data.get("description", "")
        )
