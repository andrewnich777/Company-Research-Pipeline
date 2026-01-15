"""
Executive Brief Generator - Overall deal intelligence for winning deployments.

This brief consolidates deep intelligence into actionable deal insights:
1. Key Intelligence - Wow findings you can't get from Google
2. Strategic Insights - Cross-referenced findings with actions
3. Deal Intelligence Summary - Decision makers, budget, procurement
4. Risk & Red Flags Report - Blockers, concerns, regulatory exposure
5. Relationship Mapping - Stakeholders, champions, org structure
"""

from models import CompanyProfile, SynthesisOutput, ResearchResults


# Source tracking for citations
class SourceTracker:
    """
    Track sources throughout brief generation for end citations.

    Source quality (separate from claim confidence):
    - PRIMARY (🟢): Official/authoritative source (trust center, SEC filing, company page)
    - SECONDARY (🟡): Reliable but indirect (job posting, press release, news article)
    - WEAK (🔴): Unverifiable or single indirect reference (blog mention, forum post)
    """

    def __init__(self):
        self.sources = []
        self._counter = 0

    def add(self, description: str, url: str = None, quality: str = "SECONDARY") -> str:
        """
        Add a source and return the colored superscript reference.

        Args:
            description: What the source is (e.g., "Official Trust Center")
            url: URL if available
            quality: PRIMARY (🟢), SECONDARY (🟡), or WEAK (🔴)
        """
        self._counter += 1
        self.sources.append({
            "num": self._counter,
            "description": description,
            "url": url,
            "quality": quality
        })
        # Return colored superscript based on source quality
        color_map = {
            "PRIMARY": "🟢",
            "SECONDARY": "🟡",
            "WEAK": "🔴"
        }
        color = color_map.get(quality, "⚪")
        return f"^{color}{self._counter}^"

    def generate_references(self) -> list[str]:
        """Generate the references section grouped by source quality."""
        if not self.sources:
            return []

        lines = []
        lines.append("---")
        lines.append("## Sources & References")
        lines.append("")
        lines.append("*Source quality: 🟢 = official/primary | 🟡 = secondary/indirect | 🔴 = weak/unverified*")
        lines.append("")

        # Group by quality
        primary = [s for s in self.sources if s["quality"] == "PRIMARY"]
        secondary = [s for s in self.sources if s["quality"] == "SECONDARY"]
        weak = [s for s in self.sources if s["quality"] == "WEAK"]

        if primary:
            lines.append("**🟢 Primary Sources**")
            for s in primary:
                url_part = f" - {s['url']}" if s['url'] else ""
                lines.append(f"{s['num']}. {s['description']}{url_part}")
            lines.append("")

        if secondary:
            lines.append("**🟡 Secondary Sources**")
            for s in secondary:
                url_part = f" - {s['url']}" if s['url'] else ""
                lines.append(f"{s['num']}. {s['description']}{url_part}")
            lines.append("")

        if weak:
            lines.append("**🔴 Weak/Unverified Sources**")
            for s in weak:
                url_part = f" - {s['url']}" if s['url'] else ""
                lines.append(f"{s['num']}. {s['description']}{url_part}")
            lines.append("")

        return lines


def _confidence_badge(level: str) -> str:
    """Return confidence badge based on level."""
    badges = {
        "HIGH": "[verified]",
        "MEDIUM": "[strong signal]",
        "LOW": "[inferred]",
    }
    return badges.get(level, "[unverified]")


