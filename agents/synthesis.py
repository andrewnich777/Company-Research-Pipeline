"""
Synthesis Agent - Stage 3 of the research pipeline.

Combines all research into an evidence graph and generates deployment scores.
"""

from .base import BaseAgent
from models import (
    CompanyProfile, ResearchResults, SynthesisOutput,
    EvidenceGraph, DeploymentScore, Claim, Evidence, Confidence, SourceTier
)
from logger import get_logger

logger = get_logger(__name__)


SYNTHESIS_SYSTEM_PROMPT = """Synthesis agent for Fluency AI deployment research.

FLUENCY AI: Enterprise process intelligence platform. Auto-documents workflows, AI analysis, integrates with Confluence/ServiceNow/Jira/SharePoint. Requires SSO (Okta/Azure AD/Ping/OneLogin preferred). SOC 2 Type II, HIPAA-ready, GDPR compliant. AWS deployment (US/EU).

YOUR TASKS:

1. BUILD EVIDENCE GRAPH - Every claim needs source URL + confidence (HIGH/MEDIUM/LOW). Group by: Security, Technology, Strategic, Financial, Hiring, CustomerSentiment, Regulatory, Stakeholder.

2. DETECT CONTRADICTIONS - Flag conflicting info, time-sensitive claims, unresolved conflicts.

3. SCORE DEPLOYMENT READINESS (1-10 scale):

Score each dimension using your judgment based on the evidence collected.
Weight VERIFIED evidence heavily, SOURCED evidence moderately, and
INFERRED evidence lightly. UNKNOWN gaps should lower confidence.

Dimensions to assess:
a) Security Maturity - Trust center presence, certifications, incident history
b) Integration Fit - SSO compatibility, cloud alignment, existing tool overlap
c) Compliance Complexity - Industry regulations, data residency, audit burden
d) Strategic Alignment - AI/automation initiatives, executive buy-in, process focus
e) Deal Complexity - Company size, geography, org structure complexity
f) Champion Identified - Internal advocate presence, influence level
g) Procurement Clarity - Budget cycles, approval process visibility
h) Regulatory Risk - Enforcement history, litigation, breach exposure

For each score, consider the company's specific context. A startup with no
certifications is not the same risk as an enterprise with none. Provide
reasoning in the rationale field explaining your judgment.

4. GENERATE INSIGHTS: Opportunities, blockers, recommended sales approach, discovery questions for gaps.

OUTPUT JSON:
```json
{
  "evidence_graph": {
    "security": [
      {
        "claim": "SOC 2 Type II certified",
        "confidence": "HIGH",
        "source_url": "https://trust.example.com",
        "source_tier": "TIER_0",
        "quote": "We maintain annual SOC 2 Type II certification..."
      }
    ],
    "technology": [...],
    "strategic": [...],
    "financial": [...],
    "hiring": [...],
    "customer_sentiment": [...],
    "regulatory": [...],
    "stakeholder": [...]
  },
  "contradictions": [
    {
      "claim_a": "Company uses AWS",
      "claim_b": "Company uses Azure",
      "resolution": "TIME_RESOLVED" | "UNRESOLVED",
      "note": "Appears to be multi-cloud"
    }
  ],
  "deployment_scores": {
    "security_maturity": 8,
    "integration_fit": 7,
    "compliance_complexity": 5,
    "strategic_alignment": 9,
    "deal_complexity": 6,
    "champion_identified": 7,
    "procurement_clarity": 5,
    "regulatory_risk": 8,
    "overall": 7.2,
    "rationale": "Strong security posture and active AI initiatives offset by complex compliance in healthcare vertical"
  },
  "insights": {
    "opportunities": [
      "Active AI transformation initiative - CEO quoted about efficiency",
      "Already uses Okta - seamless SSO integration possible"
    ],
    "blockers": [
      "HIPAA compliance required - need BAA",
      "Works council approval needed for EU offices"
    ],
    "recommended_approach": "Lead with compliance story - SOC 2 + HIPAA ready",
    "discovery_questions": [
      "What's the timeline for your AI transformation initiative?",
      "How do you currently document processes for compliance audits?"
    ]
  }
}
```

Be thorough in building the evidence graph - every claim needs a source. If a claim has no source, mark it as LOW confidence.
"""


