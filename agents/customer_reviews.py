"""
Customer Reviews Agent - Extracts real pain points and competitor intel from G2/Capterra.

This agent mines customer reviews to understand:
- Real product pain points (not marketing claims)
- Integration challenges users actually face
- Competitor comparisons and switching patterns
- Implementation complexity signals
"""

from .base import BaseAgent, URL_BANK_INSTRUCTIONS, JSON_OUTPUT_RULES, build_url_bank_section
from models import (
    CompanyProfile, CustomerReviewInsights, Claim, Evidence,
    Confidence, SourceTier
)


CUSTOMER_REVIEWS_SYSTEM_PROMPT = """You are a customer intelligence agent for Fluency AI deployment research.

Your goal is to extract REAL customer perspectives from review platforms.

""" + URL_BANK_INSTRUCTIONS + """

## WHY THIS MATTERS
- Reviews reveal actual pain points (opportunity areas for Fluency)
- Integration challenges mentioned = deployment complexity signals
- Competitor mentions reveal what else they're evaluating
- Implementation timelines indicate sales cycle expectations

## YOUR RESEARCH PROCESS

1. CHECK PRE-DISCOVERED URLs FIRST
   If G2, Capterra, or Glassdoor URLs are provided, fetch them directly.
   Only search if URLs are not provided or don't work.

2. EXTRACT PAIN POINTS
   From negative reviews, identify:
   - Product complaints and frustrations
   - Missing features users want
   - Performance or reliability issues
   - Support quality problems
   - Pricing concerns

3. IDENTIFY INTEGRATION SIGNALS
   Look for mentions of:
   - SSO/authentication difficulties
   - API quality (good or bad)
   - Data migration challenges
   - Integration with other tools
   - Implementation complexity

4. CAPTURE COMPETITIVE INTELLIGENCE
   - What competitors are mentioned?
   - Why did users switch TO this product?
   - Why might users switch AWAY?
   - What alternatives are being considered?

5. ASSESS IMPLEMENTATION SIGNALS
   - Time-to-value mentions
   - Onboarding experience
   - Training requirements
   - Professional services needs

## OUTPUT FORMAT
Return your findings as JSON:
```json
{
  "review_sources": ["g2.com", "capterra.com"],
  "total_reviews_analyzed": 25,
  "overall_sentiment": "POSITIVE" | "MIXED" | "NEGATIVE",
  "average_rating": 4.2,
  "pain_points": [
    "Complex onboarding process takes weeks",
    "API documentation is outdated",
    "SSO setup requires dedicated support"
  ],
  "integration_challenges": [
    "Salesforce integration has sync delays",
    "SAML setup requires professional services"
  ],
  "competitor_mentions": [
    {
      "competitor": "ServiceNow",
      "context": "Switched from ServiceNow due to cost"
    },
    {
      "competitor": "Monday.com",
      "context": "Evaluating Monday.com as alternative"
    }
  ],
  "implementation_signals": [
    "Average implementation takes 3-6 months",
    "Requires dedicated admin for maintenance",
    "Professional services recommended for enterprise"
  ],
  "positive_themes": [
    "Strong security features",
    "Good customer support",
    "Comprehensive reporting"
  ],
  "key_findings": [
    {
      "finding": "Multiple reviewers mention long SSO implementation",
      "confidence": "HIGH",
      "source": "g2.com",
      "implication": "May have complex IT procurement process"
    }
  ]
}
```

## IMPORTANT NOTES
- Focus on RECENT reviews (last 1-2 years)
- Weight enterprise user reviews more heavily
- Note patterns across multiple reviews (not one-off complaints)
- Distinguish between product reviews and company reviews

## CONFIDENCE GUIDELINES
- HIGH: Pattern across 3+ reviews
- MEDIUM: Mentioned in 2 reviews or single detailed review
- LOW: Single brief mention

""" + JSON_OUTPUT_RULES


class CustomerReviewsAgent(BaseAgent):
    """
    Deep intelligence agent that extracts customer sentiment and pain points from reviews.
    """

    @property
    def name(self) -> str:
        return "CustomerReviews"

    @property
    def system_prompt(self) -> str:
        return CUSTOMER_REVIEWS_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search"]

    async def research(self, profile: CompanyProfile) -> CustomerReviewInsights:
        """
        Research customer reviews for a company to extract pain points and sentiment.
        """
        # Build URL bank section if available
        url_bank = profile.url_bank
        url_bank_section = ""
        if url_bank:
            urls = []
            if url_bank.g2_page:
                urls.append(f"- G2 Reviews: {url_bank.g2_page}")
            if url_bank.capterra_page:
                urls.append(f"- Capterra Reviews: {url_bank.capterra_page}")
            if url_bank.glassdoor_page:
                urls.append(f"- Glassdoor: {url_bank.glassdoor_page}")

            if urls:
                url_bank_section = f"""
## PRE-DISCOVERED URLs (fetch these FIRST, avoid searching)
{chr(10).join(urls)}

IMPORTANT: Fetch these URLs directly. Only search if these don't provide enough information.
"""

        prompt = f"""Research customer reviews for {profile.name} (domain: {profile.domain}).

Company Context:
- Industry: {profile.industry}
- Type: {profile.company_type.value}
- Description: {profile.description[:200] if profile.description else 'Unknown'}
{url_bank_section}
{"If no pre-discovered URLs above, search these sources:" if not url_bank_section else "If pre-discovered URLs don't work or need more data, search:"}
1. "{profile.name} reviews site:g2.com"
2. "{profile.name} reviews site:capterra.com"
3. "{profile.name} reviews site:trustradius.com"

Focus on:
- Pain points and frustrations users mention
- Integration and implementation challenges
- Competitors they compare to or switched from
- Enterprise customer experiences specifically

This is for a B2B sales context - we want to understand:
1. What problems might this company have that Fluency could solve?
2. How complex is their IT/vendor evaluation process?
3. What competitors are they likely evaluating?

Return comprehensive JSON with your findings."""

        result = await self.run(prompt)

        # Parse the JSON response
        data = result.get("json") or {}

        # Build claims from key findings
        claims = []
        for finding in data.get("key_findings", []):
            confidence_val = finding.get("confidence", "MEDIUM")
            try:
                confidence = Confidence(confidence_val)
            except ValueError:
                confidence = Confidence.MEDIUM

            claims.append(Claim(
                claim=finding.get("finding", ""),
                category="Customer Sentiment",
                confidence=confidence,
                evidence=[Evidence(
                    url=finding.get("source", "review site"),
                    quote=finding.get("implication", ""),
                    source_type="customer_review",
                    source_tier=SourceTier.TIER_1
                )] if finding.get("source") else []
            ))

        return CustomerReviewInsights(
            overall_sentiment=data.get("overall_sentiment", "UNKNOWN"),
            average_rating=data.get("average_rating"),
            total_reviews_analyzed=data.get("total_reviews_analyzed", 0),
            pain_points=data.get("pain_points", []),
            integration_challenges=data.get("integration_challenges", []),
            competitor_mentions=data.get("competitor_mentions", []),
            implementation_signals=data.get("implementation_signals", []),
            positive_themes=data.get("positive_themes", []),
            review_sources=data.get("review_sources", []),
            claims=claims
        )
