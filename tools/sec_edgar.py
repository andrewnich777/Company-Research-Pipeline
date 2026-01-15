"""
SEC EDGAR API tool for fetching and parsing SEC filings.

Uses the SEC's free EDGAR API to fetch 10-K, 10-Q, and 8-K filings.
"""

import re
import httpx
from typing import Optional
from dataclasses import dataclass


SEC_BASE_URL = "https://data.sec.gov"
SEC_ARCHIVES_URL = "https://www.sec.gov/Archives/edgar/data"

# Required by SEC API guidelines
HEADERS = {
    "User-Agent": "FluencyAI-Research/1.0 (research@fluency.ai)",
    "Accept-Encoding": "gzip, deflate",
}


@dataclass
class SECFiling:
    """Represents an SEC filing."""
    ticker: str
    cik: str
    form_type: str
    filing_date: str
    accession_number: str
    url: str
    sections: dict[str, str]  # Section name -> content


class SECEdgarTool:
    """Tool for interacting with SEC EDGAR API."""

    def __init__(self):
        self.ticker_to_cik_cache: dict[str, str] = {}

    async def lookup_cik(self, ticker: str) -> Optional[str]:
        """Look up CIK number from ticker symbol."""
        ticker = ticker.upper()

        if ticker in self.ticker_to_cik_cache:
            return self.ticker_to_cik_cache[ticker]

        try:
            # Try direct ticker lookup first
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get company tickers mapping
                resp = await client.get(
                    "https://www.sec.gov/files/company_tickers.json",
                    headers=HEADERS
                )
                if resp.status_code == 200:
                    data = resp.json()
                    for entry in data.values():
                        if entry.get("ticker", "").upper() == ticker:
                            cik = str(entry.get("cik_str", ""))
                            self.ticker_to_cik_cache[ticker] = cik
                            return cik
        except Exception:
            pass

        return None

    async def get_company_info(self, cik: str) -> dict:
        """Get company information from SEC."""
        cik_padded = cik.zfill(10)

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{SEC_BASE_URL}/submissions/CIK{cik_padded}.json",
                    headers=HEADERS
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass

        return {}

    async def get_recent_filings(
        self,
        cik: str,
        form_type: str,
        count: int = 5
    ) -> list[dict]:
        """Get recent filings of a specific type."""
        company_info = await self.get_company_info(cik)

        if not company_info:
            return []

        filings = company_info.get("filings", {}).get("recent", {})
        forms = filings.get("form", [])
        accessions = filings.get("accessionNumber", [])
        dates = filings.get("filingDate", [])
        primary_docs = filings.get("primaryDocument", [])

        results = []
        for i, form in enumerate(forms):
            if form == form_type and len(results) < count:
                accession_clean = accessions[i].replace("-", "")
                results.append({
                    "form": form,
                    "accession_number": accessions[i],
                    "filing_date": dates[i],
                    "url": f"{SEC_ARCHIVES_URL}/{cik}/{accession_clean}/{primary_docs[i]}",
                    "index_url": f"{SEC_ARCHIVES_URL}/{cik}/{accession_clean}"
                })

        return results

    async def fetch_filing_content(self, url: str) -> str:
        """Fetch the raw content of a filing."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url, headers=HEADERS)
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            return f"Error fetching filing: {str(e)}"

    def extract_sections(self, content: str, sections: list[str]) -> dict[str, str]:
        """
        Extract specific sections from a 10-K or 10-Q filing.

        Common sections:
        - "Risk Factors" (Item 1A)
        - "Properties" (Item 2)
        - "Legal Proceedings" (Item 3)
        - "Management's Discussion" (Item 7)
        """
        extracted = {}

        # Clean HTML
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'\s+', ' ', text)

        section_patterns = {
            "Risk Factors": [
                r'(?:Item\s*1A[.\s]*Risk\s*Factors)(.*?)(?=Item\s*1B|Item\s*2\b)',
                r'(?:RISK\s*FACTORS)(.*?)(?=ITEM\s*1B|ITEM\s*2\b)',
            ],
            "Properties": [
                r'(?:Item\s*2[.\s]*Properties)(.*?)(?=Item\s*3\b)',
                r'(?:PROPERTIES)(.*?)(?=ITEM\s*3\b)',
            ],
            "Legal Proceedings": [
                r'(?:Item\s*3[.\s]*Legal\s*Proceedings)(.*?)(?=Item\s*4\b)',
            ],
            "Business": [
                r'(?:Item\s*1[.\s]*Business)(.*?)(?=Item\s*1A\b|Item\s*2\b)',
            ],
        }

        for section in sections:
            if section in section_patterns:
                for pattern in section_patterns[section]:
                    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                    if match:
                        section_text = match.group(1).strip()
                        # Truncate if too long
                        if len(section_text) > 10000:
                            section_text = section_text[:10000] + "... [truncated]"
                        extracted[section] = section_text
                        break

        return extracted

    async def get_filing_with_sections(
        self,
        ticker: str,
        form_type: str,
        sections: list[str] = None
    ) -> Optional[SECFiling]:
        """
        Fetch a filing and extract specified sections.

        Args:
            ticker: Stock ticker symbol
            form_type: Type of filing (10-K, 10-Q, 8-K)
            sections: List of sections to extract (default: Risk Factors)
        """
        if sections is None:
            sections = ["Risk Factors"]

        # Look up CIK
        cik = await self.lookup_cik(ticker)
        if not cik:
            return None

        # Get recent filings
        filings = await self.get_recent_filings(cik, form_type, count=1)
        if not filings:
            return None

        filing_info = filings[0]

        # Fetch content
        content = await self.fetch_filing_content(filing_info["url"])
        if content.startswith("Error"):
            return None

        # Extract sections
        extracted_sections = self.extract_sections(content, sections)

        return SECFiling(
            ticker=ticker,
            cik=cik,
            form_type=form_type,
            filing_date=filing_info["filing_date"],
            accession_number=filing_info["accession_number"],
            url=filing_info["url"],
            sections=extracted_sections
        )


# Singleton instance
_sec_tool = None


def get_sec_tool() -> SECEdgarTool:
    """Get the SEC EDGAR tool singleton."""
    global _sec_tool
    if _sec_tool is None:
        _sec_tool = SECEdgarTool()
    return _sec_tool


async def handle_sec_filing(
    ticker: str,
    filing_type: str,
    sections: list[str] = None
) -> dict:
    """
    Tool handler for SEC filing requests.

    This is called by the agent's tool use loop.
    """
    tool = get_sec_tool()

    try:
        filing = await tool.get_filing_with_sections(
            ticker=ticker,
            form_type=filing_type,
            sections=sections or ["Risk Factors", "Properties"]
        )

        if filing is None:
            return {
                "success": False,
                "error": f"Could not find {filing_type} filing for {ticker}"
            }

        return {
            "success": True,
            "ticker": filing.ticker,
            "cik": filing.cik,
            "form_type": filing.form_type,
            "filing_date": filing.filing_date,
            "url": filing.url,
            "sections": filing.sections
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Register the handler with tool_definitions
from tools.tool_definitions import TOOL_HANDLERS
TOOL_HANDLERS["sec_filing"] = handle_sec_filing
