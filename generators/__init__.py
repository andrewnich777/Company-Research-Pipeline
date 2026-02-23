from .sales_brief import generate_sales_brief
from .security_brief import generate_security_brief
from .product_brief import generate_product_brief
from .pdf_generator import generate_pdf, generate_all_pdfs
from .checklist_generator import generate_deployment_checklist
from .executive_brief import generate_executive_brief
from .recommendation_engine import generate_score_based_recommendation, get_score_summary
from .dedup import (
    BriefDeduplicator,
    deduplicate_items,
    deduplicate_claims,
    deduplicate_by_field,
    deduplicate_evidence_urls,
)

__all__ = [
    "generate_sales_brief",
    "generate_security_brief",
    "generate_product_brief",
    "generate_pdf",
    "generate_all_pdfs",
    "generate_deployment_checklist",
    "generate_executive_brief",
    "generate_score_based_recommendation",
    "get_score_summary",
    "BriefDeduplicator",
    "deduplicate_items",
    "deduplicate_claims",
    "deduplicate_by_field",
    "deduplicate_evidence_urls",
]
