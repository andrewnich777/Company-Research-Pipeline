"""
Brief Refiner Agent - Opus-powered audience-aware brief refinement.

This agent generates audience-specific intelligence for Sales, Security, and Product
briefs in a single API call. Each brief receives strategically tailored content
based on what that team needs.
"""

from .base import BaseAgent
from models import CompanyProfile, SynthesisOutput, ResearchResults
from logger import get_logger

logger = get_logger(__name__)


BRIEF_REFINER_SYSTEM_PROMPT = """You are an elite brief strategist for Fluency AI, an enterprise process intelligence platform.

Analyze research data and generate AUDIENCE-SPECIFIC intelligence for three teams.
Strategically select and present information based on who reads each brief.

## AUDIENCE PROFILES

### Sales Brief -> Sales Team
- **Needs:** Talking points, objection handlers, champion signals, deal velocity
- **Tone:** Business-focused, action-oriented
- **Priority:** Pain points, competitive positioning, budget signals
- **Avoid:** Deep technical details, security minutiae

### Security Brief -> CISO/Compliance
- **Needs:** Risk assessment, compliance gaps, certification verification
- **Tone:** Technical, risk-focused, evidence-heavy
- **Priority:** Certifications, incidents, regulatory exposure
- **Avoid:** Sales language, generalized statements

### Product Brief -> Implementation/CSM
- **Needs:** Integration complexity, tech compatibility, deployment roadmap
- **Tone:** Technical but practical, timeline-oriented
- **Priority:** Tech stack signals, implementation challenges
- **Avoid:** Deal dynamics, compliance deep-dives

## STRATEGIC ALLOCATION

For each finding, decide:
1. Which audience(s) need this?
2. How to present it differently for each?
3. What action should each take?

Example: "Company has no SOC 2"
- Sales: "Lead with Fluency's SOC 2 story - they'll need it"
- Security: "No SOC 2 found [U] - verify during review, extended timeline likely"
- Product: "Security approval may extend timeline - factor in"

## EVIDENCE CONFIDENCE

Use these confidence markers where applicable:
- [V] Verified - Found in trust center, SEC filings, or official sources
- [I] Inferred - Derived from multiple signals, reasonable confidence
- [U] Unverified - Single source or could not confirm
- [C] Conflicting - Multiple sources disagree

## OUTPUT FORMAT

Return a JSON object with these exact sections:

```json
{
  "sales_refinements": {
    "talking_points": [
      {
        "topic": "Main subject (e.g., 'Process Automation Pain')",
        "point": "Specific talking point to make",
        "source": "Where this insight came from",
        "objection": "Likely objection you might hear",
        "response": "How to handle the objection"
      }
    ],
    "objection_handlers": [
      {
        "objection": "Specific objection (e.g., 'We already have UiPath')",
        "response": "How to respond",
        "evidence": "Supporting evidence to reference"
      }
    ],
    "champion_engagement": {
      "primary": "Name and title of best champion candidate",
      "why": "Why this person is the right champion",
      "approach": "Specific approach to engage them"
    },
    "competitive_positioning": {
      "competitors": ["List of competitors mentioned or likely"],
      "differentiation": ["Key differentiators for this account"],
      "win_themes": ["Themes to emphasize throughout the deal"]
    },
    "deal_velocity_signals": {
      "positive": ["Signals that suggest fast deal movement"],
      "negative": ["Signals that suggest slow deal movement"],
      "recommended_timeline": "Recommended timeline based on signals"
    }
  },
  "security_refinements": {
    "risk_assessment": {
      "overall": "LOW|MEDIUM|HIGH",
      "factors": ["List of risk factors identified"],
      "mitigating": ["Mitigating factors that reduce risk"]
    },
    "compliance_gaps": [
      {
        "gap": "Specific compliance gap identified",
        "severity": "LOW|MEDIUM|HIGH",
        "action": "Recommended action",
        "fluency_alignment": "How Fluency helps address this gap"
      }
    ],
    "certification_verification": {
      "claimed": ["Certifications the company claims"],
      "verified": ["Certifications we could verify"],
      "unverified": ["Certifications we could not verify"],
      "actions": ["Actions to verify unverified certifications"]
    },
    "remediation_priorities": [
      {
        "priority": 1,
        "issue": "Specific security/compliance issue",
        "recommendation": "What to do about it"
      }
    ],
    "due_diligence_checklist": [
      "Specific items to verify during security review"
    ]
  },
  "product_refinements": {
    "integration_complexity": {
      "overall": "Simple|Moderate|Complex",
      "factors": [
        {
          "system": "System name",
          "complexity": "Simple|Moderate|Complex",
          "notes": "Specific integration notes"
        }
      ]
    },
    "tech_stack_compatibility": {
      "compatible": ["Technologies that work well with Fluency"],
      "needs_verification": ["Technologies that need verification"],
      "blockers": ["Potential technology blockers"]
    },
    "implementation_roadmap": {
      "approach": "Phased|Big Bang|Pilot",
      "phases": [
        {
          "phase": 1,
          "duration": "Estimated duration",
          "scope": "What's included in this phase"
        }
      ]
    },
    "deployment_risks": [
      {
        "risk": "Specific deployment risk",
        "probability": "LOW|MEDIUM|HIGH",
        "impact": "LOW|MEDIUM|HIGH",
        "mitigation": "How to mitigate this risk"
      }
    ],
    "success_factors": [
      "Critical success factors for deployment"
    ]
  }
}
```

## IMPORTANT GUIDELINES

1. Be SPECIFIC - Reference actual data from the research, not generic observations
2. Be ACTIONABLE - Every finding should lead to a clear action
3. Be STRATEGIC - Think about what each audience needs to succeed
4. Be CONCISE - Quality over quantity, 3-5 items per section is ideal
5. CROSS-REFERENCE - Use insights from multiple data sources when possible

Analyze ALL the data provided and generate audience-tailored refinements.
Look for connections between data points. Find the story the data tells.
Return your analysis as JSON.
"""


