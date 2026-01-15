"""
Deployment Readiness Checklist Generator

Creates a deployment checklist PDF with items pre-checked based on research findings.
"""

from pathlib import Path
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from models import CompanyProfile, SynthesisOutput, ResearchResults


def sanitize_text(text: str) -> str:
    """Sanitize text for PDF output."""
    replacements = {
        '\u2014': '-', '\u2013': '-', '\u2018': "'", '\u2019': "'",
        '\u201c': '"', '\u201d': '"', '\u2026': '...', '\u00a0': ' ',
        '\u2022': '*', '\u2192': '->', '\u2713': '[x]', '\u2717': '[ ]',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


class ChecklistPDF(FPDF):
    """PDF generator for deployment checklists."""

    def __init__(self, company_name: str):
        super().__init__()
        self.company_name = sanitize_text(company_name)
        self.add_page()
        self.set_auto_page_break(auto=True, margin=25)

    def header(self):
        """Add header to each page."""
        # Header banner
        self.set_fill_color(99, 102, 241)  # Indigo
        self.rect(0, 0, 210, 30, 'F')

        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 16)
        self.set_xy(15, 8)
        self.cell(0, 8, f"Deployment Readiness Checklist", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_font("Helvetica", "", 10)
        self.set_xy(15, 18)
        self.cell(0, 6, f"{self.company_name} | Fluency AI", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_text_color(0, 0, 0)
        self.ln(10)

    def footer(self):
        """Add footer to each page."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        timestamp = datetime.now().strftime("%B %d, %Y")
        self.cell(0, 10, f"Generated {timestamp} | Page {self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    def section_header(self, text: str):
        """Add a section header."""
        self.ln(5)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(31, 41, 55)
        self.cell(0, 7, sanitize_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(229, 231, 235)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def checklist_item(self, text: str, checked: bool = False, note: str = None, indent: int = 0):
        """Add a checklist item with optional check mark."""
        x_start = self.l_margin + (indent * 8)
        self.set_x(x_start)

        # Checkbox
        box_size = 4
        box_y = self.get_y() + 1

        if checked:
            # Filled checkbox (green background)
            self.set_fill_color(220, 252, 231)
            self.set_draw_color(22, 163, 74)
            self.rect(x_start, box_y, box_size, box_size, 'FD')
            # Checkmark
            self.set_text_color(22, 163, 74)
            self.set_font("Helvetica", "B", 8)
            self.set_xy(x_start + 0.5, box_y - 0.5)
            self.cell(box_size, box_size, "x")
        else:
            # Empty checkbox
            self.set_fill_color(255, 255, 255)
            self.set_draw_color(209, 213, 219)
            self.rect(x_start, box_y, box_size, box_size, 'D')

        # Text
        self.set_x(x_start + box_size + 3)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(55, 65, 81)

        # Use multi_cell for wrapping, but calculate available width
        text_width = self.w - self.r_margin - (x_start + box_size + 3)
        self.multi_cell(text_width, 5, sanitize_text(text))

        # Note (if provided)
        if note:
            self.set_x(x_start + box_size + 3)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(107, 114, 128)
            self.multi_cell(text_width, 4, f"Note: {sanitize_text(note)}")

        self.set_text_color(0, 0, 0)
        self.ln(1)


def generate_deployment_checklist(
    profile: CompanyProfile,
    synthesis: SynthesisOutput,
    research: ResearchResults,
    output_path: str
) -> bool:
    """
    Generate a deployment readiness checklist PDF.

    Items are pre-checked based on research findings.
    """
    try:
        pdf = ChecklistPDF(company_name=profile.name)

        # Overview section
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(75, 85, 99)
        pdf.multi_cell(0, 4,
            "This checklist identifies key requirements and considerations for deploying "
            "Fluency AI. Items are automatically checked based on research findings. "
            "Unchecked items require validation during discovery calls."
        )
        pdf.ln(5)

        # --- IDENTITY & ACCESS ---
        pdf.section_header("Identity & Access Management")

        # Check for SSO/Identity provider
        has_sso = False
        idp_name = None
        if research.tech_stack:
            if research.tech_stack.identity_provider:
                has_sso = True
                idp_name = research.tech_stack.identity_provider
            for integration in research.tech_stack.integrations:
                if integration.category.lower() in ["sso", "identity"]:
                    has_sso = True
                    idp_name = idp_name or integration.tool_name

        pdf.checklist_item(
            "SSO/SAML identity provider identified",
            checked=has_sso,
            note=f"Found: {idp_name}" if idp_name else "Ask in discovery call"
        )

        pdf.checklist_item(
            "Compatible IdP confirmed (Okta, Azure AD, Ping, OneLogin)",
            checked=idp_name and any(x in idp_name.lower() for x in ["okta", "azure", "ping", "onelogin"]) if idp_name else False,
            note="Fluency supports SAML 2.0 and OIDC" if not has_sso else None
        )

        pdf.checklist_item(
            "User provisioning method determined (SCIM, JIT, Manual)",
            checked=False,
            note="Typically discussed during technical discovery"
        )

        # --- SECURITY & COMPLIANCE ---
        pdf.section_header("Security & Compliance")

        # Check for certifications
        has_soc2 = False
        has_iso = False
        if research.security:
            for cert in research.security.certifications:
                cert_name = cert.name.lower()
                if "soc" in cert_name:
                    has_soc2 = True
                if "iso" in cert_name or "27001" in cert_name:
                    has_iso = True

        pdf.checklist_item(
            "SOC 2 compliance requirements identified",
            checked=has_soc2,
            note="Customer has SOC 2" if has_soc2 else "Verify requirements in discovery"
        )

        pdf.checklist_item(
            "ISO 27001 requirements identified",
            checked=has_iso,
            note="Customer has ISO 27001" if has_iso else None
        )

        # Industry-specific compliance
        industry_lower = profile.industry.lower() if profile.industry else ""

        is_healthcare = any(x in industry_lower for x in ["health", "medical", "pharma"])
        pdf.checklist_item(
            "BAA required (Healthcare/HIPAA)",
            checked=is_healthcare,
            note="Healthcare industry detected - BAA likely required" if is_healthcare else "N/A for non-healthcare"
        )

        is_financial = any(x in industry_lower for x in ["finance", "bank", "insurance"])
        pdf.checklist_item(
            "Financial regulatory compliance identified (SOX, FINRA)",
            checked=is_financial,
            note="Financial services - regulatory review needed" if is_financial else None
        )

        # Data residency
        has_data_residency_info = research.security and len(research.security.data_residency) > 0
        pdf.checklist_item(
            "Data residency requirements documented",
            checked=has_data_residency_info,
            note=f"Regions: {', '.join(research.security.data_residency[:3])}" if has_data_residency_info else "Ask about data location requirements"
        )

        pdf.checklist_item(
            "Security questionnaire process understood",
            checked=research.security and research.security.trust_center_url is not None,
            note=f"Trust center: {research.security.trust_center_url}" if (research.security and research.security.trust_center_url) else "Request vendor assessment process"
        )

        # --- EU/INTERNATIONAL ---
        has_eu_ops = False
        if research.financials and research.financials.geographic_operations:
            for region in research.financials.geographic_operations:
                if any(eu in region.lower() for eu in ["europe", "eu", "emea", "germany", "france", "uk"]):
                    has_eu_ops = True
                    break

        if has_eu_ops or "europe" in industry_lower:
            pdf.section_header("EU/International Considerations")

            pdf.checklist_item(
                "Works council approval requirements identified",
                checked=False,
                note="EU operations detected - confirm if works council approval needed"
            )

            pdf.checklist_item(
                "GDPR compliance requirements documented",
                checked=False,
                note="EU data protection requirements apply"
            )

            pdf.checklist_item(
                "EU data residency options reviewed",
                checked=False,
                note="Fluency supports EU data center deployment"
            )

        # --- INTEGRATION ---
        pdf.section_header("Integration & Technical")

        # Cloud provider
        cloud_provider = research.tech_stack.cloud_provider if research.tech_stack else None
        pdf.checklist_item(
            "Cloud infrastructure identified",
            checked=cloud_provider is not None,
            note=f"Found: {cloud_provider}" if cloud_provider else "AWS, Azure, GCP supported"
        )

        # Process tools
        process_tools = []
        if research.tech_stack:
            for integration in research.tech_stack.integrations:
                if integration.category.lower() in ["documentation", "workflow", "process", "collaboration"]:
                    process_tools.append(integration.tool_name)

        pdf.checklist_item(
            "Existing process documentation tools identified",
            checked=len(process_tools) > 0,
            note=f"Found: {', '.join(process_tools[:3])}" if process_tools else "Confluence, Notion, SharePoint supported"
        )

        pdf.checklist_item(
            "API integration requirements scoped",
            checked=False,
            note="Typically defined during technical discovery"
        )

        pdf.checklist_item(
            "Webhook/event notification requirements documented",
            checked=False
        )

        # --- DEPLOYMENT SCOPE ---
        pdf.section_header("Deployment Planning")

        pdf.checklist_item(
            "Initial pilot scope defined",
            checked=False,
            note="Recommend starting with 1-2 departments or use cases"
        )

        pdf.checklist_item(
            "Pilot success criteria established",
            checked=False
        )

        pdf.checklist_item(
            "Key stakeholders identified (IT, Security, Business)",
            checked=False
        )

        pdf.checklist_item(
            "Timeline expectations aligned",
            checked=False,
            note="Typical pilot: 4-8 weeks; Full rollout: 3-6 months"
        )

        # --- AI READINESS ---
        pdf.section_header("AI Governance & Readiness")

        has_ai_initiatives = research.strategic and len(research.strategic.ai_initiatives) > 0
        pdf.checklist_item(
            "AI/automation initiatives in progress",
            checked=has_ai_initiatives,
            note=f"{len(research.strategic.ai_initiatives)} initiatives found" if has_ai_initiatives else "Good opportunity to lead with AI adoption"
        )

        pdf.checklist_item(
            "AI governance framework exists",
            checked=False,
            note="Fluency provides governance and audit capabilities"
        )

        pdf.checklist_item(
            "Change management approach planned",
            checked=False
        )

        # --- SUMMARY ---
        pdf.ln(5)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(31, 41, 55)

        # Calculate checked items
        # This is a simplified count - in a real implementation, you'd track this
        pdf.cell(0, 6, "Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(75, 85, 99)

        score = synthesis.deployment_score
        pdf.multi_cell(0, 4,
            f"Based on research findings, this deployment scores {score.overall:.1f}/10 for readiness. "
            f"Key strengths include security maturity ({score.security_maturity}/10) and "
            f"integration fit ({score.integration_fit}/10). "
            f"Review unchecked items during discovery calls."
        )

        pdf.output(output_path)
        return True

    except Exception as e:
        print(f"Error generating checklist: {e}")
        import traceback
        traceback.print_exc()
        return False
