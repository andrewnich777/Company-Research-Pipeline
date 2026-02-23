"""
Executive Brief Agent - Opus-powered deal intelligence synthesis.

This agent uses Claude Opus to generate high-value insights that require
multi-factor reasoning across all research data:
1. Wow Findings - Non-obvious, deal-winning intelligence
2. Strategic Insights - Cross-referenced patterns with actions
3. Risk Assessment - Nuanced evaluation of deal risks
4. Recommended Approach - Context-aware sales strategy
"""

from .base import BaseAgent
from models import CompanyProfile, SynthesisOutput, ResearchResults
from logger import get_logger

logger = get_logger(__name__)


EXECUTIVE_BRIEF_SYSTEM_PROMPT = """You are an elite deal intelligence analyst for Fluency AI, an enterprise process intelligence platform.

Your task is to synthesize research data into ACTIONABLE deal intelligence that helps sales teams win.

## WHAT MAKES GREAT DEAL INTELLIGENCE

1. **Wow Findings** - Insights you can't get from 5 minutes on Google:
   - Hidden champions (people who can sell internally)
   - Budget signals (hiring velocity, growth patterns)
   - Pain confirmation (validated from multiple sources)
   - Timing windows (budget cycles, initiatives)
   - Non-obvious connections between data points

2. **Strategic Insights** - Cross-referenced patterns:
   - Champion + Pain + Timing alignment = perfect entry point
   - Tech stack + Process tools = integration story
   - Executive priorities + Customer pain = messaging alignment
   - Culture signals + Tech maturity = fit assessment

3. **Risk Assessment** - Nuanced evaluation:
   - Not all risks are equal - prioritize deal-killing vs manageable
   - Context matters: startup with no certs ≠ enterprise with none
   - Historical issues may be resolved - check recency

4. **Recommended Approach** - Specific, actionable strategy:
   - Who to contact first and why
   - What to lead with in outreach
   - What to prepare before first meeting
   - Timeline recommendations

## WHAT TO AVOID

- Generic insights that could apply to any company
- Obvious observations (e.g., "they use technology")
- Unactionable findings (insight without action)
- Overly cautious hedging that waters down recommendations

## OUTPUT FORMAT

Return JSON with these sections:
```json
{
  "wow_findings": [
    {
      "category": "Hidden Champion|Budget Signal|Pain Confirmed|Timing Window|Tech Insight|Competitive Intel",
      "finding": "Specific finding with evidence",
      "source": "Where this came from",
      "confidence": "HIGH|MEDIUM|LOW",
      "action": "Specific action the sales rep should take"
    }
  ],
  "strategic_insights": [
    {
      "pattern": "What cross-referenced data points reveal",
      "data_sources": ["source1", "source2"],
      "implication": "What this means for the deal",
      "action": "Specific recommended action"
    }
  ],
  "risk_assessment": {
    "deal_killers": ["Critical risks that could block the deal"],
    "manageable_risks": ["Risks that can be addressed with preparation"],
    "risk_summary": "Overall risk posture in one sentence"
  },
  "recommended_approach": {
    "primary_contact": "Who to reach out to first and why",
    "opening_message": "What to lead with in outreach",
    "demo_focus": "What to emphasize in demos",
    "timeline": "Recommended deal timeline",
    "preparation": ["Things to prepare before first meeting"]
  },
  "discovery_questions": [
    "Questions to ask to fill intelligence gaps"
  ]
}
```

Be specific. Be actionable. Find the non-obvious.
"""


