#!/usr/bin/env python3
"""
Fluency AI Deployment Research Agent

A multi-agent system that automates enterprise deployment research
for B2B SaaS sales preparation.

Usage:
    python main.py stripe.com
    python main.py https://aon.com --output results/
    python main.py stripe.com --quiet
"""

import argparse
import asyncio
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Load .env file before other imports
from config import get_config

from agents import set_api_key
from pipeline import ResearchPipeline


# Use legacy_windows mode for better Windows compatibility
console = Console(force_terminal=True, legacy_windows=True)


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="fluency-research",
        description="Fluency AI Deployment Research Agent - Automated enterprise research for sales preparation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s stripe.com
    %(prog)s https://aon.com --output ./research-results
    %(prog)s vanta.com --quiet
    %(prog)s ramp.com --resynthesize  # Rerun synthesis only with cached data

The agent will:
  1. Discover and classify the company (PUBLIC/PRIVATE/STARTUP)
  2. Research security posture, tech stack, strategic context
  3. Synthesize findings into evidence-backed intelligence
  4. Generate stakeholder-specific briefs (Sales, Security, Product)

Output files are saved to the --output directory:
  - sales_brief.md     Sales team talking points and discovery questions
  - security_brief.md  Security posture and compliance assessment
  - product_brief.md   Integration opportunities and technical fit
  - evidence.json      Structured evidence graph
  - raw_research.json  Raw findings from each agent
        """
    )

    parser.add_argument(
        "url",
        help="Company website URL (e.g., 'stripe.com' or 'https://aon.com')"
    )

    parser.add_argument(
        "-o", "--output",
        default="results",
        help="Output directory for generated briefs (default: results/)"
    )

    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress progress output"
    )

    parser.add_argument(
        "--show-score",
        action="store_true",
        help="Display deployment readiness score after completion"
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )

    parser.add_argument(
        "--api-key",
        help="Anthropic API key (can also use ANTHROPIC_API_KEY env var)"
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from checkpoint if available (skips completed agents)"
    )

    parser.add_argument(
        "--resynthesize",
        action="store_true",
        help="Rerun only synthesis and output generation using cached research data (no new API calls for research)"
    )

    return parser


def display_summary(result, show_score: bool = False):
    """Display a summary of the research results."""
    profile = result.profile
    synthesis = result.synthesis

    # Company info panel
    info_lines = [
        f"[bold]{profile.name}[/bold]",
        f"Domain: {profile.domain}",
        f"Type: {profile.company_type.value}",
        f"Industry: {profile.industry}",
    ]
    if profile.hq_location:
        info_lines.append(f"HQ: {profile.hq_location}")
    if profile.employee_count:
        info_lines.append(f"Employees: {profile.employee_count}")
    if profile.ticker:
        info_lines.append(f"Ticker: {profile.ticker}")

    console.print(Panel(
        "\n".join(info_lines),
        title="Company Profile",
        border_style="blue"
    ))

    if show_score:
        # Deployment score table
        score = synthesis.deployment_score
        synthesis_failed = "Could not complete" in score.rationale or score.rationale == ""

        table = Table(title="Deployment Readiness Score")
        table.add_column("Factor", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Weight", justify="right", style="dim")

        if synthesis_failed:
            # Show N/A when synthesis failed instead of misleading "5/10"
            table.add_row("Security Maturity", "[dim]--[/dim]", "25%")
            table.add_row("Integration Fit", "[dim]--[/dim]", "25%")
            table.add_row("Compliance Complexity", "[dim]--[/dim]", "20%")
            table.add_row("Strategic Alignment", "[dim]--[/dim]", "15%")
            table.add_row("Deal Complexity", "[dim]--[/dim]", "15%")
            table.add_row("", "", "")
            table.add_row("[bold]Overall[/bold]", "[yellow]Incomplete[/yellow]", "")
        else:
            table.add_row("Security Maturity", f"{score.security_maturity}/10", "25%")
            table.add_row("Integration Fit", f"{score.integration_fit}/10", "25%")
            table.add_row("Compliance Complexity", f"{score.compliance_complexity}/10", "20%")
            table.add_row("Strategic Alignment", f"{score.strategic_alignment}/10", "15%")
            table.add_row("Deal Complexity", f"{score.deal_complexity}/10", "15%")
            table.add_row("", "", "")
            table.add_row("[bold]Overall[/bold]", f"[bold]{score.overall:.1f}/10[/bold]", "")

        console.print(table)
        if synthesis_failed:
            console.print("\n[yellow]Synthesis incomplete - scores unavailable. Run with --resume after adding credits.[/yellow]\n")
        else:
            console.print(f"\n[dim]Rationale: {score.rationale}[/dim]\n")

    # Opportunities and blockers
    if synthesis.opportunities:
        console.print("[bold green]Opportunities:[/bold green]")
        for opp in synthesis.opportunities[:5]:
            console.print(f"  [green]+[/green] {opp}")
        console.print()

    if synthesis.blockers:
        console.print("[bold red]Potential Blockers:[/bold red]")
        for blocker in synthesis.blockers[:5]:
            console.print(f"  [red]-[/red] {blocker}")
        console.print()

    # Output files
    safe_name = profile.domain.replace(".", "_")
    output_path = Path("results") / safe_name

    console.print(f"[bold]Output files saved to:[/bold] {output_path}/")
    console.print(f"  - sales_brief.md")
    console.print(f"  - security_brief.md")
    console.print(f"  - product_brief.md")
    console.print(f"  - evidence.json")


async def main_async(args: argparse.Namespace) -> int:
    """Async main function."""
    verbose = not args.quiet

    # Set API key - prefer command line arg, then config/env
    config = get_config()
    api_key = args.api_key or config.api_key

    if api_key:
        set_api_key(api_key)
    else:
        console.print("[bold red]Error:[/bold red] No API key found.")
        console.print("Set ANTHROPIC_API_KEY in .env file or pass --api-key argument.")
        return 1

    if verbose:
        console.print(Panel.fit(
            "[bold blue]Fluency AI Research Agent[/bold blue]\n"
            "Automated Enterprise Deployment Research",
            border_style="blue"
        ))
        console.print(f"\nResearching: [bold]{args.url}[/bold]\n")

    try:
        pipeline = ResearchPipeline(output_dir=args.output, verbose=verbose, resume=args.resume)

        if args.resynthesize:
            # Rerun only synthesis and output using cached data
            result = await pipeline.resynthesize(args.url)
        else:
            result = await pipeline.run(args.url)

        if verbose:
            console.print()
            display_summary(result, show_score=args.show_score)

        console.print(f"\n[bold green]Research complete in {result.duration_seconds:.1f}s[/bold green]")
        return 0

    except KeyboardInterrupt:
        console.print("\n[yellow]Research cancelled by user[/yellow]")
        return 130

    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        if verbose:
            console.print_exception()
        return 1


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
