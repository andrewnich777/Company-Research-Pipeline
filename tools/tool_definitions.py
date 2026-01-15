"""
Tool definitions for Claude API agents.

These define the tools that agents can call. The actual implementations
are handled by the tool handlers.
"""

import httpx
from typing import Any, Callable

# Tool definitions for Claude API
WEB_FETCH_TOOL = {
    "name": "web_fetch",
    "description": """Fetch content from a URL and return the text content.
    Use this to read web pages, trust centers, security pages, etc.
    Returns the main text content of the page (HTML stripped).""",
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch"
            },
            "extract_prompt": {
                "type": "string",
                "description": "Optional: specific information to extract from the page"
            }
        },
        "required": ["url"]
    }
}

# WEB_SEARCH_TOOL - Now handled by Claude's native web_search capability
# See agents/base.py get_tool_definitions() which adds {"type": "web_search_20250305"}

SEC_FILING_TOOL = {
    "name": "sec_filing",
    "description": """Fetch SEC filings for a public company.
    Can retrieve 10-K (annual), 10-Q (quarterly), and 8-K (current) reports.
    Returns filing metadata and key sections (Risk Factors, Properties, etc.).""",
    "input_schema": {
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol (e.g., 'AON', 'AAPL')"
            },
            "filing_type": {
                "type": "string",
                "enum": ["10-K", "10-Q", "8-K"],
                "description": "Type of SEC filing to retrieve"
            },
            "sections": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific sections to extract (e.g., ['Risk Factors', 'Properties'])",
                "default": ["Risk Factors"]
            }
        },
        "required": ["ticker", "filing_type"]
    }
}

CRT_SH_TOOL = {
    "name": "crt_sh_lookup",
    "description": """Query SSL certificate transparency logs to discover subdomains.
    Useful for understanding a company's infrastructure (regions, services, etc.).""",
    "input_schema": {
        "type": "object",
        "properties": {
            "domain": {
                "type": "string",
                "description": "Base domain to search (e.g., 'aon.com')"
            }
        },
        "required": ["domain"]
    }
}


# All available tools
# Note: web_search is handled by Claude's native capability, not defined here
TOOL_DEFINITIONS = {
    "web_fetch": WEB_FETCH_TOOL,
    "sec_filing": SEC_FILING_TOOL,
    "crt_sh_lookup": CRT_SH_TOOL,
}


def get_tools_for_agent(tool_names: list[str]) -> list[dict]:
    """Get tool definitions for a specific agent."""
    return [TOOL_DEFINITIONS[name] for name in tool_names if name in TOOL_DEFINITIONS]


# ============================================================================
# Tool Handlers - Execute the actual tool calls
# ============================================================================

async def handle_web_fetch(url: str, extract_prompt: str = None) -> dict:
    """
    Fetch a URL and return its content.

    In a real implementation, this would use a proper web fetching service.
    For the demo, we use httpx with basic HTML text extraction.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            # Basic HTML to text conversion
            content = response.text

            # Strip script and style tags (basic)
            import re
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()

            # Truncate if too long
            if len(content) > 15000:
                content = content[:15000] + "... [truncated]"

            return {
                "success": True,
                "url": str(response.url),
                "status_code": response.status_code,
                "content": content
            }
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "url": url,
            "error": f"HTTP {e.response.status_code}: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "url": url,
            "error": str(e)
        }


# handle_web_search removed - now handled by Claude's native web_search capability


async def handle_crt_sh_lookup(domain: str) -> dict:
    """
    Query crt.sh for SSL certificate transparency data.
    Returns list of subdomains found in certificate logs.
    """
    try:
        url = f"https://crt.sh/?q=%.{domain}&output=json"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()

            # Extract unique subdomains
            subdomains = set()
            for entry in data:
                name = entry.get("name_value", "")
                for subdomain in name.split("\n"):
                    subdomain = subdomain.strip().lower()
                    if subdomain and subdomain.endswith(domain):
                        subdomains.add(subdomain)

            # Categorize subdomains
            categories = {
                "identity": [],  # sso, okta, auth, login
                "regional": [],  # eu, us, apac, uk
                "infrastructure": [],  # api, vpn, cdn
                "trust": [],  # trust, security
                "other": []
            }

            identity_patterns = ["sso", "okta", "auth", "login", "identity", "saml"]
            regional_patterns = ["eu", "apac", "us-", "uk", "asia", "emea"]
            infra_patterns = ["api", "vpn", "cdn", "staging", "dev", "prod"]
            trust_patterns = ["trust", "security", "compliance"]

            for sub in subdomains:
                prefix = sub.replace(f".{domain}", "").lower()
                if any(p in prefix for p in identity_patterns):
                    categories["identity"].append(sub)
                elif any(p in prefix for p in regional_patterns):
                    categories["regional"].append(sub)
                elif any(p in prefix for p in infra_patterns):
                    categories["infrastructure"].append(sub)
                elif any(p in prefix for p in trust_patterns):
                    categories["trust"].append(sub)
                else:
                    categories["other"].append(sub)

            return {
                "success": True,
                "domain": domain,
                "total_subdomains": len(subdomains),
                "categories": categories,
                "all_subdomains": sorted(subdomains)[:50]  # Limit to 50
            }
    except Exception as e:
        return {
            "success": False,
            "domain": domain,
            "error": str(e)
        }


# Tool handler registry
# Note: web_search is handled by Claude's native capability, not here
TOOL_HANDLERS: dict[str, Callable] = {
    "web_fetch": handle_web_fetch,
    "crt_sh_lookup": handle_crt_sh_lookup,
    # sec_filing handler is in sec_edgar.py
}


async def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool and return the result."""
    if tool_name not in TOOL_HANDLERS:
        return {"error": f"Unknown tool: {tool_name}"}

    handler = TOOL_HANDLERS[tool_name]
    return await handler(**tool_input)


def get_tool_handler(tool_name: str) -> Callable | None:
    """Get the handler function for a tool."""
    return TOOL_HANDLERS.get(tool_name)