class SynthesisAgent(BaseAgent):
    """
    Stage 3 agent that synthesizes research into actionable intelligence.
    """

    @property
    def name(self) -> str:
        return "Synthesis"

    @property
    def system_prompt(self) -> str:
        return SYNTHESIS_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        # Synthesis is pure reasoning - no tools needed
        return []

    async def synthesize(self, profile: CompanyProfile, research: ResearchResults) -> SynthesisOutput:
        """
        Synthesize all research into evidence graph and deployment scores.

        Returns SynthesisOutput with evidence graph, scores, and insights.
        """
        # Build the research summary for the agent
        research_summary = self._build_research_summary(profile, research)

        # Run the agent
        result = await self.run(research_summary)

        # Parse the JSON response
        data = result.get("json") or {}

        # Build evidence graph
        evidence_graph = self._parse_evidence_graph(data.get("evidence_graph", {}))

        # Build deployment scores
        scores_data = data.get("deployment_scores", {})
        deployment_score = DeploymentScore(
            security_maturity=scores_data.get("security_maturity", 5),
            integration_fit=scores_data.get("integration_fit", 5),
            compliance_complexity=scores_data.get("compliance_complexity", 5),
            strategic_alignment=scores_data.get("strategic_alignment", 5),
            deal_complexity=scores_data.get("deal_complexity", 5),
            champion_identified=scores_data.get("champion_identified", 5),
            procurement_clarity=scores_data.get("procurement_clarity", 5),
            regulatory_risk=scores_data.get("regulatory_risk", 5),
            overall=scores_data.get("overall", 5.0),
            rationale=scores_data.get("rationale", "")
        )

        # Extract insights
        insights_data = data.get("insights", {})

        return SynthesisOutput(
            evidence_graph=evidence_graph,
            contradictions=data.get("contradictions", []),
            deployment_score=deployment_score,
            opportunities=insights_data.get("opportunities", []),
            blockers=insights_data.get("blockers", []),
            recommended_approach=insights_data.get("recommended_approach", ""),
            discovery_questions=insights_data.get("discovery_questions", [])
        )

    def _build_research_summary(self, profile: CompanyProfile, research: ResearchResults) -> str:
        """Build a comprehensive summary of all research for the synthesis agent."""
        summary_parts = []

        # Company Profile
        summary_parts.append(f"""## Company Profile
- Name: {profile.name}
- Domain: {profile.domain}
- Type: {profile.company_type.value}
- Industry: {profile.industry}
- HQ: {profile.hq_location or 'Unknown'}
- Employees: {profile.employee_count or 'Unknown'}
{f'- Ticker: {profile.ticker}' if profile.ticker else ''}
- Description: {profile.description}
""")

        # Security Findings
        if research.security:
            sec = research.security
            certs = [f"  - {c.name} ({c.status})" for c in sec.certifications]
            incidents = [f"  - {c.claim} ({c.confidence.value})" for c in sec.security_incidents]

            summary_parts.append(f"""## Security Findings
- Trust Center: {sec.trust_center_url or 'Not found'}
- Security Maturity: {sec.security_maturity}
- Data Residency: {', '.join(sec.data_residency) if sec.data_residency else 'Unknown'}

Certifications:
{chr(10).join(certs) if certs else '  None found'}

Security Incidents:
{chr(10).join(incidents) if incidents else '  None found'}

Privacy Requirements:
{chr(10).join(f'  - {r}' for r in sec.privacy_requirements) if sec.privacy_requirements else '  None found'}
""")

        # Tech Stack Findings
        if research.tech_stack:
            tech = research.tech_stack
            integrations = [f"  - {i.tool_name} ({i.category}) - {i.confidence.value}" for i in tech.integrations]

            summary_parts.append(f"""## Tech Stack Findings
- Identity Provider: {tech.identity_provider or 'Unknown'}
- Cloud Provider: {tech.cloud_provider or 'Unknown'}

Integrations Found:
{chr(10).join(integrations) if integrations else '  None found'}

Subdomains Found: {len(tech.subdomains_found)}
{chr(10).join(f'  - {s}' for s in tech.subdomains_found[:10]) if tech.subdomains_found else ''}
""")

        # Strategic Findings
        if research.strategic:
            strat = research.strategic
            news = [f"  - {c.claim}" for c in strat.recent_news[:5]]
            ai = [f"  - {c.claim}" for c in strat.ai_initiatives]
            partners = [f"  - {c.claim}" for c in strat.partnerships]
            mna = [f"  - {c.claim}" for c in strat.mna_activity]
            quotes = [f"  - {c.claim}" for c in strat.executive_quotes]

            summary_parts.append(f"""## Strategic Findings

Recent News:
{chr(10).join(news) if news else '  None found'}

AI/Automation Initiatives:
{chr(10).join(ai) if ai else '  None found'}

Partnerships:
{chr(10).join(partners) if partners else '  None found'}

M&A Activity:
{chr(10).join(mna) if mna else '  None found'}

Executive Quotes:
{chr(10).join(quotes) if quotes else '  None found'}
""")

        # Financial Findings (if public company)
        if research.financials:
            fin = research.financials
            risks = [f"  - {r}" for r in fin.risk_factors[:10]]
            geo = [f"  - {g}" for g in fin.geographic_operations]
            regs = [f"  - {r}" for r in fin.regulatory_mentions]

            summary_parts.append(f"""## Financial Findings (SEC Filings)
- CIK: {fin.cik or 'Not found'}
- Recent 10-K: {fin.recent_10k_url or 'Not found'}
- Revenue: {fin.revenue or 'Not disclosed'}

Risk Factors:
{chr(10).join(risks) if risks else '  None extracted'}

Geographic Operations:
{chr(10).join(geo) if geo else '  None found'}

Regulatory Mentions:
{chr(10).join(regs) if regs else '  None found'}
""")

        # ============================================================
        # DEEP INTELLIGENCE FINDINGS
        # ============================================================

        # Job Postings Intelligence
        if research.job_postings:
            jp = research.job_postings
            techs = [f"  - {t}" for t in jp.technologies_mentioned[:15]]
            process_tools = [f"  - {t}" for t in jp.process_tools_mentioned]
            growth = [f"  - {a}" for a in jp.team_growth_areas]

            summary_parts.append(f"""## Job Postings Intelligence (DEEP INTEL)
- Total Open Roles: {jp.total_open_roles}
- Engineering Roles: {jp.engineering_roles}
- Hiring Velocity: {jp.hiring_velocity}
- Remote Policy: {jp.remote_policy or 'Unknown'}

Technologies from Job Requirements:
{chr(10).join(techs) if techs else '  None found'}

Process Tools Mentioned (Integration Opportunities):
{chr(10).join(process_tools) if process_tools else '  None found'}

Team Growth Areas:
{chr(10).join(growth) if growth else '  None found'}

Seniority Distribution: {jp.seniority_distribution if jp.seniority_distribution else 'Unknown'}
""")

        # Customer Reviews Intelligence
        if research.customer_reviews:
            cr = research.customer_reviews
            pain_points = [f"  - {p}" for p in cr.pain_points[:10]]
            integration_issues = [f"  - {i}" for i in cr.integration_challenges[:5]]
            competitors = [f"  - {c.get('competitor', 'Unknown')}: {c.get('context', '')}" for c in cr.competitor_mentions[:5] if isinstance(c, dict)]

            summary_parts.append(f"""## Customer Reviews Intelligence (DEEP INTEL)
- Overall Sentiment: {cr.overall_sentiment}
- Average Rating: {cr.average_rating or 'N/A'}
- Reviews Analyzed: {cr.total_reviews_analyzed}

Customer Pain Points (from negative reviews):
{chr(10).join(pain_points) if pain_points else '  None found'}

Integration Challenges Mentioned:
{chr(10).join(integration_issues) if integration_issues else '  None found'}

Competitor Mentions:
{chr(10).join(competitors) if competitors else '  None found'}

Implementation Signals:
{chr(10).join(f'  - {s}' for s in cr.implementation_signals[:5]) if cr.implementation_signals else '  None found'}
""")

        # Regulatory Risk Intelligence
        if research.regulatory_risk:
            rr = research.regulatory_risk
            enforcement = [f"  - {c.claim}" for c in rr.enforcement_actions[:5]]
            breaches = [f"  - {c.claim}" for c in rr.data_breaches[:5]]
            litigation = [f"  - {c.claim}" for c in rr.active_litigation[:5]]
            exposure = [f"  - {e}" for e in rr.regulatory_exposure]

            summary_parts.append(f"""## Regulatory Risk Intelligence (DEEP INTEL)
- Risk Level: {rr.risk_level}

Enforcement Actions:
{chr(10).join(enforcement) if enforcement else '  None found'}

Data Breach History:
{chr(10).join(breaches) if breaches else '  None found'}

Active Litigation:
{chr(10).join(litigation) if litigation else '  None found'}

Regulatory Exposure (industries/regulations):
{chr(10).join(exposure) if exposure else '  Standard compliance only'}
""")

        # Stakeholder Intelligence
        if research.stakeholders:
            sh = research.stakeholders
            leaders = [f"  - {s.name}, {s.title}" + (f" ({s.background[:50]}...)" if s.background else "") for s in sh.technical_leaders[:5]]
            champions = [f"  - {s.name}, {s.title}" + (f" - Signals: {', '.join(s.champion_signals[:2])}" if s.champion_signals else "") for s in sh.potential_champions[:5]]
            org_signals = [f"  - {s}" for s in sh.org_structure_signals]

            summary_parts.append(f"""## Stakeholder Intelligence (DEEP INTEL)
Technical Leaders Found:
{chr(10).join(leaders) if leaders else '  None identified'}

Potential Champions (internal advocates):
{chr(10).join(champions) if champions else '  None identified'}

Organization Structure Signals:
{chr(10).join(org_signals) if org_signals else '  Unknown'}

GitHub Contributors: {', '.join(sh.github_contributors[:10]) if sh.github_contributors else 'None found'}
Conference Speakers: {len(sh.conference_speakers)} found
""")

        return "\n".join(summary_parts)

    def _parse_evidence_graph(self, graph_data: dict) -> EvidenceGraph:
        """Parse evidence graph data into structured format."""
        def parse_claims(items: list, category: str) -> list[Claim]:
            claims = []
            for item in items:
                confidence = Confidence.MEDIUM
                try:
                    confidence = Confidence(item.get("confidence", "MEDIUM"))
                except ValueError:
                    logger.debug(f"Invalid confidence value '{item.get('confidence')}' in {category} claim, defaulting to MEDIUM")

                source_tier = SourceTier.TIER_2
                try:
                    source_tier = SourceTier(item.get("source_tier", "TIER_2"))
                except ValueError:
                    logger.debug(f"Invalid source tier '{item.get('source_tier')}' in {category} claim, defaulting to TIER_2")

                evidence = []
                if item.get("source_url"):
                    evidence.append(Evidence(
                        url=item["source_url"],
                        quote=item.get("quote", ""),
                        source_type="synthesis",
                        source_tier=source_tier
                    ))

                claims.append(Claim(
                    claim=item.get("claim", ""),
                    category=category,
                    confidence=confidence,
                    evidence=evidence
                ))
            return claims

        return EvidenceGraph(
            security_claims=parse_claims(graph_data.get("security", []), "Security"),
            technology_claims=parse_claims(graph_data.get("technology", []), "Technology"),
            strategic_claims=parse_claims(graph_data.get("strategic", []), "Strategic"),
            financial_claims=parse_claims(graph_data.get("financial", []), "Financial"),
            # Deep intelligence claims
            hiring_claims=parse_claims(graph_data.get("hiring", []), "Hiring"),
            customer_sentiment_claims=parse_claims(graph_data.get("customer_sentiment", []), "CustomerSentiment"),
            regulatory_claims=parse_claims(graph_data.get("regulatory", []), "Regulatory"),
            stakeholder_claims=parse_claims(graph_data.get("stakeholder", []), "Stakeholder")
        )
