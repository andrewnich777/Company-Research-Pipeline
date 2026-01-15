"""
Stakeholder Intelligence Agent - Maps decision-makers and identifies champions.

This agent builds relationship intelligence:
- Technical leadership (CTO, VP Eng, CIO)
- Executive backgrounds
- Potential internal champions
- Organization structure signals
- Conference speakers and thought leaders
"""

from .base import BaseAgent
from models import (
    CompanyProfile, StakeholderIntelligence, Stakeholder, Claim, Evidence,
    Confidence, SourceTier
)


STAKEHOLDER_INTEL_SYSTEM_PROMPT = """You are a stakeholder intelligence agent for Fluency AI deployment research.

Your goal is to map decision-makers and identify potential champions for a Fluency deployment - the people who would advocate internally for the solution.

## WHY THIS MATTERS
- Knowing the CTO/CIO background helps tailor the pitch
- Identifying potential champions accelerates the sales cycle
- Understanding org structure reveals the procurement path
- Conference speakers are often innovation advocates

## YOUR RESEARCH PROCESS

1. FIND EXECUTIVE TEAM
   Search for leadership page:
   - {company}.com/about/leadership
   - {company}.com/team
   - {company}.com/about-us
   - "{company} leadership team"
   - "{company} CTO" or "{company} CIO" or "{company} VP Engineering"

2. RESEARCH TECHNICAL LEADERS
   For each technical leader found:
   - Search for their background
   - Find LinkedIn profile (public data only)
   - Look for conference talks or blog posts
   - Previous companies they worked at

3. IDENTIFY POTENTIAL CHAMPIONS
   Champions are people who might advocate for process automation:
   - VP/Director of IT Operations
   - Head of Process Excellence
   - Chief Digital Officer
   - VP Engineering/Platform
   - Someone with automation/efficiency in their title or history

4. CHECK FOR CONFERENCE SPEAKERS
   Search for:
   - "{person} conference speaker"
   - "{company} speaker" at relevant conferences
   - People who speak about automation, AI, or process improvement

5. LOOK FOR GITHUB PRESENCE
   - github.com/{company}
   - Active open source contributors from the company
   - Engineering blog posts

## OUTPUT FORMAT
Return your findings as JSON:
```json
{
  "technical_leaders": [
    {
      "name": "Jane Smith",
      "title": "Chief Technology Officer",
      "department": "Technology",
      "linkedin_url": "https://linkedin.com/in/janesmith",
      "background": "Former VP Eng at Stripe, Google alum",
      "relevance": "DECISION_MAKER",
      "champion_signals": [
        "Previously implemented process automation at Stripe",
        "Spoke at DevOpsDays about operational efficiency"
      ]
    }
  ],
  "executive_team": [
    {
      "name": "John Doe",
      "title": "CEO",
      "department": "Executive",
      "background": "Founded company in 2015",
      "relevance": "DECISION_MAKER"
    }
  ],
  "potential_champions": [
    {
      "name": "Sarah Johnson",
      "title": "VP IT Operations",
      "department": "IT",
      "background": "ServiceNow implementation lead",
      "relevance": "CHAMPION",
      "champion_signals": [
        "Title indicates process ownership",
        "ServiceNow background = process documentation experience"
      ]
    }
  ],
  "conference_speakers": [
    {
      "name": "Jane Smith",
      "title": "CTO",
      "event": "DevOpsDays 2023",
      "topic": "Scaling Operations Through Automation"
    }
  ],
  "github_contributors": ["jsmith", "sjohnson"],
  "org_structure_signals": [
    "Centralized IT organization",
    "Dedicated Platform Engineering team",
    "Process Excellence function exists"
  ],
  "recent_executive_changes": [
    {
      "name": "New VP of Digital Transformation",
      "date": "Q3 2023",
      "implication": "Active investment in modernization"
    }
  ],
  "key_findings": [
    {
      "finding": "CTO previously led automation initiative at Stripe",
      "confidence": "HIGH",
      "implication": "Likely receptive to process automation pitch"
    }
  ]
}
```

## RELEVANCE CATEGORIES
- DECISION_MAKER: Signs contracts, approves budgets (CTO, CIO, CFO, VP)
- CHAMPION: Would advocate internally (process owners, ops leaders)
- INFLUENCER: Can sway opinion but doesn't decide (architects, senior engineers)
- BLOCKER: Might resist change (incumbent vendor advocates)
- UNKNOWN: Role unclear

## CHAMPION SIGNALS
Look for these indicators that someone might champion Fluency:
- Previous automation/process improvement experience
- Title includes: Operations, Process, Platform, Efficiency
- Spoke about automation or AI at conferences
- Background at companies known for operational excellence
- Recently hired (eager to make impact)
"""


