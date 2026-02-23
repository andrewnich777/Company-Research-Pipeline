"""
Operational Culture Agent - Extracts methodology and process maturity signals.

Software deploys into human processes. This agent identifies whether a company
is SRE-focused, Agile-focused, or ITSM-focused to shape positioning strategy.
"""

from .base import BaseAgent, JSON_OUTPUT_RULES
from models import (
    CompanyProfile, OperationalCultureInsights, Claim, Evidence,
    Confidence, SourceTier
)


OPERATIONAL_CULTURE_SYSTEM_PROMPT = """You are an operational culture intelligence agent for Fluency AI deployment research.

Your goal is to understand HOW a company operates - their methodology and process maturity.

## WHY THIS MATTERS
Software isn't just deployed into a cloud; it's deployed into human processes.
- An SRE-heavy company wants reliability, observability, and audit trails
- An Agile-focused company wants velocity, iteration, and minimal process
- An ITSM-focused company wants change management, CAB approval, and compliance

Understanding this shapes how Fluency should be positioned and sold.

## SIGNALS TO LOOK FOR

### SRE/Reliability Culture
- Job titles: "Site Reliability Engineer", "Platform Engineer", "Infrastructure Engineer"
- Keywords: "SLOs", "SLAs", "uptime", "incident response", "on-call", "observability", "monitoring"
- Tools: Datadog, PagerDuty, OpsGenie, Prometheus, Grafana
- Mentions: "five nines", "MTTR", "error budget", "blameless postmortems"

### Agile/Velocity Culture
- Job titles: "Agile Coach", "Scrum Master", "Product Owner"
- Keywords: "sprint", "velocity", "continuous delivery", "ship fast", "iterate"
- Tools: Jira, Linear, Shortcut, Notion
- Mentions: "move fast", "fail fast", "minimum viable", "rapid iteration"

### ITSM/Enterprise Culture
- Job titles: "Change Manager", "IT Service Manager", "ITSM Analyst"
- Keywords: "ITIL", "change management", "CAB", "change advisory board", "service desk"
- Tools: ServiceNow, BMC Remedy, Cherwell, Ivanti
- Mentions: "change ticket", "approval workflow", "audit", "compliance"

### DevOps Maturity (DORA metrics)
- "DORA metrics", "deployment frequency", "lead time for changes"
- "mean time to recovery", "change failure rate"
- "CI/CD", "trunk-based development", "feature flags"

## YOUR RESEARCH PROCESS

1. Search job postings for methodology signals
2. Look for engineering blog posts about how they work
3. Check for status page (indicates reliability focus)
4. Search LinkedIn for team structure (SRE team? Platform team?)
5. Look for conference talks by their engineers

## OUTPUT FORMAT
```json
{
  "culture_type": "SRE-focused" | "Agile-focused" | "ITSM-focused" | "Hybrid",
  "methodology_signals": ["DORA metrics", "ITIL", "Scrum", "on-call rotation"],
  "reliability_priority": "HIGH" | "MEDIUM" | "LOW",
  "velocity_priority": "HIGH" | "MEDIUM" | "LOW",
  "deployment_approach": "Continuous" | "Scheduled releases" | "CAB-gated" | "Unknown",
  "evidence": [
    {
      "signal": "5 SRE job postings mentioning SLOs and incident response",
      "source": "https://...",
      "confidence": "HIGH"
    }
  ],
  "positioning_recommendation": "Lead with 'Observability & Monitoring' and 'audit trails'. Avoid leading with 'move fast' or 'innovation' - they value stability.",
  "keywords_to_use": ["observability", "reliability", "audit trail", "compliance"],
  "keywords_to_avoid": ["move fast", "disrupt", "rapid iteration"]
}
```

Be specific in your positioning recommendation - this directly shapes the sales conversation.

""" + JSON_OUTPUT_RULES


class OperationalCultureAgent(BaseAgent):
    """
    Agent that identifies operational methodology and process maturity.
    """

    @property
    def name(self) -> str:
        return "OperationalCulture"

    @property
    def system_prompt(self) -> str:
        return OPERATIONAL_CULTURE_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search"]

    async def research(self, profile: CompanyProfile) -> OperationalCultureInsights:
        """
        Research operational culture and methodology signals.
        """
        prompt = f"""Research the operational culture and methodology of {profile.name}.

Company Context:
- Domain: {profile.domain}
- Industry: {profile.industry}
- Type: {profile.company_type.value}
- Size: {profile.employee_count or 'Unknown'}

Research in this order:
1. Search "{profile.name} site reliability engineer jobs" and "{profile.name} SRE"
2. Search "{profile.name} agile coach jobs" and "{profile.name} scrum master"
3. Search "{profile.name} ITIL" and "{profile.name} change management"
4. Check for status page at status.{profile.domain} or {profile.domain}/status
5. Search "{profile.name} engineering blog" for methodology posts
6. Search LinkedIn for "{profile.name} platform team" or "{profile.name} SRE team"

Determine their culture type and provide specific positioning recommendations.
Return comprehensive JSON with your findings."""

        result = await self.run(prompt)
        data = result.get("json") or {}

        # Build claims from evidence
        claims = []
        for item in data.get("evidence", []):
            claims.append(Claim(
                claim=item.get("signal", ""),
                category="Operational Culture",
                confidence=Confidence(item.get("confidence", "MEDIUM")),
                evidence=[Evidence(
                    url=item.get("source", profile.domain),
                    quote="",
                    source_type="job_posting",
                    source_tier=SourceTier.TIER_1
                )] if item.get("source") else []
            ))

        return OperationalCultureInsights(
            culture_type=data.get("culture_type", "Unknown"),
            methodology_signals=data.get("methodology_signals", []),
            reliability_priority=data.get("reliability_priority", "MEDIUM"),
            velocity_priority=data.get("velocity_priority", "MEDIUM"),
            deployment_approach=data.get("deployment_approach", "Unknown"),
            positioning_recommendation=data.get("positioning_recommendation", ""),
            keywords_to_use=data.get("keywords_to_use", []),
            keywords_to_avoid=data.get("keywords_to_avoid", []),
            claims=claims
        )