def _generate_wow_findings(
    profile: CompanyProfile,
    synthesis: SynthesisOutput,
    research: ResearchResults,
    sources: SourceTracker
) -> list[str]:
    """
    Generate the 'Key Intelligence' section with surprising, non-obvious findings.
    These are the wow moments that couldn't be found in 5 minutes on Google.
    """
    lines = []
    lines.append("## Key Intelligence (What Google Won't Tell You)")
    lines.append("")

    wow_findings = []

    # 1. Champion identification with evidence
    if research.stakeholders and research.stakeholders.potential_champions:
        champion = research.stakeholders.potential_champions[0]
        signals = champion.champion_signals[:2] if champion.champion_signals else []
        if signals:
            src = sources.add("LinkedIn/Company Page - Stakeholder Profile", quality="SECONDARY")
            wow_findings.append({
                "category": "Hidden Champion",
                "finding": f"**{champion.name}** ({champion.title}) shows champion signals: {'; '.join(signals)}{src}",
                "action": "Prioritize outreach to this person - they can sell internally",
                "confidence": "HIGH"
            })

    # 2. Budget signals from hiring patterns
    if research.job_postings:
        jp = research.job_postings
        if jp.hiring_velocity == "HIGH" and jp.total_open_roles > 10:
            src = sources.add("Job Board Analysis (Greenhouse/Lever)", quality="SECONDARY")
            wow_findings.append({
                "category": "Budget Signal",
                "finding": f"**{jp.total_open_roles} open roles** with HIGH hiring velocity{src}",
                "action": "Propose pilot within 30-60 days before budget cycles close",
                "confidence": "HIGH"
            })
        if jp.process_tools_mentioned:
            src = sources.add("Job Posting Requirements", quality="SECONDARY")
            wow_findings.append({
                "category": "Integration Opportunity",
                "finding": f"Job postings mention **{', '.join(jp.process_tools_mentioned)}**{src}",
                "action": "Lead demos with these tool integrations",
                "confidence": "HIGH"
            })

    # 3. Pain points confirmed from customer reviews
    if research.customer_reviews and research.customer_reviews.pain_points:
        pain = research.customer_reviews.pain_points[0]
        src = sources.add("G2/Capterra Customer Reviews", quality="SECONDARY")
        wow_findings.append({
            "category": "Pain Confirmed",
            "finding": f"Customer reviews cite: \"{pain}\"{src}",
            "action": "Reference this pain point in discovery - it's already validated",
            "confidence": "MEDIUM"
        })

    # 4. Regulatory red flags or clean record
    if research.regulatory_risk:
        rr = research.regulatory_risk
        if rr.enforcement_actions or rr.data_breaches:
            issue = rr.enforcement_actions[0].claim if rr.enforcement_actions else rr.data_breaches[0].claim
            src = sources.add("Regulatory Database Search (SEC/FTC)", quality="PRIMARY")
            wow_findings.append({
                "category": "Compliance History",
                "finding": f"Found regulatory issue: {issue}{src}",
                "action": "Lead with Fluency's SOC 2 and compliance story - they need risk mitigation",
                "confidence": "HIGH"
            })
        elif rr.risk_level == "LOW":
            src = sources.add("Regulatory Database Search (no results)", quality="SECONDARY")
            wow_findings.append({
                "category": "Fast-Track Signal",
                "finding": f"Clean regulatory record - no enforcement actions or breaches found{src}",
                "action": "Compliance review will be smoother - push for faster procurement",
                "confidence": "MEDIUM"
            })

    # 5. Tech stack from jobs vs. marketing
    if research.job_postings and research.job_postings.tech_stack_signals:
        ts = research.job_postings.tech_stack_signals
        techs = []
        for category, items in ts.items():
            techs.extend(items[:2])
        if techs:
            src = sources.add("Job Posting Technical Requirements", quality="SECONDARY")
            wow_findings.append({
                "category": "Real Tech Stack",
                "finding": f"Job requirements reveal actual stack: **{', '.join(techs[:6])}**{src}",
                "action": "Reference these specific technologies in technical discussions",
                "confidence": "HIGH"
            })

    # 6. Conference speakers / thought leaders
    if research.stakeholders and research.stakeholders.conference_speakers:
        speaker = research.stakeholders.conference_speakers[0]
        src = sources.add("Conference Speaker Database", quality="PRIMARY")
        wow_findings.append({
            "category": "Thought Leader",
            "finding": f"**{speaker.name}** ({speaker.title}) speaks at conferences{' - ' + speaker.background if speaker.background else ''}{src}",
            "action": "Reference their public talks in outreach - builds instant credibility",
            "confidence": "HIGH"
        })

    # 7. LinkedIn thought leadership topics - what execs publicly care about
    if research.linkedin_intel and research.linkedin_intel.thought_leadership_topics:
        topics = research.linkedin_intel.thought_leadership_topics[:3]
        src = sources.add("LinkedIn Executive Posts", quality="SECONDARY")
        wow_findings.append({
            "category": "Executive Priorities",
            "finding": f"Leadership publicly discusses: **{', '.join(topics)}**{src}",
            "action": "Reference these topics in outreach - shows you did your homework",
            "confidence": "MEDIUM"
        })

    # 8. LinkedIn strategic initiatives - real-time signals
    if research.linkedin_intel and research.linkedin_intel.strategic_initiatives:
        initiative = research.linkedin_intel.strategic_initiatives[0]
        src = sources.add("LinkedIn Company/Executive Posts", quality="SECONDARY")
        wow_findings.append({
            "category": "Strategic Initiative",
            "finding": f"Announced: **{initiative}**{src}",
            "action": "Position Fluency as enabler of this initiative",
            "confidence": "HIGH"
        })

    # 9. LinkedIn hiring announcements (different from job board data)
    if research.linkedin_intel and research.linkedin_intel.hiring_announcements:
        announcement = research.linkedin_intel.hiring_announcements[0]
        src = sources.add("LinkedIn Hiring Posts", quality="SECONDARY")
        wow_findings.append({
            "category": "Growth Signal",
            "finding": f"LinkedIn hiring post: **{announcement}**{src}",
            "action": "Growth mode = budget available. Strike while iron is hot",
            "confidence": "MEDIUM"
        })

    # Output the findings
    if wow_findings:
        for i, finding in enumerate(wow_findings[:5], 1):
            badge = _confidence_badge(finding["confidence"])
            lines.append(f"**{i}. {finding['category']}** {badge}")
            lines.append(f"   {finding['finding']}")
            lines.append(f"   -> ACTION: {finding['action']}")
            lines.append("")
    else:
        lines.append("*Limited deep intelligence available - prioritize discovery call*")
        lines.append("")
        lines.append("-> ACTION: Focus discovery on identifying champions and understanding tech stack")
        lines.append("")

    return lines


