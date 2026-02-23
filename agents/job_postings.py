"""
Job Postings Agent - Extracts real tech stack and hiring signals from job listings.

This agent provides "deeper intelligence" by analyzing what companies actually
require in job postings, revealing:
- Real tech stack (vs. marketing claims)
- Hiring velocity (budget indicator)
- Team growth areas (strategic priorities)
- Process tools in use
"""

from .base import BaseAgent, URL_BANK_INSTRUCTIONS, JSON_OUTPUT_RULES, build_url_bank_section
from models import (
    CompanyProfile, JobPostingInsights, Claim, Evidence,
    Confidence, SourceTier
)


JOB_POSTINGS_SYSTEM_PROMPT = """You are a job postings intelligence agent for Fluency AI deployment research.

Your goal is to extract REAL technology and organizational intelligence from job postings.

""" + URL_BANK_INSTRUCTIONS + """

## WHY THIS MATTERS
- Job postings reveal actual tech stack (required skills = what they use)
- Hiring patterns indicate budget health and strategic priorities
- Process tools mentioned = integration opportunities for Fluency
- Seniority distribution indicates organizational maturity

## YOUR RESEARCH PROCESS

1. CHECK PRE-DISCOVERED URLs FIRST
   If careers pages or job board URLs are provided, fetch them directly.
   Only search if URLs are not provided or don't have enough listings.

2. EXTRACT TECHNOLOGY SIGNALS
   From job requirements, identify:
   - Programming languages (Python, Java, Go, etc.)
   - Infrastructure (Kubernetes, Terraform, AWS, Azure, GCP)
   - Databases (PostgreSQL, MongoDB, Snowflake, etc.)
   - Process tools (Jira, Confluence, ServiceNow, Monday, Notion)
   - Identity systems (Okta, Azure AD, Ping Identity)
   - Monitoring (Datadog, Splunk, New Relic)

3. ANALYZE HIRING PATTERNS
   - Total open roles (more = growth, fewer = stable/decline)
   - Engineering vs. other roles ratio
   - Seniority distribution (senior-heavy = mature org)
   - Team names mentioned (reveals org structure)
   - Remote vs. on-site policy

4. IDENTIFY PROCESS TOOL SIGNALS
   These are especially valuable for Fluency deployment:
   - Confluence = documentation-heavy culture
   - ServiceNow = ITSM integration opportunity
   - Jira = engineering process maturity
   - SharePoint = Microsoft ecosystem
   - Notion = modern documentation

## OUTPUT FORMAT
Return your findings as JSON:
```json
{
  "job_board_sources": ["greenhouse.io", "lever.co"],
  "total_open_roles": 45,
  "engineering_roles": 20,
  "hiring_velocity": "HIGH" | "MEDIUM" | "LOW",
  "technologies_mentioned": ["Python", "Kubernetes", "AWS", "PostgreSQL"],
  "tech_stack_signals": {
    "languages": ["Python", "Go", "TypeScript"],
    "infrastructure": ["AWS", "Kubernetes", "Terraform"],
    "databases": ["PostgreSQL", "Redis", "Snowflake"],
    "tools": ["Jira", "Confluence", "Datadog"]
  },
  "process_tools_mentioned": ["Confluence", "Jira", "ServiceNow"],
  "team_growth_areas": ["Engineering", "Product", "Security"],
  "seniority_distribution": {
    "senior": 8,
    "mid": 10,
    "junior": 2
  },
  "remote_policy": "Hybrid",
  "key_findings": [
    {
      "finding": "Heavy investment in platform engineering - 8 open roles",
      "confidence": "HIGH",
      "source": "greenhouse.io",
      "implication": "Likely interested in process automation"
    }
  ]
}
```

## CONFIDENCE GUIDELINES
- HIGH: Direct requirement in job posting
- MEDIUM: Mentioned as "nice to have" or inferred from context
- LOW: Single mention or edge case

Be efficient - fetch provided URLs first. Only search if URLs don't work.

""" + JSON_OUTPUT_RULES


class JobPostingsAgent(BaseAgent):
    """
    Deep intelligence agent that extracts tech stack and hiring signals from job postings.
    """

    @property
    def name(self) -> str:
        return "JobPostings"

    @property
    def system_prompt(self) -> str:
        return JOB_POSTINGS_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search"]

    async def research(self, profile: CompanyProfile) -> JobPostingInsights:
        """
        Research job postings for a company to extract tech stack and hiring intelligence.
        """
        # Build the research prompt with company-specific details
        company_slug = profile.domain.split('.')[0].lower()

        # Build URL bank section if available
        url_bank = profile.url_bank
        url_bank_section = ""
        if url_bank:
            urls = []
            if url_bank.careers_page:
                urls.append(f"- Careers Page: {url_bank.careers_page}")
            if url_bank.job_board_urls:
                for jb_url in url_bank.job_board_urls[:3]:
                    urls.append(f"- Job Board: {jb_url}")

            if urls:
                url_bank_section = f"""
## PRE-DISCOVERED URLs (fetch these FIRST, avoid searching)
{chr(10).join(urls)}

IMPORTANT: Fetch these URLs directly. Only search if these don't have job listings.
"""

        prompt = f"""Research job postings for {profile.name} (domain: {profile.domain}).

Company Context:
- Industry: {profile.industry}
- Type: {profile.company_type.value}
- Size: {profile.employee_count or 'Unknown'}
{url_bank_section}
{"If pre-discovered URLs don't work, try:" if url_bank_section else "Search these sources in order:"}
1. https://{company_slug}.greenhouse.io/jobs
2. https://jobs.lever.co/{company_slug}
3. https://careers.{profile.domain}
4. https://{profile.domain}/careers
{"5. Only search if above URLs don't work" if url_bank_section else "5. Web search for careers/jobs"}

Extract all technology mentions, hiring patterns, and process tools.
Focus especially on:
- Identity/SSO systems (Fluency integration opportunity)
- Process documentation tools (Confluence, ServiceNow, etc.)
- Engineering team structure and growth

Return comprehensive JSON with your findings."""

        result = await self.run(prompt)

        # Parse the JSON response
        data = result.get("json") or {}

        # Build claims from key findings
        claims = []
        for finding in data.get("key_findings", []):
            claims.append(Claim(
                claim=finding.get("finding", ""),
                category="Hiring",
                confidence=Confidence(finding.get("confidence", "MEDIUM")),
                evidence=[Evidence(
                    url=finding.get("source", profile.domain),
                    quote=finding.get("implication", ""),
                    source_type="job_posting",
                    source_tier=SourceTier.TIER_1
                )] if finding.get("source") else []
            ))

        return JobPostingInsights(
            total_open_roles=data.get("total_open_roles", 0),
            engineering_roles=data.get("engineering_roles", 0),
            technologies_mentioned=data.get("technologies_mentioned", []),
            tech_stack_signals=data.get("tech_stack_signals", {}),
            hiring_velocity=data.get("hiring_velocity", "UNKNOWN"),
            team_growth_areas=data.get("team_growth_areas", []),
            seniority_distribution=data.get("seniority_distribution", {}),
            process_tools_mentioned=data.get("process_tools_mentioned", []),
            remote_policy=data.get("remote_policy"),
            job_board_sources=data.get("job_board_sources", []),
            claims=claims
        )
