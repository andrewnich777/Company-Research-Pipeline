#!/usr/bin/env python3
"""
Quick script to regenerate briefs from existing research data.
Usage: python regenerate_briefs.py <company_folder>
Example: python regenerate_briefs.py results/lila_ai
"""

import json
import sys
from pathlib import Path

from models import (
    CompanyProfile, CompanyType, ResearchResults, SynthesisOutput,
    SecurityFindings, TechStackFindings, StrategicFindings,
    JobPostingInsights, CustomerReviewInsights, RegulatoryRiskInsights,
    StakeholderIntelligence, LinkedInIntelligence, DeploymentScore, EvidenceGraph
)
from generators.sales_brief import generate_sales_brief
from generators.security_brief import generate_security_brief
from generators.product_brief import generate_product_brief
from generators.executive_brief import generate_executive_brief
from generators.pdf_generator import generate_all_pdfs


def load_research_results(raw_research: dict) -> ResearchResults:
    """Load research results from raw JSON."""
    results = ResearchResults()

    # Map of field names to model classes
    model_map = {
        "security": SecurityFindings,
        "tech_stack": TechStackFindings,
        "strategic": StrategicFindings,
        "financials": None,  # Skip - complex type
        "job_postings": JobPostingInsights,
        "customer_reviews": CustomerReviewInsights,
        "regulatory_risk": RegulatoryRiskInsights,
        "stakeholders": StakeholderIntelligence,
        "linkedin_intel": LinkedInIntelligence,
    }

    for field_name, model_class in model_map.items():
        if field_name in raw_research and raw_research[field_name] and model_class:
            try:
                setattr(results, field_name, model_class(**raw_research[field_name]))
            except Exception as e:
                print(f"  Warning: Could not load {field_name}: {e}")

    return results


def load_synthesis(evidence: dict, profile: CompanyProfile) -> SynthesisOutput:
    """Create synthesis output from evidence JSON."""
    # Create evidence graph
    evidence_graph = EvidenceGraph(
        security_claims=evidence.get("security_claims", []),
        technology_claims=evidence.get("technology_claims", []),
        strategic_claims=evidence.get("strategic_claims", []),
        financial_claims=evidence.get("financial_claims", []),
    )

    # Create deployment score
    score = DeploymentScore(
        overall=evidence.get("deployment_score", {}).get("overall", 5.0),
        security_maturity=evidence.get("deployment_score", {}).get("security_maturity", 5),
        integration_fit=evidence.get("deployment_score", {}).get("integration_fit", 5),
        compliance_complexity=evidence.get("deployment_score", {}).get("compliance_complexity", 5),
        strategic_alignment=evidence.get("deployment_score", {}).get("strategic_alignment", 5),
        deal_complexity=evidence.get("deployment_score", {}).get("deal_complexity", 5),
        rationale=evidence.get("deployment_score", {}).get("rationale", ""),
        champion_identified=evidence.get("deployment_score", {}).get("champion_identified", 5),
        regulatory_risk=evidence.get("deployment_score", {}).get("regulatory_risk", 5),
    )

    return SynthesisOutput(
        company_name=profile.name,
        deployment_score=score,
        opportunities=evidence.get("opportunities", []),
        blockers=evidence.get("blockers", []),
        recommended_approach=evidence.get("recommended_approach", ""),
        discovery_questions=evidence.get("discovery_questions", []),
        evidence_graph=evidence_graph,
        contradictions=evidence.get("contradictions", []),
    )


def main():
    if len(sys.argv) < 2:
        print("Usage: python regenerate_briefs.py <results_folder>")
        print("Example: python regenerate_briefs.py results/lila_ai")
        sys.exit(1)

    folder = Path(sys.argv[1])

    # Load files
    checkpoint_file = folder / "checkpoint.json"
    raw_research_file = folder / "raw_research.json"
    evidence_file = folder / "evidence.json"

    if not all(f.exists() for f in [checkpoint_file, raw_research_file, evidence_file]):
        print(f"Error: Missing required files in {folder}")
        sys.exit(1)

    print(f"Regenerating briefs from {folder}...")

    # Load checkpoint for profile
    with open(checkpoint_file) as f:
        checkpoint = json.load(f)

    profile_data = checkpoint["profile"]
    profile = CompanyProfile(
        name=profile_data["name"],
        legal_name=profile_data.get("legal_name"),
        domain=profile_data["domain"],
        company_type=CompanyType(profile_data["company_type"]),
        ticker=profile_data.get("ticker"),
        industry=profile_data.get("industry"),
        hq_location=profile_data.get("hq_location"),
        employee_count=profile_data.get("employee_count"),
        founded_year=profile_data.get("founded_year"),
        description=profile_data.get("description", ""),
    )

    # Load research results
    with open(raw_research_file) as f:
        raw_research = json.load(f)

    research = load_research_results(raw_research)

    # Load evidence for synthesis
    with open(evidence_file) as f:
        evidence = json.load(f)

    synthesis = load_synthesis(evidence, profile)

    # Generate briefs
    print("  Generating sales brief...")
    sales_brief = generate_sales_brief(profile, synthesis, research)
    (folder / "sales_brief.md").write_text(sales_brief, encoding="utf-8")

    print("  Generating security brief...")
    security_brief = generate_security_brief(profile, synthesis, research)
    (folder / "security_brief.md").write_text(security_brief, encoding="utf-8")

    print("  Generating product brief...")
    product_brief = generate_product_brief(profile, synthesis, research)
    (folder / "product_brief.md").write_text(product_brief, encoding="utf-8")

    print("  Generating executive brief...")
    executive_brief = generate_executive_brief(profile, synthesis, research)
    (folder / "executive_brief.md").write_text(executive_brief, encoding="utf-8")

    # Generate PDFs
    print("  Generating PDFs...")
    generate_all_pdfs(
        str(folder),
        profile.name,
        sales_brief,
        security_brief,
        product_brief,
        executive_brief
    )

    print("Done! Briefs regenerated successfully.")


if __name__ == "__main__":
    main()
