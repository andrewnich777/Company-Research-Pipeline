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
import time
from pathlib import Path
from datetime import datetime
from typing import Callable
from urllib.parse import urlparse

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

from logger import get_logger
from config import get_config

logger = get_logger(__name__)

from models import (
    CompanyProfile, ResearchResults, SynthesisOutput, ResearchOutput,
    CompanyType
)
from agents import (
    DiscoveryAgent, SecurityAgent, TechStackAgent,
    StrategicAgent, FinancialsAgent, SynthesisAgent,
    # Deep intelligence agents
    JobPostingsAgent, CustomerReviewsAgent, RegulatoryRiskAgent,
    StakeholderIntelAgent, LinkedInIntelAgent,
    # Deployment success agents
    OperationalCultureAgent, ShadowITAgent, LocalRegulationsAgent,
    ProcurementAgent, ImplementationRiskAgent,
    # Opus-powered generators
    ExecutiveBriefAgent, BriefRefinerAgent
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

        # Search monitoring - tracks web_search API usage
        self.search_stats = {
            "total_searches": 0,
            "total_fetches": 0,
            "by_agent": {},
            "discovery_searches": 0,  # Searches done in URL bank building
            "research_searches": 0,   # Searches done by research agents (ideally low)
        }

        # Search query deduplication - tracks queries to avoid repeats
        self.issued_queries: set[str] = set()

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
        # Deployment success agents
        self.operational_culture_agent = OperationalCultureAgent()
        self.shadow_it_agent = ShadowITAgent()
        self.local_regulations_agent = LocalRegulationsAgent()
        self.procurement_agent = ProcurementAgent()
        self.implementation_risk_agent = ImplementationRiskAgent()
        # Opus-powered brief generation
        self.executive_brief_agent = ExecutiveBriefAgent()
        self.brief_refiner_agent = BriefRefinerAgent()

    def log(self, message: str, style: str = ""):
        """Log a message if verbose mode is on."""
        if self.verbose:
            console.print(message, style=style)

    def _track_agent_searches(self, agent_name: str, agent):
        """Track search statistics for an agent after it runs."""
        stats = agent.search_stats
        self.search_stats["by_agent"][agent_name] = {
            "searches": stats["web_search_count"],
            "fetches": stats["web_fetch_count"],
            "queries": stats["search_queries"],
        }
        self.search_stats["total_searches"] += stats["web_search_count"]
        self.search_stats["total_fetches"] += stats["web_fetch_count"]

        if agent_name == "Discovery":
            self.search_stats["discovery_searches"] = stats["web_search_count"]
        else:
            self.search_stats["research_searches"] += stats["web_search_count"]

        # Add queries to global dedup set (normalized)
        for query in stats["search_queries"]:
            normalized = self._normalize_query(query)
            self.issued_queries.add(normalized)

    def _normalize_query(self, query: str) -> str:
        """Normalize a query for deduplication comparison."""
        # Lowercase and sort words for fuzzy matching
        return " ".join(sorted(query.lower().split()))

    def _get_search_context(self) -> str:
        """Get context about already-searched queries for agents to avoid repeats."""
        if not self.issued_queries:
            return ""
        # Return a sample of issued queries (limit to avoid prompt bloat)
        sample = list(self.issued_queries)[:15]
        return f"\n\n## PREVIOUSLY SEARCHED (avoid repeating these queries):\n{', '.join(sample)}"

    def _log_search_summary(self):
        """Log a summary of search API usage."""
        self.log("\n[bold yellow]Search API Usage Summary[/bold yellow]")
        self.log(f"  Total web_search calls: {self.search_stats['total_searches']}")
        self.log(f"  Total web_fetch calls: {self.search_stats['total_fetches']}")
        self.log(f"  Discovery searches (URL bank building): {self.search_stats['discovery_searches']}")
        self.log(f"  Research agent searches (should be low): {self.search_stats['research_searches']}")

        if self.search_stats["by_agent"]:
            self.log("\n  By Agent:")
            for agent_name, stats in sorted(self.search_stats["by_agent"].items()):
                search_indicator = "[green]0[/green]" if stats["searches"] == 0 else f"[yellow]{stats['searches']}[/yellow]"
                self.log(f"    {agent_name}: {search_indicator} searches, {stats['fetches']} fetches")

        # Calculate savings estimate
        # Baseline: ~3 searches per research agent without URL bank
        baseline_searches = 3 * 13  # 13 research agents × 3 searches each
        actual_research_searches = self.search_stats["research_searches"]
        savings = baseline_searches - actual_research_searches

        if savings > 0:
            self.log(f"\n  [green]Estimated savings: ~{savings} searches avoided via URL bank[/green]")
        else:
            self.log(f"\n  [yellow]URL bank may need tuning - research agents still searching[/yellow]")

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
                completed_count = len(data.get('completed_agents', []))
                self.log(f"  [green]Loaded checkpoint with {completed_count} completed agents[/green]")
                logger.info(f"Loaded checkpoint from {checkpoint_path} with {completed_count} completed agents")
                return data
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON in checkpoint file: {e}"
                self.log(f"  [yellow]Could not load checkpoint: {error_msg}[/yellow]")
                logger.warning(f"Checkpoint load failed for {url}: {error_msg}")
            except IOError as e:
                error_msg = f"Could not read checkpoint file: {e}"
                self.log(f"  [yellow]Could not load checkpoint: {error_msg}[/yellow]")
                logger.warning(f"Checkpoint load failed for {url}: {error_msg}")
            except Exception as e:
                error_msg = f"Unexpected error: {e}"
                self.log(f"  [yellow]Could not load checkpoint: {error_msg}[/yellow]")
                logger.exception(f"Unexpected error loading checkpoint for {url}")
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
            # Track discovery search stats
            self._track_agent_searches("Discovery", self.discovery_agent)
            # Save checkpoint
            self.checkpoint["profile"] = profile.model_dump()
            self._save_checkpoint(url, self.checkpoint)

        update_progress("Discovery", 100)

        self.log(f"  Company: {profile.name}")
        self.log(f"  Type: {profile.company_type.value}")
        self.log(f"  Industry: {profile.industry}")

        # Log URL bank stats
        if profile.url_bank:
            url_count = sum([
                1 if profile.url_bank.trust_center else 0,
                1 if profile.url_bank.linkedin_company else 0,
                1 if profile.url_bank.g2_page else 0,
                1 if profile.url_bank.careers_page else 0,
                len(profile.url_bank.news_articles),
                len(profile.url_bank.linkedin_executives),
                len(profile.url_bank.job_board_urls),
            ])
            self.log(f"  [cyan]URL Bank: {url_count} URLs discovered for downstream agents[/cyan]")

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

        # Deployment success stats
        self.log("\n  [bold magenta]Deployment Success Intel:[/bold magenta]")
        if research.operational_culture:
            self.log(f"  Operational Culture: {research.operational_culture.culture_type} ({len(research.operational_culture.methodology_signals)} signals)")
        if research.shadow_it:
            self.log(f"  Shadow IT: {research.shadow_it.tech_debt_level} tech debt ({len(research.shadow_it.legacy_systems_detected)} legacy systems)")
        if research.local_regulations:
            self.log(f"  Local Regulations: {len(research.local_regulations.operating_regions)} regions, {len(research.local_regulations.applicable_regulations)} regulations")
        if research.procurement:
            self.log(f"  Procurement: {research.procurement.procurement_complexity} complexity ({research.procurement.estimated_approval_timeline})")
        if research.implementation_risk:
            self.log(f"  Implementation Risk: {research.implementation_risk.risk_level} ({research.implementation_risk.recommended_approach} approach)")

        # Stage 3: Synthesis
        self.log("\n[bold blue]Stage 3: Synthesis[/bold blue]")
        update_progress("Synthesis", 0)

        # Check if synthesis is cached
        if "synthesis" in self.checkpoint:
            self.log("  [green]Using cached synthesis data[/green]")
            from models import EvidenceGraph, DeploymentScore
            synth_data = self.checkpoint["synthesis"]
            synthesis = SynthesisOutput(
                evidence_graph=self._parse_cached_evidence_graph(synth_data.get("evidence_graph", {})),
                contradictions=synth_data.get("contradictions", []),
                deployment_score=DeploymentScore(**synth_data.get("deployment_score", {})),
                opportunities=synth_data.get("opportunities", []),
                blockers=synth_data.get("blockers", []),
                recommended_approach=synth_data.get("recommended_approach", ""),
                discovery_questions=synth_data.get("discovery_questions", [])
            )
        else:
            self.log("  [dim]Buffer (5s)...[/dim]")
            await asyncio.sleep(5)
            synthesis = await self._run_synthesis(profile, research)
            # Cache synthesis result
            self.checkpoint["synthesis"] = {
                "evidence_graph": self._serialize_evidence_graph(synthesis.evidence_graph),
                "contradictions": synthesis.contradictions,
                "deployment_score": synthesis.deployment_score.model_dump(),
                "opportunities": synthesis.opportunities,
                "blockers": synthesis.blockers,
                "recommended_approach": synthesis.recommended_approach,
                "discovery_questions": synthesis.discovery_questions
            }
            self._save_checkpoint(url, self.checkpoint)

        update_progress("Synthesis", 100)

        self.log(f"  Overall score: {synthesis.deployment_score.overall:.1f}/10")
        self.log(f"  Opportunities: {len(synthesis.opportunities)}")
        self.log(f"  Blockers: {len(synthesis.blockers)}")

        # Stage 4: Output Generation
        self.log("\n[bold blue]Stage 4: Output Generation[/bold blue]")
        update_progress("Output", 0)

        briefs = await self._generate_outputs(profile, synthesis, research)
        # Save checkpoint with briefs if newly generated
        if "briefs" in self.checkpoint:
            self._save_checkpoint(url, self.checkpoint)
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

        # Log search API usage summary
        self._log_search_summary()

        self.log(f"\n[bold green]Pipeline complete in {duration:.1f}s[/bold green]")

        return output

    async def resynthesize(self, url: str, progress_callback: Callable[[str, float], None] | None = None) -> ResearchOutput:
        """
        Rerun only synthesis and output generation using cached research data.

        This is useful when you want to regenerate briefs without making new API calls
        for the research agents. Requires existing checkpoint data.

        Args:
            url: The company website URL (used to locate checkpoint)
            progress_callback: Optional callback for progress updates

        Returns:
            ResearchOutput with regenerated briefs
        """
        start_time = datetime.now()

        def update_progress(stage: str, percent: float):
            if progress_callback:
                progress_callback(stage, percent)

        # Force load checkpoint
        self.checkpoint_path = self._get_checkpoint_path(url)
        if not self.checkpoint_path.exists():
            raise ValueError(f"No checkpoint found for {url}. Run full research first.")

        self.checkpoint = json.loads(self.checkpoint_path.read_text(encoding="utf-8"))

        # Verify we have the required cached data
        if "profile" not in self.checkpoint:
            raise ValueError("Checkpoint missing profile data. Run full research first.")
        if "agents" not in self.checkpoint:
            raise ValueError("Checkpoint missing research data. Run full research first.")

        self.log("\n[bold blue]Resynthesize Mode[/bold blue]")
        self.log("  Using cached discovery and research data")
        self.log("  Regenerating synthesis and outputs only\n")

        # Load profile from cache
        profile = CompanyProfile(**self.checkpoint["profile"])
        self.log(f"  Company: {profile.name}")
        self.log(f"  Type: {profile.company_type.value}")
        update_progress("Load Cache", 100)

        # Load research from cache
        from models import (
            SecurityFindings, TechStackFindings, StrategicFindings, FinancialFindings,
            JobPostingInsights, CustomerReviewInsights, RegulatoryRiskInsights,
            StakeholderIntelligence, LinkedInIntelligence,
            LocalRegulationsInsights, ProcurementInsights, ImplementationRiskInsights,
            OperationalCultureInsights, ShadowITInsights
        )

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
            "local_regulations": LocalRegulationsInsights,
            "procurement": ProcurementInsights,
            "implementation_risk": ImplementationRiskInsights,
            "operational_culture": OperationalCultureInsights,
            "shadow_it": ShadowITInsights,
        }

        results = {}
        cached_agents = self.checkpoint.get("agents", {})
        for name, data in cached_agents.items():
            if data is not None and name in model_classes:
                try:
                    results[name] = model_classes[name](**data)
                except Exception as e:
                    logger.warning(f"Could not load cached {name}: {e}")

        self.log(f"  Loaded {len(results)} cached agent results")

        research = ResearchResults(
            security=results.get("security"),
            tech_stack=results.get("tech_stack"),
            strategic=results.get("strategic"),
            financials=results.get("financials"),
            job_postings=results.get("job_postings"),
            customer_reviews=results.get("customer_reviews"),
            regulatory_risk=results.get("regulatory_risk"),
            stakeholders=results.get("stakeholders"),
            linkedin_intel=results.get("linkedin_intel"),
            local_regulations=results.get("local_regulations"),
            procurement=results.get("procurement"),
            implementation_risk=results.get("implementation_risk"),
            operational_culture=results.get("operational_culture"),
            shadow_it=results.get("shadow_it"),
        )

        # Clear synthesis and briefs from checkpoint to force regeneration
        if "synthesis" in self.checkpoint:
            del self.checkpoint["synthesis"]
        if "briefs" in self.checkpoint:
            del self.checkpoint["briefs"]
        self._save_checkpoint(url, self.checkpoint)

        # Stage 3: Synthesis (regenerate)
        self.log("\n[bold blue]Stage 3: Synthesis (Regenerating)[/bold blue]")
        update_progress("Synthesis", 0)

        self.log("  [dim]Buffer (5s)...[/dim]")
        await asyncio.sleep(5)
        synthesis = await self._run_synthesis(profile, research)

        # Cache synthesis result
        self.checkpoint["synthesis"] = {
            "evidence_graph": self._serialize_evidence_graph(synthesis.evidence_graph),
            "contradictions": synthesis.contradictions,
            "deployment_score": synthesis.deployment_score.model_dump(),
            "opportunities": synthesis.opportunities,
            "blockers": synthesis.blockers,
            "recommended_approach": synthesis.recommended_approach,
            "discovery_questions": synthesis.discovery_questions
        }
        self._save_checkpoint(url, self.checkpoint)

        update_progress("Synthesis", 100)

        self.log(f"  Overall score: {synthesis.deployment_score.overall:.1f}/10")
        self.log(f"  Opportunities: {len(synthesis.opportunities)}")
        self.log(f"  Blockers: {len(synthesis.blockers)}")

        # Stage 4: Output Generation (regenerate with validation)
        self.log("\n[bold blue]Stage 4: Output Generation (Regenerating)[/bold blue]")
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

        self.log(f"\n[bold green]Resynthesize complete in {duration:.1f}s[/bold green]")

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
            StakeholderIntelligence, LinkedInIntelligence,
            # Deployment success models
            LocalRegulationsInsights, ProcurementInsights, ImplementationRiskInsights,
            OperationalCultureInsights, ShadowITInsights
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
            # Deployment success models
            "local_regulations": LocalRegulationsInsights,
            "procurement": ProcurementInsights,
            "implementation_risk": ImplementationRiskInsights,
            "operational_culture": OperationalCultureInsights,
            "shadow_it": ShadowITInsights,
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
            # Deployment success agents
            ("operational_culture", self.operational_culture_agent),
            ("shadow_it", self.shadow_it_agent),
            ("local_regulations", self.local_regulations_agent),
            ("procurement", self.procurement_agent),
            ("implementation_risk", self.implementation_risk_agent),
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
                except (TypeError, ValueError) as e:
                    # Validation error - data doesn't match model schema
                    logger.warning(f"Cached {name} agent data invalid, will re-run: {e}")
                except Exception as e:
                    # Unexpected error - log and re-run
                    logger.exception(f"Unexpected error loading cached {name} agent data, will re-run")

        if completed_count > 0:
            self.log(f"  [green]Loaded {completed_count} cached agent results[/green]")

        async def run_agent(name: str, agent) -> tuple[str, any]:
            try:
                self.log(f"  Running {name} agent...")
                # Pass search context to agent to avoid duplicate queries
                agent._search_context = self._get_search_context()
                result = await agent.research(profile)
                # Track search stats for monitoring
                self._track_agent_searches(name, agent)
                searches = agent.search_stats["web_search_count"]
                search_note = f" (0 searches)" if searches == 0 else f" ({searches} searches)"
                self.log(f"  [green]{name} complete[/green]{search_note}")
                return name, result
            except Exception as e:
                self.log(f"  [red]{name} error: {e}[/red]")
                return name, None

        # Run agents that aren't cached
        # Use 60s delay between agents to allow rate limit bucket to recover
        # Combined with 30s buffer after rate limit recovery in base agent
        batch_delay = 60  # Buffer between agents to prevent rate limit escalation
        agents_to_run = [(name, agent) for name, agent in agent_configs if name not in results]

        if not agents_to_run:
            self.log("  [green]All agents cached, skipping research phase[/green]")
        else:
            self.log(f"  [dim]Running {len(agents_to_run)} agents ({len(results)} cached)[/dim]")

        stage_start = time.time()
        agent_times = []

        for i, (name, agent) in enumerate(agents_to_run):
            # Calculate progress
            pct = int((i / len(agents_to_run)) * 100)
            elapsed = time.time() - stage_start

            # Estimate remaining time
            if agent_times:
                avg_time = sum(agent_times) / len(agent_times)
                remaining_agents = len(agents_to_run) - i
                eta_seconds = int(avg_time * remaining_agents)
                eta_str = f"~{eta_seconds // 60}m {eta_seconds % 60}s remaining"
            else:
                eta_str = "calculating..."

            self.log(f"  [dim]Agent {i+1}/{len(agents_to_run)} ({pct}%) - {eta_str}[/dim]")

            agent_start = time.time()
            name, result = await run_agent(name, agent)
            agent_times.append(time.time() - agent_start + batch_delay)  # Include delay in estimate

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

        # Final progress
        total_time = time.time() - stage_start
        self.log(f"  [green]Research complete in {int(total_time)}s[/green]")

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
            # Deployment success results
            local_regulations=results.get("local_regulations"),
            procurement=results.get("procurement"),
            implementation_risk=results.get("implementation_risk"),
            operational_culture=results.get("operational_culture"),
            shadow_it=results.get("shadow_it"),
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

    def _serialize_evidence_graph(self, graph) -> dict:
        """Serialize evidence graph for caching."""
        return {
            "security": [c.model_dump() for c in graph.security_claims],
            "technology": [c.model_dump() for c in graph.technology_claims],
            "strategic": [c.model_dump() for c in graph.strategic_claims],
            "financial": [c.model_dump() for c in graph.financial_claims],
            "hiring": [c.model_dump() for c in getattr(graph, 'hiring_claims', [])],
            "customer_sentiment": [c.model_dump() for c in getattr(graph, 'customer_sentiment_claims', [])],
            "regulatory": [c.model_dump() for c in getattr(graph, 'regulatory_claims', [])],
            "stakeholder": [c.model_dump() for c in getattr(graph, 'stakeholder_claims', [])],
        }

    def _parse_cached_evidence_graph(self, data: dict):
        """Parse cached evidence graph data."""
        from models import EvidenceGraph, Claim, Evidence, Confidence, SourceTier

        def parse_claims(items: list) -> list:
            claims = []
            for item in items:
                confidence = Confidence.MEDIUM
                try:
                    confidence = Confidence(item.get("confidence", "MEDIUM"))
                except ValueError:
                    pass

                evidence = []
                for ev in item.get("evidence", []):
                    source_tier = SourceTier.TIER_2
                    try:
                        source_tier = SourceTier(ev.get("source_tier", "TIER_2"))
                    except ValueError:
                        pass
                    evidence.append(Evidence(
                        url=ev.get("url", ""),
                        quote=ev.get("quote", ""),
                        source_type=ev.get("source_type", "synthesis"),
                        source_tier=source_tier
                    ))

                claims.append(Claim(
                    claim=item.get("claim", ""),
                    category=item.get("category", ""),
                    confidence=confidence,
                    evidence=evidence
                ))
            return claims

        return EvidenceGraph(
            security_claims=parse_claims(data.get("security", [])),
            technology_claims=parse_claims(data.get("technology", [])),
            strategic_claims=parse_claims(data.get("strategic", [])),
            financial_claims=parse_claims(data.get("financial", [])),
            hiring_claims=parse_claims(data.get("hiring", [])),
            customer_sentiment_claims=parse_claims(data.get("customer_sentiment", [])),
            regulatory_claims=parse_claims(data.get("regulatory", [])),
            stakeholder_claims=parse_claims(data.get("stakeholder", [])),
        )

    def _validate_brief(self, name: str, content: str) -> list[str]:
        """Validate a brief for common issues. Returns list of warnings."""
        warnings = []

        if not content or len(content) < 100:
            warnings.append(f"{name}: Brief is too short or empty")

        # Check for placeholder/error text
        error_patterns = [
            "Could not complete",
            "Error:",
            "None found",
            "[object Object]",
            "undefined",
            "NaN",
        ]
        for pattern in error_patterns:
            if pattern in content:
                warnings.append(f"{name}: Contains potential error text '{pattern}'")

        # Check for required sections based on brief type
        if name == "sales" and "## " not in content:
            warnings.append(f"{name}: Missing section headers")
        if name == "executive" and "Score" not in content:
            warnings.append(f"{name}: Missing deployment score section")

        # Check for encoding issues
        try:
            content.encode('utf-8')
        except UnicodeEncodeError as e:
            warnings.append(f"{name}: Contains invalid Unicode characters")

        return warnings

    def _validate_briefs(self, briefs: dict[str, str]) -> bool:
        """Validate all briefs and log warnings. Returns True if all valid."""
        all_warnings = []
        for name, content in briefs.items():
            warnings = self._validate_brief(name, content)
            all_warnings.extend(warnings)

        if all_warnings:
            self.log("  [yellow]Brief Validation Warnings:[/yellow]")
            for warning in all_warnings:
                self.log(f"    [yellow]- {warning}[/yellow]")
            return False
        else:
            self.log("  [green]Brief validation passed[/green]")
            return True

    async def _generate_outputs(
        self,
        profile: CompanyProfile,
        synthesis: SynthesisOutput,
        research: ResearchResults
    ) -> dict[str, str]:
        """Stage 4: Generate all output briefs."""
        # Check if briefs are cached
        if "briefs" in self.checkpoint:
            self.log("  [green]Using cached briefs[/green]")
            return self.checkpoint["briefs"]

        # Run Opus-powered Brief Refiner Agent for audience-specific refinements
        self.log("  Running Brief Refiner Agent (Opus)...")
        brief_refinements = None
        try:
            brief_refinements = await self.brief_refiner_agent.generate_refinements(
                profile, synthesis, research
            )
            # Track search stats (should be 0 - pure reasoning)
            self._track_agent_searches("BriefRefiner", self.brief_refiner_agent)
            sales_count = len(brief_refinements.get("sales_refinements", {}).get("talking_points", []))
            security_count = len(brief_refinements.get("security_refinements", {}).get("compliance_gaps", []))
            product_count = len(brief_refinements.get("product_refinements", {}).get("deployment_risks", []))
            self.log(f"  [green]Brief Refiner Agent complete[/green] ({sales_count} talking points, {security_count} compliance gaps, {product_count} deployment risks)")
        except Exception as e:
            self.log(f"  [yellow]Brief Refiner Agent error: {e}[/yellow]")
            self.log(f"  [yellow]Falling back to template-based generation[/yellow]")
            brief_refinements = None

        # Generate briefs with AI refinements
        sales = generate_sales_brief(
            profile, synthesis, research,
            ai_refinements=brief_refinements.get("sales_refinements") if brief_refinements else None
        )
        security = generate_security_brief(
            profile, synthesis, research,
            ai_refinements=brief_refinements.get("security_refinements") if brief_refinements else None
        )
        product = generate_product_brief(
            profile, synthesis, research,
            ai_refinements=brief_refinements.get("product_refinements") if brief_refinements else None
        )

        # Run Opus-powered Executive Brief Agent for high-value insights
        self.log("  Running Executive Brief Agent (Opus)...")
        try:
            ai_intelligence = await self.executive_brief_agent.generate_intelligence(
                profile, synthesis, research
            )
            # Track search stats (should be 0 - pure reasoning)
            self._track_agent_searches("ExecutiveBrief", self.executive_brief_agent)
            wow_count = len(ai_intelligence.get("wow_findings", []))
            insight_count = len(ai_intelligence.get("strategic_insights", []))
            self.log(f"  [green]Executive Brief Agent complete[/green] ({wow_count} wow findings, {insight_count} strategic insights)")
        except Exception as e:
            self.log(f"  [yellow]Executive Brief Agent error: {e}[/yellow]")
            self.log(f"  [yellow]Falling back to template-based generation[/yellow]")
            ai_intelligence = None

        executive = generate_executive_brief(profile, synthesis, research, ai_intelligence)

        briefs = {
            "sales": sales,
            "security": security,
            "product": product,
            "executive": executive
        }

        # Validate briefs before caching
        self._validate_briefs(briefs)

        # Cache briefs
        self.checkpoint["briefs"] = briefs
        # Note: Checkpoint is saved in _save_outputs after file writes

        return briefs

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
                executive_brief=output.executive_brief,
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
            # Deployment success data
            "local_regulations": output.research.local_regulations.model_dump() if output.research.local_regulations else None,
            "procurement": output.research.procurement.model_dump() if output.research.procurement else None,
            "implementation_risk": output.research.implementation_risk.model_dump() if output.research.implementation_risk else None,
            "operational_culture": output.research.operational_culture.model_dump() if output.research.operational_culture else None,
            "shadow_it": output.research.shadow_it.model_dump() if output.research.shadow_it else None,
        }

        (company_dir / "raw_research.json").write_text(
            json.dumps(research_data, indent=2, default=str),
            encoding="utf-8"
        )

        self.log(f"  Saved raw_research.json")

        # Save search monitoring stats
        search_stats_data = {
            "total_web_searches": self.search_stats["total_searches"],
            "total_web_fetches": self.search_stats["total_fetches"],
            "discovery_searches": self.search_stats["discovery_searches"],
            "research_agent_searches": self.search_stats["research_searches"],
            "by_agent": self.search_stats["by_agent"],
            "url_bank_urls_discovered": sum([
                1 if output.profile.url_bank.trust_center else 0,
                1 if output.profile.url_bank.linkedin_company else 0,
                1 if output.profile.url_bank.g2_page else 0,
                len(output.profile.url_bank.news_articles),
                len(output.profile.url_bank.linkedin_executives),
            ]) if output.profile.url_bank else 0,
        }

        (company_dir / "search_stats.json").write_text(
            json.dumps(search_stats_data, indent=2, default=str),
            encoding="utf-8"
        )

        self.log(f"  Saved search_stats.json")


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
