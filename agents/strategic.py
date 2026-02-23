"""
Strategic Research Agent - Stage 2 of the research pipeline.

Researches recent news, AI initiatives, partnerships, and strategic context.
"""

from .base import BaseAgent, URL_BANK_INSTRUCTIONS, JSON_OUTPUT_RULES, build_url_bank_section
from models import CompanyProfile, StrategicFindings, Claim, Evidence, Confidence, SourceTier


STRATEGIC_SYSTEM_PROMPT = """You are a strategic intelligence research agent for Fluency AI sales preparation.

""" + URL_BANK_INSTRUCTIONS + """

Given a company profile, you must:

1. CHECK PRE-DISCOVERED URLs FIRST - Fetch any news_articles or press_releases provided.

2. RECENT NEWS (only search if needed) - Search for:
   - Press releases
   - Major announcements
   - Leadership changes
   - M&A activity
   - Funding rounds (if startup)

2. AI/AUTOMATION INITIATIVES - Look for:
   - AI strategy announcements
   - Digital transformation initiatives
   - Automation projects
   - Process improvement programs
   - Job postings for AI/ML roles

3. PARTNERSHIPS - Find:
   - Technology partnerships
   - Strategic alliances
   - Vendor relationships
   - Customer case studies they're featured in

4. EXECUTIVE QUOTES - Look for:
   - CEO/CTO quotes about strategy
   - Earnings call mentions of automation/AI
   - Conference presentations
   - LinkedIn posts from executives

For each finding, record:
- The specific claim
- Source URL
- Date (if available)
- Confidence level
- Relevant quote

Return your findings as JSON:
```json
{
  "recent_news": [
    {
      "claim": "Company announced Q4 earnings beat",
      "date": "2024-01-15",
      "source_url": "https://...",
      "quote": "Revenue grew 15% YoY...",
      "confidence": "HIGH"
    }
  ],
  "ai_initiatives": [
    {
      "claim": "Company is investing in AI-driven automation",
      "source_url": "https://...",
      "quote": "CEO said: 'We are committed to...'",
      "confidence": "HIGH"
    }
  ],
  "partnerships": [
    {
      "claim": "Partnership with Microsoft for cloud migration",
      "source_url": "https://...",
      "confidence": "MEDIUM"
    }
  ],
  "mna_activity": [
    {
      "claim": "Acquired XYZ company for $100M",
      "date": "2024-02-01",
      "source_url": "https://..."
    }
  ],
  "executive_quotes": [
    {
      "executive": "Jane Doe, CEO",
      "quote": "Our focus for 2024 is operational efficiency...",
      "source_url": "https://...",
      "context": "Q4 2023 Earnings Call"
    }
  ]
}
```

Focus on findings relevant to Fluency AI's value proposition:
- Process documentation
- Workflow visibility
- AI/automation readiness
- Operational efficiency initiatives

""" + JSON_OUTPUT_RULES


class StrategicAgent(BaseAgent):
    """
    Stage 2 agent that researches strategic context and recent news.
    """

    @property
    def name(self) -> str:
        return "Strategic"

    @property
    def system_prompt(self) -> str:
        return STRATEGIC_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search"]

    async def research(self, profile: CompanyProfile) -> StrategicFindings:
        """
        Research strategic context for a company.

        Returns StrategicFindings with news, AI initiatives, partnerships, etc.
        """
        # Build URL bank section if available
        url_bank = profile.url_bank
        url_bank_section = ""
        if url_bank:
            urls = []
            if url_bank.news_articles:
                for i, news_url in enumerate(url_bank.news_articles[:5]):
                    urls.append(f"- News Article {i+1}: {news_url}")
            if url_bank.press_releases:
                for i, pr_url in enumerate(url_bank.press_releases[:3]):
                    urls.append(f"- Press Release {i+1}: {pr_url}")
            if url_bank.blog_posts:
                for i, blog_url in enumerate(url_bank.blog_posts[:2]):
                    urls.append(f"- Blog Post {i+1}: {blog_url}")

            if urls:
                url_bank_section = f"""
## PRE-DISCOVERED URLs (fetch these FIRST, avoid searching)
{chr(10).join(urls)}

IMPORTANT: Fetch these URLs directly. Only search if these don't provide enough strategic context.
"""

        # Build the research prompt
        prompt = f"""Research the strategic context and recent news for {profile.name}.

Company Details:
- Domain: {profile.domain}
- Type: {profile.company_type.value}
- Industry: {profile.industry}
{"- Ticker: " + profile.ticker if profile.ticker else ""}
{url_bank_section}
Focus on:
1. {"Fetch pre-discovered news URLs above, then" if url_bank_section else ""} Recent news and announcements (last 90 days)
2. AI and automation initiatives
3. Strategic partnerships
4. M&A activity
5. Executive quotes about strategy and operations

{"Only search if pre-discovered URLs don't provide enough information." if url_bank_section else 'Search for news, AI initiatives, etc.'}
"""

        # Run the agent
        result = await self.run(prompt)

        # Parse the JSON response
        data = result.get("json") or {}

        def parse_claims(items: list, category: str) -> list[Claim]:
            claims = []
            for item in items:
                confidence = Confidence.MEDIUM
                try:
                    confidence = Confidence(item.get("confidence", "MEDIUM"))
                except ValueError:
                    pass

                evidence = []
                if item.get("source_url"):
                    evidence.append(Evidence(
                        url=item["source_url"],
                        quote=item.get("quote", item.get("claim", "")),
                        source_type="news",
                        source_tier=SourceTier.TIER_1 if confidence == Confidence.HIGH else SourceTier.TIER_2
                    ))

                claims.append(Claim(
                    claim=item.get("claim", ""),
                    category=category,
                    confidence=confidence,
                    evidence=evidence
                ))
            return claims

        # Parse executive quotes as claims
        exec_claims = []
        for quote_data in data.get("executive_quotes", []):
            exec_claims.append(Claim(
                claim=f"{quote_data.get('executive', 'Executive')}: \"{quote_data.get('quote', '')}\"",
                category="Executive Quote",
                confidence=Confidence.HIGH,
                evidence=[Evidence(
                    url=quote_data.get("source_url", ""),
                    quote=quote_data.get("quote", ""),
                    source_type="executive_quote",
                    source_tier=SourceTier.TIER_0
                )] if quote_data.get("source_url") else []
            ))

        return StrategicFindings(
            recent_news=parse_claims(data.get("recent_news", []), "News"),
            ai_initiatives=parse_claims(data.get("ai_initiatives", []), "AI Initiative"),
            partnerships=parse_claims(data.get("partnerships", []), "Partnership"),
            mna_activity=parse_claims(data.get("mna_activity", []), "M&A"),
            executive_quotes=exec_claims,
            claims=parse_claims(data.get("recent_news", []), "Strategic")
        )
