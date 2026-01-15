"""
LinkedIn Intelligence Agent - Extracts company insights from LinkedIn presence.

This agent mines LinkedIn for strategic intelligence:
- Executive profiles and recent content
- Company page posts and announcements
- Thought leadership topics (what executives care about)
- Strategic initiatives and transformations
- Culture signals (values, work model)
"""

from .base import BaseAgent
from models import (
    CompanyProfile, LinkedInIntelligence, Claim, Evidence,
    Confidence, SourceTier
)


LINKEDIN_SYSTEM_PROMPT = """You are a LinkedIn intelligence agent for Fluency AI deployment research.

Your goal is to extract STRATEGIC SIGNALS from LinkedIn - the kind of real-time insight into what company leadership actually cares about.

## WHY THIS MATTERS
- LinkedIn posts reveal real-time strategic priorities (not PR-crafted messaging)
- Executive content shows what leadership actually thinks about
- Hiring announcements signal budget health and timing windows
- Thought leadership topics indicate potential champion alignment
- Culture signals reveal organizational readiness

## YOUR RESEARCH PROCESS

1. FIND COMPANY LINKEDIN PRESENCE
   - Search: "{company_name} linkedin company page"
   - Search: "site:linkedin.com/company/{company_slug}"
   - Note follower count if visible (credibility signal)

2. IDENTIFY KEY EXECUTIVES
   Search for these roles specifically:
   - CEO, CTO, VP Engineering, VP Product, VP Operations
   - Search: "{exec_name} {company_name} linkedin"
   - Search: "site:linkedin.com/in {company_name} CTO"

3. ANALYZE RECENT POSTS (focus on last 3-6 months)
   - Search: "site:linkedin.com/posts {company_name}"
   - Search: "{company_name} linkedin announcement"
   - Search: "{CEO_name} linkedin post"
   - Look for: announcements, initiatives, challenges discussed

4. EXTRACT STRATEGIC SIGNALS
   - Hiring announcements in posts → growth areas, budget signals
   - Technology mentions → current priorities
   - Challenges discussed → pain points (sales opportunities!)
   - Partnerships announced → ecosystem plays
   - Conference speaking → thought leadership topics

5. IDENTIFY CULTURE SIGNALS
   - Remote/hybrid/in-office mentions
   - Values statements
   - Diversity initiatives
   - Work-life balance messaging

## OUTPUT FORMAT
Return your findings as JSON:
```json
{
  "company_linkedin_url": "https://linkedin.com/company/acme",
  "follower_count": 15000,
  "executives_found": [
    {
      "name": "Jane Smith",
      "title": "CEO",
      "linkedin_url": "https://linkedin.com/in/janesmith",
      "recent_topics": ["AI transformation", "scaling engineering teams"]
    }
  ],
  "posts_analyzed": 8,
  "recent_post_themes": ["AI investment", "team growth", "product launch"],
  "strategic_initiatives": [
    "Announced AI transformation initiative in Q3",
    "Expanding engineering team by 50%"
  ],
  "hiring_announcements": [
    "Posted about hiring 20 engineers",
    "VP Engineering hiring spree for platform team"
  ],
  "thought_leadership_topics": [
    "Process automation",
    "Engineering productivity",
    "Documentation at scale"
  ],
  "culture_signals": [
    "Hybrid work model emphasized",
    "Strong diversity messaging",
    "Engineering-first culture"
  ],
  "key_findings": [
    {
      "finding": "CEO has posted 3x about 'documentation challenges' in past 2 months",
      "confidence": "HIGH",
      "source": "linkedin.com/in/janesmith",
      "implication": "Clear pain point - Fluency directly addresses this"
    },
    {
      "finding": "Company announced 'operational excellence initiative' last month",
      "confidence": "MEDIUM",
      "source": "linkedin.com/company/acme",
      "implication": "Timing is good - they're actively looking at process tools"
    }
  ]
}
```

## CONFIDENCE GUIDELINES
- HIGH: Direct quote from executive, clear announcement
- MEDIUM: Mentioned in posts, visible from company page
- LOW: Inferred from partial information, single mention

## IMPORTANT NOTES
- LinkedIn may block direct page access - use web_search to find indexed content
- Focus on ACTIONABLE intelligence - things a salesperson can reference in outreach
- Executive thought leadership topics are gold - they show what leaders care about
"""


class LinkedInIntelAgent(BaseAgent):
    """
    Deep intelligence agent that extracts strategic signals from LinkedIn presence.
    """

    @property
    def name(self) -> str:
        return "LinkedInIntel"

    @property
    def system_prompt(self) -> str:
        return LINKEDIN_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search"]

    async def research(self, profile: CompanyProfile) -> LinkedInIntelligence:
        """
        Research LinkedIn presence for strategic intelligence.
        """
        company_slug = profile.domain.split('.')[0].lower()

        prompt = f"""Research LinkedIn presence for {profile.name} (domain: {profile.domain}).

Company Context:
- Industry: {profile.industry}
- Type: {profile.company_type.value}
- Size: {profile.employee_count or 'Unknown'}

Your research priorities:
1. Find the company LinkedIn page and note follower count
2. Identify CEO, CTO, and VP Engineering by name
3. Search for recent posts from company and executives
4. Extract thought leadership topics - what do executives post about?
5. Find any announcements about initiatives, hiring, or transformations

Search queries to use:
- "{profile.name} linkedin company page"
- "{profile.name} CEO linkedin"
- "{profile.name} CTO linkedin"
- "site:linkedin.com/posts {profile.name}"
- "{profile.name} linkedin announcement 2024"

Focus on finding ACTIONABLE intelligence:
- What does leadership care about? (topics they post about)
- Any announced initiatives or transformations?
- Pain points they've mentioned publicly?
- Hiring signals from posts?

Return comprehensive JSON with your findings."""

        result = await self.run(prompt)

        # Parse the JSON response
        data = result.get("json") or {}

        # Build claims from key findings
        claims = []
        for finding in data.get("key_findings", []):
            claims.append(Claim(
                claim=finding.get("finding", ""),
                category="LinkedIn",
                confidence=Confidence(finding.get("confidence", "MEDIUM")),
                evidence=[Evidence(
                    url=finding.get("source", "linkedin.com"),
                    quote=finding.get("implication", ""),
                    source_type="linkedin_post",
                    source_tier=SourceTier.TIER_1
                )] if finding.get("source") else []
            ))

        return LinkedInIntelligence(
            company_linkedin_url=data.get("company_linkedin_url"),
            follower_count=data.get("follower_count"),
            executives_found=data.get("executives_found", []),
            posts_analyzed=data.get("posts_analyzed", 0),
            recent_post_themes=data.get("recent_post_themes", []),
            strategic_initiatives=data.get("strategic_initiatives", []),
            hiring_announcements=data.get("hiring_announcements", []),
            thought_leadership_topics=data.get("thought_leadership_topics", []),
            culture_signals=data.get("culture_signals", []),
            claims=claims
        )