def _generate_strategic_insights(
    profile: CompanyProfile,
    synthesis: SynthesisOutput,
    research: ResearchResults,
    sources: SourceTracker
) -> list[str]:
    """
    Generate cross-referenced strategic insights that connect multiple data sources.
    """
    lines = []
    lines.append("## Strategic Insights (Cross-Referenced)")
    lines.append("")

    insights = []

    # Insight 1: Champion + Pain + Timing alignment
    has_champion = research.stakeholders and research.stakeholders.potential_champions
    has_pain = research.customer_reviews and research.customer_reviews.pain_points
    has_hiring = research.job_postings and research.job_postings.hiring_velocity == "HIGH"

    if has_champion and has_pain:
        champion = research.stakeholders.potential_champions[0]
        pain = research.customer_reviews.pain_points[0]
        src1 = sources.add("Stakeholder Intelligence", quality="SECONDARY")
        src2 = sources.add("Customer Review Analysis", quality="SECONDARY")
        insight = f"**Champion + Pain Alignment:** {champion.name} ({champion.title}){src1} can advocate internally while addressing documented pain: \"{pain[:60]}...\"{src2}"
        if has_hiring:
            src3 = sources.add("Job Posting Analysis", quality="SECONDARY")
            insight += f" Timing favorable - high hiring velocity{src3}"
        insights.append({
            "insight": insight,
            "action": "Position Fluency as the solution to their stated problem, with an internal champion ready"
        })

    # Insight 2: Tech stack + Process tools = Integration story
    has_tech = research.job_postings and research.job_postings.tech_stack_signals
    has_process_tools = research.job_postings and research.job_postings.process_tools_mentioned
    has_idp = research.tech_stack and research.tech_stack.identity_provider

    if has_process_tools and (has_tech or has_idp):
        tools = research.job_postings.process_tools_mentioned
        idp = research.tech_stack.identity_provider if has_idp else None
        src1 = sources.add("Job Posting Tool Requirements", quality="SECONDARY")
        insight = f"**Integration-Ready:** They use {', '.join(tools)}{src1} for process documentation"
        if idp:
            src2 = sources.add("Tech Stack Discovery", quality="SECONDARY")
            insight += f" with {idp}{src2} for identity"
        insight += " - Fluency integrates with all of these."
        insights.append({
            "insight": insight,
            "action": "Demo should show live integration with their existing tools"
        })

    # Insight 3: Regulatory + Security = Compliance positioning
    has_security = research.security and research.security.certifications
    has_regulatory_exposure = research.regulatory_risk and research.regulatory_risk.regulatory_exposure

    if has_security and has_regulatory_exposure:
        certs = [c.name for c in research.security.certifications[:3]]
        exposures = research.regulatory_risk.regulatory_exposure[:2]
        src1 = sources.add("Official Trust Center", quality="PRIMARY")
        src2 = sources.add("Regulatory Exposure Analysis", quality="SECONDARY")
        insight = f"**Compliance-Conscious:** They maintain {', '.join(certs)}{src1} and have exposure to {', '.join(exposures)}{src2}."
        insight += " Fluency's SOC 2 + audit trail aligns with their compliance needs."
        insights.append({
            "insight": insight,
            "action": "Lead with compliance documentation - they'll ask for it anyway"
        })

    # Insight 4: Growth signals + No AI initiatives = Opportunity
    has_high_growth = research.job_postings and research.job_postings.total_open_roles > 15
    has_ai_initiatives = research.strategic and research.strategic.ai_initiatives

    if has_high_growth and not has_ai_initiatives:
        roles = research.job_postings.total_open_roles
        src1 = sources.add("Job Board Role Count", quality="SECONDARY")
        src2 = sources.add("Strategic News Search", quality="WEAK")
        insight = f"**AI Entry Point:** {roles} open roles{src1} but no announced AI/automation initiatives{src2}. They're scaling manually."
        insight += " Fluency can be positioned as their process automation starting point."
        insights.append({
            "insight": insight,
            "action": "Frame Fluency as essential for scaling without proportionally scaling ops overhead"
        })

    # Insight 5: LinkedIn thought leadership + Pain points = Perfect alignment
    has_linkedin_topics = research.linkedin_intel and research.linkedin_intel.thought_leadership_topics

    if has_linkedin_topics and has_pain:
        topics = research.linkedin_intel.thought_leadership_topics[:2]
        pain = research.customer_reviews.pain_points[0]
        src1 = sources.add("LinkedIn Executive Posts", quality="SECONDARY")
        src2 = sources.add("Customer Review Analysis", quality="SECONDARY")

        # Check for topic-pain alignment
        topic_pain_match = any(
            t.lower() in pain.lower() or pain.lower() in t.lower()
            for t in topics
        )
        if topic_pain_match:
            insight = f"**Leadership + Customer Alignment:** Executives post about {', '.join(topics)}{src1} and customers cite related pain: \"{pain[:50]}...\"{src2}"
            insight += " - Leadership is already thinking about this problem."
            insights.append({
                "insight": insight,
                "action": "Quote both executive posts AND customer pain in outreach - shows comprehensive understanding"
            })
        else:
            insight = f"**Dual Entry Point:** Executives discuss {', '.join(topics)}{src1} while customers struggle with \"{pain[:40]}...\"{src2}"
            insight += " - Multiple angles for value prop."
            insights.append({
                "insight": insight,
                "action": "Tailor messaging: exec outreach focuses on their public topics, user outreach on pain points"
            })

    # Insight 6: LinkedIn culture + Tech stack = Fit assessment
    has_culture = research.linkedin_intel and research.linkedin_intel.culture_signals

    if has_culture and has_tech:
        culture = research.linkedin_intel.culture_signals[:2]
        src = sources.add("LinkedIn Culture Signals", quality="SECONDARY")
        insight = f"**Culture Fit:** Company signals: {', '.join(culture)}{src}"
        if any("engineering" in c.lower() or "tech" in c.lower() for c in culture):
            insight += " - Engineering-led culture means technical proof points matter most."
            insights.append({
                "insight": insight,
                "action": "Lead with technical demos and architecture discussions, not ROI slides"
            })
        elif any("remote" in c.lower() or "distributed" in c.lower() for c in culture):
            insight += " - Distributed team means async collaboration is critical."
            insights.append({
                "insight": insight,
                "action": "Emphasize Fluency's async features and documentation-as-communication value"
            })

    # Output insights
    if insights:
        for insight in insights[:3]:
            lines.append(f"{insight['insight']}")
            lines.append(f"   -> ACTION: {insight['action']}")
            lines.append("")
    else:
        lines.append("*Insufficient cross-referenced data for strategic insights*")
        lines.append("")
        lines.append("-> ACTION: Use discovery call to gather connecting data points")
        lines.append("")

    return lines


