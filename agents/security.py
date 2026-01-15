"""
Security Research Agent - Stage 2 of the research pipeline.

Researches security posture, certifications, trust centers, and compliance.
"""

from .base import BaseAgent
from models import CompanyProfile, SecurityFindings, Certification, Claim, Evidence, Confidence, SourceTier


SECURITY_SYSTEM_PROMPT = """You are a security posture research agent for Fluency AI deployment preparation.

Your task is to research a company's security and compliance posture to help prepare for deployment discussions.

Given a company profile, you must:

1. CHECK FOR TRUST CENTER - Look for security/trust pages at these common URLs:
   - https://trust.{domain}
   - https://security.{domain}
   - https://{domain}/trust
   - https://{domain}/security
   - https://{domain}/compliance
   - https://{domain}/.well-known/security.txt

2. FIND CERTIFICATIONS - Look for mentions of:
   - SOC 2 Type I/II
   - ISO 27001
   - HIPAA (healthcare)
   - FedRAMP (government)
   - GDPR compliance
   - PCI DSS (payments)
   - Other industry-specific certifications

3. DATA RESIDENCY - Where is data stored?
   - US, EU, APAC regions
   - Specific cloud providers (AWS, Azure, GCP)
   - Data localization requirements

4. SECURITY INCIDENTS - Search for any historical security incidents or breaches
   - Use web_search to look for "{company_name} data breach" or "{company_name} security incident"

5. PRIVACY REQUIREMENTS - Look for:
   - Privacy policy details
   - Employee monitoring policies (relevant for Fluency)
   - Works council requirements (EU)

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

Be thorough - check multiple potential trust center URLs. A company with a comprehensive trust center indicates HIGH security maturity.
"""


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
        # Build the research prompt
        prompt = f"""Research the security posture of {profile.name}.

Company Details:
- Domain: {profile.domain}
- Type: {profile.company_type.value}
- Industry: {profile.industry}
{"- Ticker: " + profile.ticker if profile.ticker else ""}

Start by checking for a trust center, then look for certifications and compliance information.
"""

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
            except ValueError:
                pass

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
