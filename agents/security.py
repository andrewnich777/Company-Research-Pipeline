"""
Security Research Agent - Stage 2 of the research pipeline.

Researches security posture, certifications, trust centers, and compliance.
"""

from .base import BaseAgent, URL_BANK_INSTRUCTIONS, JSON_OUTPUT_RULES, build_url_bank_section
from models import CompanyProfile, SecurityFindings, Certification, Claim, Evidence, Confidence, SourceTier
from logger import get_logger

logger = get_logger(__name__)


SECURITY_SYSTEM_PROMPT = """You are a security posture research agent for Fluency AI deployment preparation.

""" + URL_BANK_INSTRUCTIONS + """

Given a company profile, you must:

1. CHECK FOR TRUST CENTER - First check any trust_center or security_page URL provided.
   If not provided, try these common URLs:
   - https://trust.{domain}
   - https://security.{domain}
   - https://{domain}/trust
   - https://{domain}/security

2. FIND CERTIFICATIONS - Look for mentions of:
   - SOC 2 Type I/II
   - ISO 27001
   - HIPAA (healthcare)
   - FedRAMP (government)
   - GDPR compliance
   - PCI DSS (payments)

3. DATA RESIDENCY - Where is data stored?
   - US, EU, APAC regions
   - Specific cloud providers (AWS, Azure, GCP)

4. SECURITY INCIDENTS - Check any regulatory_mentions URLs provided first.
   Only web_search for "{company_name} data breach" if no URLs provided and you need this info.

5. PRIVACY REQUIREMENTS - Fetch the privacy_policy URL if provided.

For each finding, record:
- The source URL
- A specific quote or excerpt
- Confidence level: HIGH (official source), MEDIUM (news/third-party), LOW (inferred)

Return your findings as JSON:
```json
{
  "trust_center_url": "https://trust.example.com" or null,
  "certifications": [
    {
      "name": "SOC 2 Type II",
      "status": "certified",
      "source_url": "https://...",
      "quote": "We maintain SOC 2 Type II certification..."
    }
  ],
  "data_residency": ["US", "EU"],
  "security_incidents": [
    {
      "claim": "No public security incidents found",
      "confidence": "MEDIUM",
      "source_url": "search results"
    }
  ],
  "privacy_requirements": ["GDPR compliant", "Privacy policy mentions employee data"],
  "security_maturity": "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN",
  "maturity_rationale": "Why you assigned this maturity level"
}
```

Be thorough but efficient - fetch provided URLs first, then check additional trust center locations only if needed.

""" + JSON_OUTPUT_RULES


class SecurityAgent(BaseAgent):
    """
    Stage 2 agent that researches security posture and compliance.
    """

    @property
    def name(self) -> str:
        return "Security"

    @property
    def system_prompt(self) -> str:
        return SECURITY_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search"]

    async def research(self, profile: CompanyProfile) -> SecurityFindings:
        """
        Research security posture for a company.

        Returns SecurityFindings with certifications, trust center info, etc.
        """
        # Build URL bank section using shared helper
        url_bank_section = build_url_bank_section(
            profile.url_bank,
            relevant_fields=["trust_center", "security_page", "privacy_policy", "compliance_page", "regulatory_mentions"]
        )

        # Build the research prompt
        prompt = f"""Research the security posture of {profile.name}.

Company Details:
- Domain: {profile.domain}
- Type: {profile.company_type.value}
- Industry: {profile.industry}
{"- Ticker: " + profile.ticker if profile.ticker else ""}
{url_bank_section}
IMPORTANT: Fetch ALL pre-discovered URLs above BEFORE using web_search.
{self.search_context}"""

        # Run the agent
        result = await self.run(prompt)

        # Parse the JSON response
        data = result.get("json") or {}

        # Build certifications list
        certifications = []
        for cert_data in data.get("certifications", []):
            evidence = None
            if cert_data.get("source_url"):
                evidence = Evidence(
                    url=cert_data["source_url"],
                    quote=cert_data.get("quote", ""),
                    source_type="trust_center",
                    source_tier=SourceTier.TIER_0
                )
            certifications.append(Certification(
                name=cert_data.get("name", "Unknown"),
                status=cert_data.get("status", "claimed"),
                evidence=evidence
            ))

        # Build claims from security incidents
        claims = []
        for incident in data.get("security_incidents", []):
            confidence = Confidence.MEDIUM
            try:
                confidence = Confidence(incident.get("confidence", "MEDIUM"))
            except ValueError as e:
                logger.debug(f"Invalid confidence value '{incident.get('confidence')}', defaulting to MEDIUM")

            claims.append(Claim(
                claim=incident.get("claim", ""),
                category="Security Incident",
                confidence=confidence,
                evidence=[Evidence(
                    url=incident.get("source_url", ""),
                    quote=incident.get("claim", ""),
                    source_type="search",
                    source_tier=SourceTier.TIER_1
                )] if incident.get("source_url") else []
            ))

        return SecurityFindings(
            trust_center_url=data.get("trust_center_url"),
            certifications=certifications,
            data_residency=data.get("data_residency", []),
            security_incidents=claims,
            privacy_requirements=data.get("privacy_requirements", []),
            security_maturity=data.get("security_maturity", "UNKNOWN"),
            claims=claims
        )