def generate_executive_brief(
    profile: CompanyProfile,
    synthesis: SynthesisOutput,
    research: ResearchResults
) -> str:
    """
    Generate the comprehensive executive intelligence brief.

    This is the "overall brief" that provides deal-winning context beyond
    the standard sales/security/product briefs.

    Returns markdown-formatted string.
    """
    lines = []

    # Create source tracker for citations
    sources = SourceTracker()

    # Header
    lines.append(f"# Executive Intelligence Brief: {profile.name}")
    lines.append("")
    lines.append("**Fluency AI Deployment Intelligence**")
    lines.append("")
    lines.append(f"> {profile.description[:200]}..." if len(profile.description) > 200 else f"> {profile.description}")
    lines.append("")

    # Quick Stats with confidence indicators
    src_profile = sources.add("Company Website/Discovery", quality="PRIMARY")
    synthesis_failed = "Could not complete" in synthesis.deployment_score.rationale or synthesis.deployment_score.rationale == ""

    lines.append("## Quick Assessment")
    lines.append("")
    lines.append(f"| Metric | Value | Signal |")
    lines.append(f"|--------|-------|--------|")
    lines.append(f"| **Company Type** | {profile.company_type.value} | {src_profile} |")
    lines.append(f"| **Industry** | {profile.industry} | - |")
    lines.append(f"| **Size** | {profile.employee_count or 'Unknown'} | - |")

    if synthesis_failed:
        lines.append(f"| **Overall Score** | -- | *Synthesis incomplete* |")
        lines.append(f"| **Champion Score** | -- | *Run --resume* |")
        lines.append(f"| **Regulatory Risk** | -- | *Data pending* |")
    else:
        score = synthesis.deployment_score.overall
        score_signal = "Strong fit" if score >= 7 else "Moderate fit" if score >= 5 else "Challenging"
        lines.append(f"| **Overall Score** | {score:.1f}/10 | {score_signal} |")
        champ = synthesis.deployment_score.champion_identified
        champ_signal = "Champion identified" if champ >= 7 else "Potential champions" if champ >= 5 else "Need discovery"
        lines.append(f"| **Champion Score** | {champ}/10 | {champ_signal} |")
        reg = synthesis.deployment_score.regulatory_risk
        reg_signal = "Low risk" if reg >= 7 else "Moderate risk" if reg >= 5 else "High risk - address early"
        lines.append(f"| **Regulatory Risk** | {reg}/10 | {reg_signal} |")
    lines.append("")

    # ==========================================================================
    # KEY INTELLIGENCE (WOW FINDINGS) - NEW SECTION
    # ==========================================================================
    lines.append("---")
    lines.extend(_generate_wow_findings(profile, synthesis, research, sources))

    # ==========================================================================
    # STRATEGIC INSIGHTS (CROSS-REFERENCED) - NEW SECTION
    # ==========================================================================
    lines.append("---")
    lines.extend(_generate_strategic_insights(profile, synthesis, research, sources))

    # ==========================================================================
    # SECTION 1: DEAL INTELLIGENCE SUMMARY
    # ==========================================================================
    lines.append("---")
    lines.append("## Deal Intelligence Summary")
    lines.append("")

    # Decision Makers & Authority
    lines.append("### Decision Makers & Authority")
    lines.append("")

    if research.stakeholders:
        stakeholders = research.stakeholders

        # Technical Decision Makers
        if stakeholders.technical_leaders:
            lines.append("**Technical Leadership:**")
            for leader in stakeholders.technical_leaders[:5]:
                bg = f" - {leader.background}" if leader.background else ""
                signals = ""
                if leader.champion_signals:
                    signals = f" [verified]"
                else:
                    signals = " [inferred]"
                lines.append(f"- **{leader.name}**, {leader.title}{bg}{signals}")
            lines.append("")
            lines.append("-> ACTION: Map reporting structure to identify budget authority")
            lines.append("")

        # Potential Champions with action
        if stakeholders.potential_champions:
            lines.append("**Potential Internal Champions:**")
            for champion in stakeholders.potential_champions[:3]:
                reasons = ""
                if champion.champion_signals:
                    reasons = f" *(Signals: {'; '.join(champion.champion_signals[:2])})*"
                lines.append(f"- **{champion.name}**, {champion.title}{reasons}")
            lines.append("")
            lines.append("-> ACTION: Prioritize outreach to top champion - they can navigate internal politics")
            lines.append("")
        else:
            lines.append("**Champions:** Not identified from public data")
            lines.append("")
            lines.append("-> ACTION: In discovery, ask 'Who drives process improvement initiatives?' to find champions")
            lines.append("")
    else:
        lines.append("*Stakeholder intelligence limited - organization structure unclear*")
        lines.append("")
        lines.append("-> ACTION: Request org chart or LinkedIn research before first call")
        lines.append("")

    # Budget Indicators with interpretation
    lines.append("### Budget Indicators")
    lines.append("")

    if research.job_postings:
        jp = research.job_postings
        lines.append(f"- **Hiring Velocity:** {jp.hiring_velocity} [verified]")
        lines.append(f"- **Open Roles:** {jp.total_open_roles} total, {jp.engineering_roles} engineering")

        if jp.team_growth_areas:
            lines.append(f"- **Growth Areas:** {', '.join(jp.team_growth_areas[:5])}")

        # Action based on velocity
        if jp.hiring_velocity == "HIGH":
            lines.append("")
            lines.append("-> ACTION: High growth = budget available. Push for 30-day pilot decision before priorities shift")
        elif jp.hiring_velocity == "MEDIUM":
            lines.append("")
            lines.append("-> ACTION: Stable growth. Standard 60-90 day sales cycle expected")
        else:
            lines.append("")
            lines.append("-> ACTION: Low hiring may signal budget constraints. Emphasize cost efficiency and ROI")
    else:
        lines.append("*Job posting data not available - unable to assess budget health*")
        lines.append("")
        lines.append("-> ACTION: In discovery, ask about recent hires and planned headcount to gauge budget")
    lines.append("")

    # ==========================================================================
    # SECTION 2: RISK & RED FLAGS REPORT
    # ==========================================================================
    lines.append("---")
    lines.append("## Risk & Red Flags Report")
    lines.append("")

    # Deal Blockers (RED)
    lines.append("### Deal Blockers (HIGH Risk)")
    lines.append("")

    blockers_found = False

    # From synthesis blockers
    if synthesis.blockers:
        for blocker in synthesis.blockers[:5]:
            lines.append(f"- **{blocker}**")
            blockers_found = True

    # From regulatory risk
    if research.regulatory_risk:
        rr = research.regulatory_risk
        if rr.risk_level == "HIGH":
            lines.append(f"- **Regulatory Risk Level: HIGH** [verified]")
            blockers_found = True

        for action in rr.enforcement_actions[:2]:
            lines.append(f"- **Enforcement Action:** {action.claim} [verified]")
            blockers_found = True

        for breach in rr.data_breaches[:2]:
            lines.append(f"- **Data Breach History:** {breach.claim} [verified]")
            blockers_found = True

    if blockers_found:
        lines.append("")
        lines.append("-> ACTION: Address these in first meeting. Don't let them surface in procurement review")
    else:
        lines.append("- No critical blockers identified [verified: clean search]")
        lines.append("")
        lines.append("-> ACTION: Clean record is a selling point. Mention fast compliance approval to accelerate deal")
    lines.append("")

    # Concerns (YELLOW)
    lines.append("### Concerns (MEDIUM Risk)")
    lines.append("")

    concerns_found = False

    if research.customer_reviews:
        cr = research.customer_reviews
        if cr.overall_sentiment == "NEGATIVE":
            lines.append(f"- **Customer Sentiment:** Negative reviews indicate potential internal friction")
            lines.append("  -> May face resistance from teams burned by past vendor experiences")
            concerns_found = True

        for challenge in cr.integration_challenges[:2]:
            lines.append(f"- **Integration Challenge:** {challenge} [from reviews]")
            concerns_found = True

    if research.regulatory_risk and research.regulatory_risk.regulatory_exposure:
        for exposure in research.regulatory_risk.regulatory_exposure[:3]:
            lines.append(f"- **Regulatory Exposure:** {exposure}")
            concerns_found = True

    if not concerns_found:
        lines.append("- No significant concerns identified [verified: clean search]")
        lines.append("")
        lines.append("-> ACTION: Low-friction deal. Push for accelerated timeline")
    else:
        lines.append("")
        lines.append("-> ACTION: Prepare responses for each concern before they're raised")
    lines.append("")

    # Competitive Landscape with interpretation
    lines.append("### Competitive Landscape")
    lines.append("")

    competitors_found = False
    if research.customer_reviews and research.customer_reviews.competitor_mentions:
        for mention in research.customer_reviews.competitor_mentions[:5]:
            if isinstance(mention, dict):
                competitor = mention.get("competitor", "Unknown")
                context = mention.get("context", "")
                lines.append(f"- **{competitor}:** {context}")
                competitors_found = True

    if not competitors_found:
        lines.append("- No competitor mentions found in customer reviews [verified: limited data]")
        lines.append("")
        lines.append("-> ACTION: In discovery, ask 'What alternatives are you evaluating?' to map competitive landscape")
    else:
        lines.append("")
        lines.append("-> ACTION: Prepare differentiation talking points for each competitor mentioned")
    lines.append("")

    # ==========================================================================
    # SECTION 3: RELATIONSHIP MAPPING
    # ==========================================================================
    lines.append("---")
    lines.append("## Relationship Mapping")
    lines.append("")

    # Technical Leadership Table
    lines.append("### Technical Leadership")
    lines.append("")

    if research.stakeholders and research.stakeholders.technical_leaders:
        lines.append("| Name | Title | Background | Champion Potential |")
        lines.append("|------|-------|------------|-------------------|")

        for leader in research.stakeholders.technical_leaders[:7]:
            bg = leader.background[:50] + "..." if leader.background and len(leader.background) > 50 else (leader.background or "N/A")
            potential = "HIGH [verified]" if leader.champion_signals else "MEDIUM [inferred]"
            lines.append(f"| {leader.name} | {leader.title} | {bg} | {potential} |")
        lines.append("")
    else:
        lines.append("*Technical leadership not mapped from public sources*")
        lines.append("")
        lines.append("-> ACTION: Request introductions to technical decision-makers in discovery")
        lines.append("")

    # LinkedIn Executives with recent topics
    if research.linkedin_intel and research.linkedin_intel.executives_found:
        lines.append("### LinkedIn Executive Profiles")
        lines.append("")
        for exec in research.linkedin_intel.executives_found[:5]:
            if isinstance(exec, dict):
                name = exec.get("name", "Unknown")
                title = exec.get("title", "")
                topics = exec.get("recent_topics", [])
                lines.append(f"- **{name}**, {title} [verified]")
                if topics:
                    lines.append(f"  - Recent topics: {', '.join(topics[:3])}")
        lines.append("")
        lines.append("-> ACTION: Reference their recent LinkedIn posts in personalized outreach")
        lines.append("")

    # Conference Speakers / Thought Leaders
    if research.stakeholders and research.stakeholders.conference_speakers:
        lines.append("### Conference Speakers & Thought Leaders")
        lines.append("")
        for speaker in research.stakeholders.conference_speakers[:5]:
            lines.append(f"- **{speaker.name}**, {speaker.title} [verified]")
            if speaker.background:
                lines.append(f"  - {speaker.background}")
        lines.append("")
        lines.append("-> ACTION: Reference their public talks in outreach - instant credibility builder")
        lines.append("")

    # GitHub Contributors with interpretation
    if research.stakeholders and research.stakeholders.github_contributors:
        lines.append("### Open Source Contributors")
        lines.append("")
        lines.append(f"GitHub contributors: {', '.join(research.stakeholders.github_contributors[:10])}")
        lines.append("")
        lines.append("-> ACTION: Open source culture signals engineering-led decisions. Lead with technical value")
        lines.append("")
    else:
        # Interpret absence of data
        lines.append("### Engineering Culture")
        lines.append("")
        lines.append("- No public open source presence detected [verified: limited data]")
        lines.append("")
        lines.append("-> ACTION: Likely internal/proprietary dev culture. Expect longer security review process")
        lines.append("")

    # ==========================================================================
    # SECTION 4: TECHNICAL FIT
    # ==========================================================================
    lines.append("---")
    lines.append("## Technical Fit (from Job Postings)")
    lines.append("")

    if research.job_postings:
        jp = research.job_postings

        # Tech Stack from Jobs
        if jp.tech_stack_signals:
            lines.append("### Actual Tech Stack (from job requirements)")
            lines.append("")

            for category, techs in jp.tech_stack_signals.items():
                if techs:
                    lines.append(f"**{category.title()}:** {', '.join(techs[:8])} [verified]")
            lines.append("")
            lines.append("-> ACTION: Reference these specific technologies in demos and proposals")
            lines.append("")

        # Process Tools with action
        if jp.process_tools_mentioned:
            lines.append("### Process Documentation Tools")
            lines.append("")
            lines.append(f"Mentioned in job postings: **{', '.join(jp.process_tools_mentioned)}** [verified]")
            lines.append("")
            lines.append("-> ACTION: Demo Fluency's integration with these tools specifically")
            lines.append("")
        else:
            lines.append("### Process Documentation Tools")
            lines.append("")
            lines.append("- No specific tools mentioned in job postings [verified: limited data]")
            lines.append("")
            lines.append("-> ACTION: In discovery, ask 'How do you currently document processes?' to identify tools")
            lines.append("")

        # Remote Policy
        if jp.remote_policy:
            lines.append(f"### Work Model: {jp.remote_policy}")
            lines.append("")
            if "remote" in jp.remote_policy.lower():
                lines.append("-> ACTION: Emphasize Fluency's async collaboration features for distributed teams")
            lines.append("")
    else:
        lines.append("*Job posting data not available - technical fit assessment limited*")
        lines.append("")
        lines.append("-> ACTION: Research their tech stack via LinkedIn engineering posts or GitHub before call")
        lines.append("")

    # ==========================================================================
    # SECTION 5: RECOMMENDED APPROACH
    # ==========================================================================
    lines.append("---")
    lines.append("## Recommended Approach")
    lines.append("")

    if synthesis.recommended_approach:
        lines.append(synthesis.recommended_approach)
    else:
        lines.append("### Based on Research Findings:")
        lines.append("")

        recommendations = []

        # Champion-based
        if research.stakeholders and research.stakeholders.potential_champions:
            champion = research.stakeholders.potential_champions[0]
            recommendations.append(f"**Lead contact:** {champion.name} ({champion.title}) - highest champion potential")

        # Tech fit based
        if research.job_postings and research.job_postings.process_tools_mentioned:
            tools = research.job_postings.process_tools_mentioned[:2]
            recommendations.append(f"**Demo focus:** Integration with {', '.join(tools)}")

        # Risk mitigation
        if research.regulatory_risk and research.regulatory_risk.risk_level == "HIGH":
            recommendations.append("**Risk mitigation:** Lead with compliance documentation - SOC 2, security architecture")

        # Timing
        if research.job_postings and research.job_postings.hiring_velocity == "HIGH":
            recommendations.append("**Timing:** High growth phase - push for decision within 30 days")

        # Default recommendations
        if not recommendations:
            recommendations = [
                "**Priority:** Request discovery call to identify champions and understand tech stack",
                "**Message:** Lead with process documentation pain points",
                "**Preparation:** Have security and compliance documentation ready"
            ]

        for rec in recommendations:
            lines.append(f"- {rec}")

    lines.append("")

    # ==========================================================================
    # SECTION 6: DISCOVERY QUESTIONS
    # ==========================================================================
    lines.append("---")
    lines.append("## Key Discovery Questions")
    lines.append("")

    questions = []

    # From synthesis
    if synthesis.discovery_questions:
        questions.extend(synthesis.discovery_questions[:5])

    # Add based on research gaps with context
    if not research.stakeholders or not research.stakeholders.potential_champions:
        questions.append("Who owns process documentation and improvement initiatives? *(Need: Champion identification)*")

    if research.job_postings and not research.job_postings.process_tools_mentioned:
        questions.append("What tools do you currently use for process documentation? *(Need: Integration targets)*")

    if research.regulatory_risk and research.regulatory_risk.risk_level in ["HIGH", "MEDIUM"]:
        questions.append("How does your compliance team evaluate new vendors? *(Need: Procurement process clarity)*")

    # Default questions
    if not questions:
        questions = [
            "What are your biggest process documentation challenges? *(Need: Pain validation)*",
            "Who would be the key stakeholders for a pilot? *(Need: Champion + decision-maker mapping)*",
            "What's your typical vendor evaluation timeline? *(Need: Deal velocity estimate)*",
            "Are there any compliance requirements we should be aware of? *(Need: Blocker identification)*"
        ]

    for i, question in enumerate(questions[:8], 1):
        lines.append(f"{i}. {question}")
    lines.append("")

    # ==========================================================================
    # SOURCES & REFERENCES
    # ==========================================================================
    lines.extend(sources.generate_references())

    # Footer
    lines.append("---")
    lines.append("*Generated by Fluency AI Research Agent - Deep Intelligence Module*")
    lines.append("")
    lines.append("**Legend:** [verified]/[strong signal]/[inferred] = claim confidence | 🟢/🟡/🔴 = source quality")

    return "\n".join(lines)
