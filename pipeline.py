"""
Research Pipeline Orchestrator

Runs the 4-stage research pipeline:
1. Discovery - Identify and classify the company
2. Research - Parallel specialized research agents
3. Synthesis - Combine findings into evidence graph
4. Output - Generate stakeholder-specific briefs
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Callable

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from models import (
    CompanyProfile, ResearchResults, SynthesisOutput, ResearchOutput,
    CompanyType
)
from agents import (
    DiscoveryAgent, SecurityAgent, TechStackAgent,
    StrategicAgent, FinancialsAgent, SynthesisAgent,
    # Deep intelligence agents
    JobPostingsAgent, CustomerReviewsAgent, RegulatoryRiskAgent,
    StakeholderIntelAgent, LinkedInIntelAgent
)
from generators import (
    generate_sales_brief, generate_security_brief, generate_product_brief,
    generate_all_pdfs, generate_deployment_checklist, generate_executive_brief
)


console = Console()


class ResearchPipeline:
    """
    Orchestrates the full research pipeline for a company.
    """

    def __init__(self, output_dir: str = "results", verbose: bool = True, resume: bool = False):
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        self.resume = resume
        self.checkpoint = {}
        self.checkpoint_path = None

        # Initialize agents
        self.discovery_agent = DiscoveryAgent()
        self.security_agent = SecurityAgent()
        self.tech_stack_agent = TechStackAgent()
        self.strategic_agent = StrategicAgent()
        self.financials_agent = FinancialsAgent()
        self.synthesis_agent = SynthesisAgent()
        # Deep intelligence agents
        self.job_postings_agent = JobPostingsAgent()
        self.customer_reviews_agent = CustomerReviewsAgent()
        self.regulatory_risk_agent = RegulatoryRiskAgent()
        self.stakeholder_intel_agent = StakeholderIntelAgent()
        self.linkedin_intel_agent = LinkedInIntelAgent()

    def log(self, message: str, style: str = ""):
        """Log a message if verbose mode is on."""
        if self.verbose:
            console.print(message, style=style)

    def _get_checkpoint_path(self, url: str) -> Path:
        """Get checkpoint file path for a URL."""
        from urllib.parse import urlparse
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        domain = parsed.netloc.replace("www.", "")
        safe_name = domain.replace(".", "_")
        return self.output_dir / safe_name / "checkpoint.json"

    def _load_checkpoint(self, url: str) -> dict:
        """Load checkpoint if it exists and resume is enabled."""
        if not self.resume:
            return {}

        checkpoint_path = self._get_checkpoint_path(url)
        if checkpoint_path.exists():
            try:
                data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                self.log(f"  [green]Loaded checkpoint with {len(data.get('completed_agents', []))} completed agents[/green]")
                return data
            except Exception as e:
                self.log(f"  [yellow]Could not load checkpoint: {e}[/yellow]")
        return {}

    def _save_checkpoint(self, url: str, data: dict):
        """Save checkpoint data."""
        checkpoint_path = self._get_checkpoint_path(url)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    async def run(self, url: str, progress_callback: Callable[[str, float], None] | None = None) -> ResearchOutput:
        """
        Run the full research pipeline for a company URL.

        Args:
            url: The company website URL
            progress_callback: Optional callback for progress updates (stage_name, percent)

        Returns:
            ResearchOutput with all findings and generated briefs
        """
        start_time = datetime.now()

        def update_progress(stage: str, percent: float):
            if progress_callback:
                progress_callback(stage, percent)

        # Load checkpoint if resuming
        self.checkpoint = self._load_checkpoint(url)
        self.checkpoint_path = self._get_checkpoint_path(url)

        # Stage 1: Discovery
        self.log("\n[bold blue]Stage 1: Discovery[/bold blue]")
        update_progress("Discovery", 0)

        if "profile" in self.checkpoint:
            self.log("  [green]Using cached discovery data[/green]")
            profile = CompanyProfile(**self.checkpoint["profile"])
        else:
            profile = await self._run_discovery(url)
            # Save checkpoint
            self.checkpoint["profile"] = profile.model_dump()
            self._save_checkpoint(url, self.checkpoint)

        update_progress("Discovery", 100)

        self.log(f"  Company: {profile.name}")
        self.log(f"  Type: {profile.company_type.value}")
        self.log(f"  Industry: {profile.industry}")

        # Small buffer after discovery - agents have retry logic for rate limits
        if "profile" not in self.checkpoint:
            self.log("  [dim]Buffer (5s)...[/dim]")
            await asyncio.sleep(5)

        # Stage 2: Research (Sequential to avoid rate limits)
        self.log("\n[bold blue]Stage 2: Research Agents[/bold blue]")
        update_progress("Research", 0)

        research = await self._run_research(profile, url)
        update_progress("Research", 100)

        self.log(f"  Security findings: {len(research.security.certifications) if research.security else 0} certs")
        self.log(f"  Tech stack findings: {len(research.tech_stack.integrations) if research.tech_stack else 0} integrations")
        self.log(f"  Strategic findings: {len(research.strategic.recent_news) if research.strategic else 0} news items")
        if research.financials:
            self.log(f"  Financial findings: {len(research.financials.risk_factors)} risk factors")
        # Deep intelligence stats
        self.log("\n  [bold cyan]Deep Intelligence:[/bold cyan]")
        if research.job_postings:
            self.log(f"  Job postings: {research.job_postings.total_open_roles} roles, {len(research.job_postings.technologies_mentioned)} technologies")
        if research.customer_reviews:
            self.log(f"  Customer reviews: {research.customer_reviews.total_reviews_analyzed} analyzed, {len(research.customer_reviews.pain_points)} pain points")
        if research.regulatory_risk:
            self.log(f"  Regulatory risk: {research.regulatory_risk.risk_level} ({len(research.regulatory_risk.enforcement_actions)} enforcement actions)")
        if research.stakeholders:
            champions = len(research.stakeholders.potential_champions)
            leaders = len(research.stakeholders.technical_leaders)
            self.log(f"  Stakeholders: {leaders} leaders, {champions} potential champions")
        if research.linkedin_intel:
            execs = len(research.linkedin_intel.executives_found)
            topics = len(research.linkedin_intel.thought_leadership_topics)
            self.log(f"  LinkedIn Intel: {execs} executives, {topics} thought leadership topics")

        # Stage 3: Synthesis
        self.log("\n[bold blue]Stage 3: Synthesis[/bold blue]")
        self.log("  [dim]Buffer (5s)...[/dim]")
        await asyncio.sleep(5)
        update_progress("Synthesis", 0)

        synthesis = await self._run_synthesis(profile, research)
        update_progress("Synthesis", 100)

        self.log(f"  Overall score: {synthesis.deployment_score.overall:.1f}/10")
        self.log(f"  Opportunities: {len(synthesis.opportunities)}")
        self.log(f"  Blockers: {len(synthesis.blockers)}")

        # Stage 4: Output Generation
        self.log("\n[bold blue]Stage 4: Output Generation[/bold blue]")
        update_progress("Output", 0)

        briefs = await self._generate_outputs(profile, synthesis, research)
        update_progress("Output", 100)

        # Calculate duration
        duration = (datetime.now() - start_time).total_seconds()

        # Build final output
        output = ResearchOutput(
            profile=profile,
            research=research,
            synthesis=synthesis,
            sales_brief=briefs["sales"],
            security_brief=briefs["security"],
            product_brief=briefs["product"],
            executive_brief=briefs["executive"],
            generated_at=datetime.now(),
            duration_seconds=duration
        )

        # Save outputs
        await self._save_outputs(output)

        self.log(f"\n[bold green]Pipeline complete in {duration:.1f}s[/bold green]")

        return output

    async def _run_discovery(self, url: str) -> CompanyProfile:
        """Stage 1: Run discovery agent."""
        try:
            return await self.discovery_agent.discover(url)
        except Exception as e:
            self.log(f"  [red]Discovery error: {e}[/red]")
            # Return minimal profile on error with actionable description
            from urllib.parse import urlparse
            parsed = urlparse(url if url.startswith("http") else f"https://{url}")
            domain = parsed.netloc.replace("www.", "")
            name = domain.split(".")[0].title()
            return CompanyProfile(
                name=name,
                domain=domain,
                company_type=CompanyType.PRIVATE_ENTERPRISE,
                industry="Unknown (discovery incomplete)",
                description=f"Discovery phase incomplete for {name}. Company profile data will be gathered from research agents. Recommend manual review of {domain} for accurate classification."
            )

    async def _run_research(self, profile: CompanyProfile, url: str) -> ResearchResults:
        """Stage 2: Run research agents in batches to avoid rate limits."""
        from models import (
            SecurityFindings, TechStackFindings, StrategicFindings, FinancialFindings,
            JobPostingInsights, CustomerReviewInsights, RegulatoryRiskInsights,
            StakeholderIntelligence, LinkedInIntelligence
        )

        # Model classes for deserializing cached results
        model_classes = {
            "security": SecurityFindings,
            "tech_stack": TechStackFindings,
            "strategic": StrategicFindings,
            "financials": FinancialFindings,
            "job_postings": JobPostingInsights,
            "customer_reviews": CustomerReviewInsights,
            "regulatory_risk": RegulatoryRiskInsights,
            "stakeholders": StakeholderIntelligence,
            "linkedin_intel": LinkedInIntelligence,
        }

        # Define agent tasks
        agent_configs = [
            ("security", self.security_agent),
            ("tech_stack", self.tech_stack_agent),
            ("strategic", self.strategic_agent),
            ("job_postings", self.job_postings_agent),
            ("customer_reviews", self.customer_reviews_agent),
            ("regulatory_risk", self.regulatory_risk_agent),
            ("stakeholders", self.stakeholder_intel_agent),
            ("linkedin_intel", self.linkedin_intel_agent),
        ]

        # Add financials for public companies
        if profile.company_type == CompanyType.PUBLIC and profile.ticker:
            agent_configs.append(("financials", self.financials_agent))

        results = {}
        cached_agents = self.checkpoint.get("agents", {})
        completed_count = 0

        # Load any cached results first
        for name in cached_agents:
            if cached_agents[name] is not None and name in model_classes:
                try:
                    results[name] = model_classes[name](**cached_agents[name])
                    completed_count += 1
                except Exception:
                    pass  # Will re-run this agent

        if completed_count > 0:
            self.log(f"  [green]Loaded {completed_count} cached agent results[/green]")

        async def run_agent(name: str, agent) -> tuple[str, any]:
            try:
                self.log(f"  Running {name} agent...")
                result = await agent.research(profile)
                self.log(f"  [green]{name} complete[/green]")
                return name, result
            except Exception as e:
                self.log(f"  [red]{name} error: {e}[/red]")
                return name, None

        # Run agents that aren't cached
        batch_delay = 30  # 30 seconds between agents to avoid rate limits
        agents_to_run = [(name, agent) for name, agent in agent_configs if name not in results]

        if not agents_to_run:
            self.log("  [green]All agents cached, skipping research phase[/green]")
        else:
            self.log(f"  [dim]Running {len(agents_to_run)} agents ({len(results)} cached)[/dim]")

        for i, (name, agent) in enumerate(agents_to_run):
            self.log(f"  [dim]Agent {i+1}/{len(agents_to_run)}[/dim]")

            name, result = await run_agent(name, agent)
            results[name] = result

            # Save checkpoint after each agent
            if "agents" not in self.checkpoint:
                self.checkpoint["agents"] = {}
            self.checkpoint["agents"][name] = result.model_dump() if result else None
            self._save_checkpoint(url, self.checkpoint)

            # Delay before next agent
            if i + 1 < len(agents_to_run):
                self.log(f"  [dim]Rate limit pause ({batch_delay}s)...[/dim]")
                await asyncio.sleep(batch_delay)

        return ResearchResults(
            security=results.get("security"),
            tech_stack=results.get("tech_stack"),
            strategic=results.get("strategic"),
            financials=results.get("financials"),
            # Deep intelligence results
            job_postings=results.get("job_postings"),
            customer_reviews=results.get("customer_reviews"),
            regulatory_risk=results.get("regulatory_risk"),
            stakeholders=results.get("stakeholders"),
            linkedin_intel=results.get("linkedin_intel"),
        )

    async def _run_synthesis(self, profile: CompanyProfile, research: ResearchResults) -> SynthesisOutput:
        """Stage 3: Run synthesis agent."""
        try:
            return await self.synthesis_agent.synthesize(profile, research)
        except Exception as e:
            self.log(f"  [red]Synthesis error: {e}[/red]")
            # Return minimal synthesis on error
            from models import EvidenceGraph, DeploymentScore
            return SynthesisOutput(
                evidence_graph=EvidenceGraph(
                    security_claims=[],
                    technology_claims=[],
                    strategic_claims=[],
                    financial_claims=[]
                ),
                contradictions=[],
                deployment_score=DeploymentScore(
                    security_maturity=5,
                    integration_fit=5,
                    compliance_complexity=5,
                    strategic_alignment=5,
                    deal_complexity=5,
                    overall=5.0,
                    rationale="Could not complete synthesis"
                ),
                opportunities=[],
                blockers=[],
                recommended_approach="",
                discovery_questions=[]
            )

    async def _generate_outputs(
        self,
        profile: CompanyProfile,
        synthesis: SynthesisOutput,
        research: ResearchResults
    ) -> dict[str, str]:
        """Stage 4: Generate all output briefs."""
        # These are synchronous but we wrap them for consistency
        sales = generate_sales_brief(profile, synthesis, research)
        security = generate_security_brief(profile, synthesis, research)
        product = generate_product_brief(profile, synthesis, research)
        executive = generate_executive_brief(profile, synthesis, research)

        return {
            "sales": sales,
            "security": security,
            "product": product,
            "executive": executive
        }

    async def _save_outputs(self, output: ResearchOutput):
        """Save all outputs to the output directory."""
        # Create company-specific directory
        safe_name = output.profile.domain.replace(".", "_")
        company_dir = self.output_dir / safe_name
        company_dir.mkdir(parents=True, exist_ok=True)

        # Save briefs as markdown
        (company_dir / "sales_brief.md").write_text(output.sales_brief, encoding="utf-8")
        (company_dir / "security_brief.md").write_text(output.security_brief, encoding="utf-8")
        (company_dir / "product_brief.md").write_text(output.product_brief, encoding="utf-8")
        (company_dir / "executive_brief.md").write_text(output.executive_brief, encoding="utf-8")

        self.log(f"  Saved markdown briefs to {company_dir}/")

        # Generate PDFs with executive summary
        try:
            # Prepare synthesis data for PDF
            synthesis_data = {
                "deployment_score": output.synthesis.deployment_score.model_dump(),
                "opportunities": output.synthesis.opportunities,
                "blockers": output.synthesis.blockers,
                "recommended_approach": output.synthesis.recommended_approach,
            }
            profile_data = {
                "company_type": output.profile.company_type.value,
                "industry": output.profile.industry,
                "description": output.profile.description,
            }

            pdfs = generate_all_pdfs(
                output_dir=company_dir,
                company_name=output.profile.name,
                sales_brief=output.sales_brief,
                security_brief=output.security_brief,
                product_brief=output.product_brief,
                synthesis_data=synthesis_data,
                profile_data=profile_data
            )
            if pdfs:
                self.log(f"  Generated {len(pdfs)} PDF briefs with executive summary")
        except Exception as e:
            self.log(f"  [yellow]PDF generation skipped: {e}[/yellow]")

        # Generate deployment checklist
        try:
            checklist_path = company_dir / "deployment_checklist.pdf"
            if generate_deployment_checklist(
                profile=output.profile,
                synthesis=output.synthesis,
                research=output.research,
                output_path=str(checklist_path)
            ):
                self.log(f"  Generated deployment readiness checklist")
        except Exception as e:
            self.log(f"  [yellow]Checklist generation skipped: {e}[/yellow]")

        # Save evidence as JSON
        evidence_data = {
            "profile": output.profile.model_dump(),
            "synthesis": {
                "deployment_score": output.synthesis.deployment_score.model_dump(),
                "opportunities": output.synthesis.opportunities,
                "blockers": output.synthesis.blockers,
                "contradictions": output.synthesis.contradictions,
            },
            "evidence_graph": {
                "security": [c.model_dump() for c in output.synthesis.evidence_graph.security_claims],
                "technology": [c.model_dump() for c in output.synthesis.evidence_graph.technology_claims],
                "strategic": [c.model_dump() for c in output.synthesis.evidence_graph.strategic_claims],
                "financial": [c.model_dump() for c in output.synthesis.evidence_graph.financial_claims],
            },
            "metadata": {
                "generated_at": output.generated_at.isoformat(),
                "duration_seconds": output.duration_seconds
            }
        }

        (company_dir / "evidence.json").write_text(
            json.dumps(evidence_data, indent=2, default=str),
            encoding="utf-8"
        )

        self.log(f"  Saved evidence.json")

        # Save raw research data
        research_data = {
            "security": output.research.security.model_dump() if output.research.security else None,
            "tech_stack": output.research.tech_stack.model_dump() if output.research.tech_stack else None,
            "strategic": output.research.strategic.model_dump() if output.research.strategic else None,
            "financials": output.research.financials.model_dump() if output.research.financials else None,
            "job_postings": output.research.job_postings.model_dump() if output.research.job_postings else None,
            "customer_reviews": output.research.customer_reviews.model_dump() if output.research.customer_reviews else None,
            "regulatory_risk": output.research.regulatory_risk.model_dump() if output.research.regulatory_risk else None,
            "stakeholders": output.research.stakeholders.model_dump() if output.research.stakeholders else None,
            "linkedin_intel": output.research.linkedin_intel.model_dump() if output.research.linkedin_intel else None,
        }

        (company_dir / "raw_research.json").write_text(
            json.dumps(research_data, indent=2, default=str),
            encoding="utf-8"
        )

        self.log(f"  Saved raw_research.json")


async def run_pipeline(url: str, output_dir: str = "results", verbose: bool = True) -> ResearchOutput:
    """
    Convenience function to run the pipeline.

    Args:
        url: Company website URL
        output_dir: Directory to save outputs
        verbose: Whether to print progress

    Returns:
        ResearchOutput with all findings
    """
    pipeline = ResearchPipeline(output_dir=output_dir, verbose=verbose)
    return await pipeline.run(url)


if __name__ == "__main__":
    # Quick test
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = "stripe.com"

    result = asyncio.run(run_pipeline(url))
    console.print(Panel(f"[bold green]Research complete for {result.profile.name}[/bold green]"))