class ExecutiveBriefAgent(BaseAgent):
    """
    Opus-powered agent that generates high-value deal intelligence.

    This agent excels at:
    - Finding non-obvious patterns across data sources
    - Making nuanced judgment calls about deal dynamics
    - Generating actionable, specific recommendations
    """

    @property
    def name(self) -> str:
        return "ExecutiveBrief"

    @property
    def system_prompt(self) -> str:
        return EXECUTIVE_BRIEF_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        # Pure reasoning - no tools needed
        return []

    async def generate_intelligence(
        self,
        profile: CompanyProfile,
        synthesis: SynthesisOutput,
        research: ResearchResults
    ) -> dict:
        """
        Generate deal intelligence using Opus-level reasoning.

        Returns structured intelligence for the executive brief.
        """
        # Build comprehensive research summary for the agent
        research_summary = self._build_research_summary(profile, synthesis, research)

        # Run the agent
        result = await self.run(research_summary)

        # Parse the JSON response
        data = result.get("json") or {}

        # Log stats
        wow_count = len(data.get("wow_findings", []))
        insight_count = len(data.get("strategic_insights", []))
        logger.info(f"[ExecutiveBrief] Generated {wow_count} wow findings, {insight_count} strategic insights")

        return {
            "wow_findings": data.get("wow_findings", []),
            "strategic_insights": data.get("strategic_insights", []),
            "risk_assessment": data.get("risk_assessment", {}),
            "recommended_approach": data.get("recommended_approach", {}),
            "discovery_questions": data.get("discovery_questions", []),
        }

    def _build_research_summary(
        self,
        profile: CompanyProfile,
        synthesis: SynthesisOutput,
        research: ResearchResults
    ) -> str:
        """Build comprehensive summary of all research for Opus to analyze."""
        sections = []

        # Company Profile
        sections.append(f"""## Company Profile
- Name: {profile.name}
- Domain: {profile.domain}
- Type: {profile.company_type.value}
- Industry: {profile.industry}
- Size: {profile.employee_count or 'Unknown'}
- HQ: {profile.hq_location or 'Unknown'}
- Description: {profile.description}
""")

        # Deployment Scores (judgment context)
        score = synthesis.deployment_score
        sections.append(f"""## Deployment Readiness Scores
- Overall: {score.overall}/10
- Security Maturity: {score.security_maturity}/10
- Integration Fit: {score.integration_fit}/10
- Compliance Complexity: {score.compliance_complexity}/10
- Strategic Alignment: {score.strategic_alignment}/10
- Deal Complexity: {score.deal_complexity}/10
- Champion Identified: {score.champion_identified}/10
- Procurement Clarity: {score.procurement_clarity}/10
- Regulatory Risk: {score.regulatory_risk}/10
- Rationale: {score.rationale}
""")

        # Opportunities and Blockers
        if synthesis.opportunities:
            sections.append(f"""## Identified Opportunities
{chr(10).join(f'- {o}' for o in synthesis.opportunities)}
""")

        if synthesis.blockers:
            sections.append(f"""## Identified Blockers
{chr(10).join(f'- {b}' for b in synthesis.blockers)}
""")

        # Stakeholder Intelligence
        if research.stakeholders:
            sh = research.stakeholders
            leaders = [f"- {s.name}, {s.title}" + (f" (Champion signals: {', '.join(s.champion_signals[:2])})" if s.champion_signals else "")
                      for s in sh.potential_champions[:5]]
            tech_leaders = [f"- {s.name}, {s.title}" + (f" - {s.background[:50]}..." if s.background else "")
                          for s in sh.technical_leaders[:5]]

            sections.append(f"""## Stakeholder Intelligence
Potential Champions:
{chr(10).join(leaders) if leaders else '  None identified'}

Technical Leaders:
{chr(10).join(tech_leaders) if tech_leaders else '  None identified'}

Org Structure Signals: {', '.join(sh.org_structure_signals) if sh.org_structure_signals else 'Unknown'}
""")

        # LinkedIn Intelligence
        if research.linkedin_intel:
            li = research.linkedin_intel
            execs = []
            for e in li.executives_found[:5]:
                if isinstance(e, dict):
                    topics = e.get("recent_topics", [])
                    execs.append(f"- {e.get('name', 'Unknown')}, {e.get('title', '')} - Topics: {', '.join(topics[:3]) if topics else 'None'}")

            sections.append(f"""## LinkedIn Intelligence
Company Page Followers: {li.follower_count or 'Unknown'}
Executives Found:
{chr(10).join(execs) if execs else '  None'}

Thought Leadership Topics: {', '.join(li.thought_leadership_topics[:5]) if li.thought_leadership_topics else 'None'}
Strategic Initiatives: {', '.join(li.strategic_initiatives[:3]) if li.strategic_initiatives else 'None'}
Hiring Announcements: {', '.join(li.hiring_announcements[:3]) if li.hiring_announcements else 'None'}
Culture Signals: {', '.join(li.culture_signals[:4]) if li.culture_signals else 'None'}
""")

        # Job Postings Intelligence
        if research.job_postings:
            jp = research.job_postings
            tech_stack = []
            if jp.tech_stack_signals:
                for category, techs in jp.tech_stack_signals.items():
                    if techs:
                        tech_stack.append(f"  {category}: {', '.join(techs[:5])}")

            sections.append(f"""## Job Postings Intelligence
Total Open Roles: {jp.total_open_roles}
Engineering Roles: {jp.engineering_roles}
Hiring Velocity: {jp.hiring_velocity}
Remote Policy: {jp.remote_policy or 'Unknown'}

Tech Stack (from job requirements):
{chr(10).join(tech_stack) if tech_stack else '  Not extracted'}

Process Tools Mentioned: {', '.join(jp.process_tools_mentioned) if jp.process_tools_mentioned else 'None'}
Team Growth Areas: {', '.join(jp.team_growth_areas[:5]) if jp.team_growth_areas else 'Unknown'}
""")

        # Customer Reviews Intelligence
        if research.customer_reviews:
            cr = research.customer_reviews
            competitors = []
            for c in cr.competitor_mentions[:5]:
                if isinstance(c, dict):
                    competitors.append(f"- {c.get('competitor', 'Unknown')}: {c.get('context', '')}")

            sections.append(f"""## Customer Reviews Intelligence
Overall Sentiment: {cr.overall_sentiment}
Average Rating: {cr.average_rating or 'N/A'}
Reviews Analyzed: {cr.total_reviews_analyzed}

Pain Points:
{chr(10).join(f'- {p}' for p in cr.pain_points[:5]) if cr.pain_points else '  None identified'}

Integration Challenges:
{chr(10).join(f'- {c}' for c in cr.integration_challenges[:3]) if cr.integration_challenges else '  None identified'}

Competitor Mentions:
{chr(10).join(competitors) if competitors else '  None'}

Implementation Signals: {', '.join(cr.implementation_signals[:3]) if cr.implementation_signals else 'None'}
""")

        # Regulatory Risk
        if research.regulatory_risk:
            rr = research.regulatory_risk
            sections.append(f"""## Regulatory Risk Intelligence
Risk Level: {rr.risk_level}
Regulatory Exposure: {', '.join(rr.regulatory_exposure) if rr.regulatory_exposure else 'Standard'}

Enforcement Actions:
{chr(10).join(f'- {a.claim}' for a in rr.enforcement_actions[:3]) if rr.enforcement_actions else '  None found'}

Data Breaches:
{chr(10).join(f'- {b.claim}' for b in rr.data_breaches[:3]) if rr.data_breaches else '  None found'}

Active Litigation:
{chr(10).join(f'- {l.claim}' for l in rr.active_litigation[:3]) if rr.active_litigation else '  None found'}
""")

        # Security Findings
        if research.security:
            sec = research.security
            certs = [f"- {c.name} ({c.status})" for c in sec.certifications[:5]]

            sections.append(f"""## Security Posture
Trust Center: {sec.trust_center_url or 'Not found'}
Security Maturity: {sec.security_maturity}
Data Residency: {', '.join(sec.data_residency) if sec.data_residency else 'Unknown'}

Certifications:
{chr(10).join(certs) if certs else '  None found'}
""")

        # Procurement Intelligence
        if research.procurement:
            proc = research.procurement
            sections.append(f"""## Procurement Intelligence
Complexity: {proc.procurement_complexity}
Estimated Timeline: {proc.estimated_approval_timeline}
Fiscal Year End: {proc.fiscal_year_end or 'Unknown'}
Budget Planning Cycle: {proc.budget_planning_cycle or 'Unknown'}
Procurement Platform: {proc.procurement_platform or 'Unknown'}
Timing Recommendation: {proc.timing_recommendation or 'None'}
""")

        # Implementation Risk
        if research.implementation_risk:
            ir = research.implementation_risk
            sections.append(f"""## Implementation Risk Assessment
Risk Level: {ir.risk_level}
Integration Complexity: {ir.integration_complexity}
Recommended Approach: {ir.recommended_approach}

Tech Debt Signals: {', '.join(ir.tech_debt_signals[:3]) if ir.tech_debt_signals else 'None'}
Change Management Concerns: {', '.join(ir.change_management_concerns[:3]) if ir.change_management_concerns else 'None'}

Success Factors:
{chr(10).join(f'- {f}' for f in ir.success_factors[:4]) if ir.success_factors else '  Not identified'}

Risk Mitigations:
{chr(10).join(f'- {m}' for m in ir.risk_mitigations[:4]) if ir.risk_mitigations else '  Not identified'}
""")

        # Operational Culture
        if research.operational_culture:
            oc = research.operational_culture
            sections.append(f"""## Operational Culture
Culture Type: {oc.culture_type}
Reliability Priority: {oc.reliability_priority}
Velocity Priority: {oc.velocity_priority}
Deployment Approach: {oc.deployment_approach}
Methodology Signals: {', '.join(oc.methodology_signals[:4]) if oc.methodology_signals else 'None'}
Positioning Recommendation: {oc.positioning_recommendation or 'None'}
Keywords to Use: {', '.join(oc.keywords_to_use[:5]) if oc.keywords_to_use else 'None'}
Keywords to Avoid: {', '.join(oc.keywords_to_avoid[:5]) if oc.keywords_to_avoid else 'None'}
""")

        # Strategic Findings
        if research.strategic:
            strat = research.strategic
            sections.append(f"""## Strategic Context
Recent News:
{chr(10).join(f'- {n.claim}' for n in strat.recent_news[:5]) if strat.recent_news else '  None found'}

AI/Automation Initiatives:
{chr(10).join(f'- {a.claim}' for a in strat.ai_initiatives[:3]) if strat.ai_initiatives else '  None found'}

Partnerships:
{chr(10).join(f'- {p.claim}' for p in strat.partnerships[:3]) if strat.partnerships else '  None found'}

Executive Quotes:
{chr(10).join(f'- {q.claim}' for q in strat.executive_quotes[:3]) if strat.executive_quotes else '  None found'}
""")

        # Final instruction
        sections.append("""## YOUR TASK

Analyze ALL the data above and generate:
1. **Wow Findings** - Non-obvious insights that could win this deal
2. **Strategic Insights** - Patterns from cross-referencing multiple data sources
3. **Risk Assessment** - Nuanced evaluation of deal risks
4. **Recommended Approach** - Specific, actionable sales strategy
5. **Discovery Questions** - Questions to fill intelligence gaps

Look for connections between data points. Find the story the data tells.
Be specific and actionable. Avoid generic insights.

Return your analysis as JSON.
""")

        return "\n".join(sections)
