"""
Discovery Agent - Stage 1 of the research pipeline.

Extracts company identity, classifies company type, and builds a URL bank for downstream agents.
"""

from .base import BaseAgent
from models import CompanyProfile, CompanyType, URLBank
from logger import get_logger

logger = get_logger(__name__)


DISCOVERY_SYSTEM_PROMPT = """You are a company research agent. Your task is to identify and classify companies AND discover URLs for downstream research agents.

Given a URL, you must:

## PART 1: COMPANY IDENTIFICATION
1. Fetch the homepage and /about page to understand the company
2. Extract the company's official name (and legal name if different)
3. Determine the company type:
   - PUBLIC: Has a stock ticker, traded on stock exchange, has SEC filings
   - PRIVATE_ENTERPRISE: Large company (500+ employees), not publicly traded
   - STARTUP: Venture-backed, founded recently (last 10 years), smaller company
4. Identify the industry vertical (e.g., Insurance, SaaS, Healthcare, Finance, etc.)
5. Find the headquarters location, employee count, founding year

## PART 2: URL BANK BUILDING (CRITICAL FOR COST EFFICIENCY)
After identifying the company, use web_search to find URLs for downstream agents. This is crucial - other agents will use these URLs directly instead of searching.

Search for and record URLs for:
1. SECURITY & TRUST:
   - "{company} trust center" or "{company} security"
   - "{company} SOC 2" or "{company} compliance"

2. REVIEWS & REPUTATION:
   - "{company} G2 reviews"
   - "{company} Capterra reviews"
   - "{company} Glassdoor"

3. SOCIAL & PROFESSIONAL:
   - "site:linkedin.com/company {company}"
   - "{company} LinkedIn executives CTO CEO"
   - "site:github.com {company}"

4. NEWS & PRESS:
   - "{company} news 2024 2025"
   - "{company} funding announcement" or "{company} acquisition"

5. JOBS:
   - "{company} careers" or "{company} jobs LinkedIn"

6. REGULATORY (if relevant):
   - "{company} data breach" or "{company} FTC"
   - "{company} SEC filing" (if public)

Record the ACTUAL URLs from search results, not just that you searched.

Return your findings as JSON:
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
  "description": "Brief description of what the company does",
  "url_bank": {
    "homepage": "https://company.com",
    "about_page": "https://company.com/about",
    "careers_page": "https://company.com/careers",
    "trust_center": "https://trust.company.com" or null,
    "security_page": "https://company.com/security" or null,
    "privacy_policy": "https://company.com/privacy" or null,
    "linkedin_company": "https://linkedin.com/company/..." or null,
    "linkedin_executives": ["https://linkedin.com/in/ceo-name", ...],
    "github_org": "https://github.com/company" or null,
    "g2_page": "https://g2.com/products/company" or null,
    "capterra_page": "https://capterra.com/..." or null,
    "glassdoor_page": "https://glassdoor.com/..." or null,
    "news_articles": ["url1", "url2", ...],
    "press_releases": ["url1", ...],
    "job_board_urls": ["https://linkedin.com/company/x/jobs", ...],
    "sec_filings": ["https://sec.gov/..."] or [],
    "regulatory_mentions": ["url1", ...],
    "searches_performed": ["query1", "query2", ...]
  }
}
```

IMPORTANT: The url_bank saves money by allowing downstream agents to fetch directly instead of searching. Be thorough in URL discovery - this is where we consolidate search costs.
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
        # Discovery now uses web_search to build URL bank for downstream agents
        return ["web_fetch", "web_search"]

    async def discover(self, url: str) -> CompanyProfile:
        """
        Discover and classify a company from its URL.

        Returns a CompanyProfile with basic company information and URL bank.
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
            logger.warning(f"Invalid company type '{company_type_str}', defaulting to PRIVATE_ENTERPRISE")
            company_type = CompanyType.PRIVATE_ENTERPRISE

        # Parse URL bank from response
        url_bank_data = data.get("url_bank", {})
        url_bank = URLBank(
            homepage=url_bank_data.get("homepage") or url,
            about_page=url_bank_data.get("about_page"),
            careers_page=url_bank_data.get("careers_page"),
            trust_center=url_bank_data.get("trust_center"),
            security_page=url_bank_data.get("security_page"),
            privacy_policy=url_bank_data.get("privacy_policy"),
            compliance_page=url_bank_data.get("compliance_page"),
            integrations_page=url_bank_data.get("integrations_page"),
            api_docs=url_bank_data.get("api_docs"),
            status_page=url_bank_data.get("status_page"),
            linkedin_company=url_bank_data.get("linkedin_company"),
            linkedin_executives=url_bank_data.get("linkedin_executives", []),
            github_org=url_bank_data.get("github_org"),
            g2_page=url_bank_data.get("g2_page"),
            capterra_page=url_bank_data.get("capterra_page"),
            glassdoor_page=url_bank_data.get("glassdoor_page"),
            news_articles=url_bank_data.get("news_articles", []),
            press_releases=url_bank_data.get("press_releases", []),
            blog_posts=url_bank_data.get("blog_posts", []),
            job_board_urls=url_bank_data.get("job_board_urls", []),
            sec_filings=url_bank_data.get("sec_filings", []),
            regulatory_mentions=url_bank_data.get("regulatory_mentions", []),
            additional_urls=url_bank_data.get("additional_urls", {}),
            searches_performed=url_bank_data.get("searches_performed", []),
        )

        # Log URL bank stats for monitoring
        url_count = sum([
            1 if url_bank.trust_center else 0,
            1 if url_bank.linkedin_company else 0,
            1 if url_bank.g2_page else 0,
            len(url_bank.news_articles),
            len(url_bank.linkedin_executives),
            len(url_bank.job_board_urls),
        ])
        logger.info(f"[Discovery] URL bank built: {url_count} URLs from {len(url_bank.searches_performed)} searches")

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
            description=data.get("description", ""),
            url_bank=url_bank
        )