class BriefRefinerAgent(BaseAgent):
    """
    Opus-powered agent that generates audience-specific brief refinements.

    This agent excels at:
    - Tailoring intelligence to different stakeholder needs
    - Strategic allocation of findings across briefs
    - Making nuanced judgment calls about relevance
    - Generating actionable, specific recommendations per audience
    """

    @property
    def name(self) -> str:
        return "BriefRefiner"

    @property
    def system_prompt(self) -> str:
        return BRIEF_REFINER_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        # Pure reasoning - no tools needed
        return []

    async def generate_refinements(
        self,
        profile: CompanyProfile,
        synthesis: SynthesisOutput,
        research: ResearchResults
    ) -> dict:
        """
        Generate audience-specific refinements for all three briefs.

        Returns structured refinements for Sales, Security, and Product briefs.
        """
        # Build comprehensive research summary for the agent
        research_summary = self._build_research_summary(profile, synthesis, research)

        # Run the agent
        result = await self.run(research_summary)

        # Parse the JSON response
        data = result.get("json") or {}

        # Log stats
        sales_count = len(data.get("sales_refinements", {}).get("talking_points", []))
        security_count = len(data.get("security_refinements", {}).get("compliance_gaps", []))
        product_count = len(data.get("product_refinements", {}).get("deployment_risks", []))
        logger.info(
            f"[BriefRefiner] Generated refinements: "
            f"{sales_count} talking points, {security_count} compliance gaps, {product_count} deployment risks"
        )

        return {
            "sales_refinements": data.get("sales_refinements", {}),
            "security_refinements": data.get("security_refinements", {}),
            "product_refinements": data.get("product_refinements", {}),
        }

    def _build_research_summary(
        self,
        profile: CompanyProfile,
        synthesis: SynthesisOutput,
        research: ResearchResults
    ) -> str:
        """Build comprehensive summary of all research for Opus to analyze."""

        def safe_str(item) -> str:
            """Safely convert an item to string, handling dicts and objects."""
            if isinstance(item, dict):
                # Try common key names for the main value
                for key in ['name', 'claim', 'system', 'tool', 'regulation', 'signal', 'topic', 'value', 'text']:
                    if key in item:
                        return str(item[key])
                return str(item)
            elif hasattr(item, 'name'):
                return str(item.name)
            elif hasattr(item, 'claim'):
                return str(item.claim)
            else:
                return str(item)

        def safe_join(items, sep: str = ', ', limit: int = 5) -> str:
            """Safely join a list of items, handling dicts and objects."""
            if not items:
                return ''
            return sep.join(safe_str(item) for item in items[:limit])

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
            opps = []
            for o in synthesis.opportunities:
                if isinstance(o, dict):
                    opps.append(f"- {o.get('opportunity', o.get('claim', str(o)))}")
                else:
                    opps.append(f"- {o}")
            sections.append(f"""## Identified Opportunities
{chr(10).join(opps)}
""")

        if synthesis.blockers:
            blockers = []
            for b in synthesis.blockers:
                if isinstance(b, dict):
                    blockers.append(f"- {b.get('blocker', b.get('claim', str(b)))}")
                else:
                    blockers.append(f"- {b}")
            sections.append(f"""## Identified Blockers
{chr(10).join(blockers)}
""")

        # Stakeholder Intelligence (key for Sales)
        if research.stakeholders:
            sh = research.stakeholders
            leaders = [
                f"- {s.name}, {s.title}" +
                (f" (Champion signals: {', '.join(s.champion_signals[:2])})" if s.champion_signals else "")
                for s in sh.potential_champions[:5]
            ]
            tech_leaders = [
                f"- {s.name}, {s.title}" + (f" - {s.background[:50]}..." if s.background else "")
                for s in sh.technical_leaders[:5]
            ]

            sections.append(f"""## Stakeholder Intelligence
Potential Champions:
{chr(10).join(leaders) if leaders else '  None identified'}

Technical Leaders:
{chr(10).join(tech_leaders) if tech_leaders else '  None identified'}

Org Structure Signals: {safe_join(sh.org_structure_signals) or 'Unknown'}
""")

        # LinkedIn Intelligence
        if research.linkedin_intel:
            li = research.linkedin_intel
            execs = []
            for e in li.executives_found[:5]:
                if isinstance(e, dict):
                    topics = e.get("recent_topics", [])
                    execs.append(
                        f"- {e.get('name', 'Unknown')}, {e.get('title', '')} - "
                        f"Topics: {', '.join(str(t) for t in topics[:3]) if topics else 'None'}"
                    )
                elif hasattr(e, 'name'):
                    # Handle Pydantic model objects
                    topics = getattr(e, 'recent_topics', []) or []
                    execs.append(
                        f"- {e.name}, {getattr(e, 'title', '')} - "
                        f"Topics: {', '.join(str(t) for t in topics[:3]) if topics else 'None'}"
                    )
                else:
                    execs.append(f"- {str(e)}")

            sections.append(f"""## LinkedIn Intelligence
Company Page Followers: {li.follower_count or 'Unknown'}
Executives Found:
{chr(10).join(execs) if execs else '  None'}

Thought Leadership Topics: {safe_join(li.thought_leadership_topics) or 'None'}
Strategic Initiatives: {safe_join(li.strategic_initiatives, limit=3) or 'None'}
Hiring Announcements: {safe_join(li.hiring_announcements, limit=3) or 'None'}
Culture Signals: {safe_join(li.culture_signals, limit=4) or 'None'}
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

Process Tools Mentioned: {safe_join(jp.process_tools_mentioned) or 'None'}
Team Growth Areas: {safe_join(jp.team_growth_areas) or 'Unknown'}
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
{chr(10).join(f'- {safe_str(p)}' for p in cr.pain_points[:5]) if cr.pain_points else '  None identified'}

Integration Challenges:
{chr(10).join(f'- {safe_str(c)}' for c in cr.integration_challenges[:3]) if cr.integration_challenges else '  None identified'}

Competitor Mentions:
{chr(10).join(competitors) if competitors else '  None'}

Implementation Signals: {safe_join(cr.implementation_signals, limit=3) or 'None'}
""")

        # Regulatory Risk
        if research.regulatory_risk:
            rr = research.regulatory_risk
            sections.append(f"""## Regulatory Risk Intelligence
Risk Level: {rr.risk_level}
Regulatory Exposure: {safe_join(rr.regulatory_exposure) or 'Standard'}

Enforcement Actions:
{chr(10).join(f'- {a.claim}' for a in rr.enforcement_actions[:3]) if rr.enforcement_actions else '  None found'}

Data Breaches:
{chr(10).join(f'- {b.claim}' for b in rr.data_breaches[:3]) if rr.data_breaches else '  None found'}

Active Litigation:
{chr(10).join(f'- {l.claim}' for l in rr.active_litigation[:3]) if rr.active_litigation else '  None found'}
""")

        # Security Findings (key for Security brief)
        if research.security:
            sec = research.security
            certs = [f"- {c.name} ({c.status})" for c in sec.certifications[:10]]

            sections.append(f"""## Security Posture
Trust Center: {sec.trust_center_url or 'Not found'}
Security Maturity: {sec.security_maturity}
Data Residency: {safe_join(sec.data_residency) or 'Unknown'}

Certifications:
{chr(10).join(certs) if certs else '  None found'}

Privacy Requirements: {safe_join(sec.privacy_requirements) or 'None identified'}

Security Incidents:
{chr(10).join(f'- {i.claim}' for i in sec.security_incidents[:3]) if sec.security_incidents else '  None found'}
""")

        # Tech Stack (key for Product brief)
        if research.tech_stack:
            tech = research.tech_stack
            integrations = []
            for integ in tech.integrations[:15]:
                integrations.append(f"- {integ.tool_name} ({integ.category})")

            sections.append(f"""## Tech Stack
Identity Provider: {tech.identity_provider or 'Unknown'}
Cloud Provider: {tech.cloud_provider or 'Unknown'}

Detected Integrations:
{chr(10).join(integrations) if integrations else '  None found'}

Subdomains Found: {len(tech.subdomains_found) if tech.subdomains_found else 0}
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

Tech Debt Signals: {safe_join(ir.tech_debt_signals, limit=3) or 'None'}
Change Management Concerns: {safe_join(ir.change_management_concerns, limit=3) or 'None'}

Success Factors:
{chr(10).join(f'- {safe_str(f)}' for f in ir.success_factors[:4]) if ir.success_factors else '  Not identified'}

Risk Mitigations:
{chr(10).join(f'- {safe_str(m)}' for m in ir.risk_mitigations[:4]) if ir.risk_mitigations else '  Not identified'}
""")

        # Operational Culture
        if research.operational_culture:
            oc = research.operational_culture
            sections.append(f"""## Operational Culture
Culture Type: {oc.culture_type}
Reliability Priority: {oc.reliability_priority}
Velocity Priority: {oc.velocity_priority}
Deployment Approach: {oc.deployment_approach}
Methodology Signals: {safe_join(oc.methodology_signals, limit=4) or 'None'}
Positioning Recommendation: {oc.positioning_recommendation or 'None'}
Keywords to Use: {safe_join(oc.keywords_to_use) or 'None'}
Keywords to Avoid: {safe_join(oc.keywords_to_avoid) or 'None'}
""")

        # Shadow IT
        if research.shadow_it:
            sit = research.shadow_it
            # Handle legacy_systems_detected which could be strings or dicts
            legacy_systems = []
            for sys in (sit.legacy_systems_detected[:5] if sit.legacy_systems_detected else []):
                if isinstance(sys, dict):
                    legacy_systems.append(sys.get('system', sys.get('name', str(sys))))
                else:
                    legacy_systems.append(str(sys))
            # Handle shadow_it_tools which could be strings or dicts
            shadow_tools = []
            for tool in (sit.shadow_it_tools[:5] if sit.shadow_it_tools else []):
                if isinstance(tool, dict):
                    shadow_tools.append(tool.get('tool', tool.get('name', str(tool))))
                else:
                    shadow_tools.append(str(tool))
            sections.append(f"""## Shadow IT Assessment
Tech Debt Level: {sit.tech_debt_level}
Legacy Systems: {', '.join(legacy_systems) if legacy_systems else 'None identified'}
Shadow IT Tools: {', '.join(shadow_tools) if shadow_tools else 'None identified'}
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

        # Financial findings
        if research.financials:
            fin = research.financials
            sections.append(f"""## Financial Context
Revenue: {fin.revenue or 'Unknown'}
Revenue Growth: {fin.revenue_growth or 'Unknown'}
Cash Position: {fin.cash_position or 'Unknown'}

Geographic Operations: {safe_join(fin.geographic_operations) or 'Unknown'}
Regulatory Mentions: {safe_join(fin.regulatory_mentions) or 'None'}

Risk Factors:
{chr(10).join(f'- {safe_str(r)}' for r in fin.risk_factors[:5]) if fin.risk_factors else '  None identified'}
""")

        # Local Regulations
        if research.local_regulations:
            lr = research.local_regulations
            # Handle operating_regions which could be strings or dicts
            regions = []
            for r in (lr.operating_regions or []):
                if isinstance(r, dict):
                    regions.append(r.get('region', r.get('name', str(r))))
                else:
                    regions.append(str(r))
            # Handle applicable_regulations which could be strings or dicts
            regs = []
            for r in (lr.applicable_regulations[:5] if lr.applicable_regulations else []):
                if isinstance(r, dict):
                    regs.append(r.get('regulation', r.get('name', str(r))))
                else:
                    regs.append(str(r))
            sections.append(f"""## Local Regulations
Operating Regions: {', '.join(regions) if regions else 'Unknown'}
Applicable Regulations: {', '.join(regs) if regs else 'None'}
Works Council Required: {lr.works_council_required if hasattr(lr, 'works_council_required') else 'Unknown'}
""")

        # Final instruction
        sections.append("""## YOUR TASK

Analyze ALL the data above and generate AUDIENCE-SPECIFIC refinements for three teams:

1. **Sales Team** - Needs talking points, objection handlers, champion engagement strategy,
   competitive positioning, and deal velocity signals.

2. **Security/Compliance Team** - Needs risk assessment, compliance gaps analysis,
   certification verification, remediation priorities, and due diligence checklist.

3. **Product/Implementation Team** - Needs integration complexity assessment, tech stack
   compatibility analysis, implementation roadmap, deployment risks, and success factors.

For each finding, think about:
- Who needs this information most?
- How should it be presented for that audience?
- What specific action should they take?

Be SPECIFIC - use actual data from the research.
Be ACTIONABLE - every finding should have a clear next step.
Be STRATEGIC - tailor content to what each team needs to succeed.

Return your analysis as JSON with sales_refinements, security_refinements, and product_refinements.
""")

        return "\n".join(sections)