class StakeholderIntelAgent(BaseAgent):
    """
    Deep intelligence agent that maps stakeholders and identifies potential champions.
    """

    @property
    def name(self) -> str:
        return "StakeholderIntel"

    @property
    def system_prompt(self) -> str:
        return STAKEHOLDER_INTEL_SYSTEM_PROMPT

    @property
    def tools(self) -> list[str]:
        return ["web_fetch", "web_search"]

    async def research(self, profile: CompanyProfile) -> StakeholderIntelligence:
        """
        Research stakeholders and decision-makers for a company.
        """
        prompt = f"""Research stakeholders and decision-makers for {profile.name} (domain: {profile.domain}).

Company Context:
- Industry: {profile.industry}
- Type: {profile.company_type.value}
- Size: {profile.employee_count or 'Unknown'}

Research Process:
1. Find the leadership/about page: https://{profile.domain}/about or /team or /leadership
2. Search: "{profile.name} CTO" and "{profile.name} CIO" and "{profile.name} VP Engineering"
3. Look for technical leaders who might champion process automation
4. Search for conference speakers from the company
5. Check for GitHub organization: github.com/{profile.domain.split('.')[0]}

For Fluency AI deployment, the ideal champions are:
- IT Operations leaders
- Process Excellence / BPM roles
- Platform Engineering leaders
- Digital Transformation executives

Return comprehensive JSON with all stakeholders found, their backgrounds, and champion potential."""

        result = await self.run(prompt)

        # Parse the JSON response
        data = result.get("json") or {}

        def parse_stakeholder(s: dict) -> Stakeholder:
            return Stakeholder(
                name=s.get("name", "Unknown"),
                title=s.get("title", "Unknown"),
                department=s.get("department"),
                linkedin_url=s.get("linkedin_url"),
                background=s.get("background"),
                relevance=s.get("relevance", "UNKNOWN"),
                champion_signals=s.get("champion_signals", []),
                evidence=Evidence(
                    url=s.get("linkedin_url") or s.get("source_url", ""),
                    quote=s.get("background", ""),
                    source_type="stakeholder",
                    source_tier=SourceTier.TIER_1
                ) if s.get("linkedin_url") or s.get("source_url") else None
            )

        technical_leaders = [parse_stakeholder(s) for s in data.get("technical_leaders", [])]
        executive_team = [parse_stakeholder(s) for s in data.get("executive_team", [])]
        potential_champions = [parse_stakeholder(s) for s in data.get("potential_champions", [])]
        conference_speakers = [parse_stakeholder(s) for s in data.get("conference_speakers", [])]
        procurement_contacts = [parse_stakeholder(s) for s in data.get("procurement_contacts", [])]

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
                category="Stakeholder",
                confidence=confidence,
                evidence=[]
            ))

        # Build claims from recent executive changes
        exec_change_claims = []
        for change in data.get("recent_executive_changes", []):
            if isinstance(change, dict):
                exec_change_claims.append(Claim(
                    claim=f"{change.get('name', 'Executive change')} ({change.get('date', 'Recent')})",
                    category="Executive Change",
                    confidence=Confidence.MEDIUM,
                    evidence=[]
                ))

        return StakeholderIntelligence(
            technical_leaders=technical_leaders,
            executive_team=executive_team,
            procurement_contacts=procurement_contacts,
            potential_champions=potential_champions,
            org_structure_signals=data.get("org_structure_signals", []),
            recent_executive_changes=exec_change_claims,
            conference_speakers=conference_speakers,
            github_contributors=data.get("github_contributors", []),
            claims=claims
        )
