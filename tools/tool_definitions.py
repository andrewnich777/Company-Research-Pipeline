"""
Tool definitions for Claude API agents.

These define the tools that agents can call. The actual implementations
are handled by the tool handlers.
"""

import httpx
import time
from typing import Any, Callable
from urllib.parse import urlparse

from logger import get_logger

logger = get_logger(__name__)


# =============================================================================
# Fetch Cache - Reduces redundant HTTP requests across agents
# =============================================================================
_fetch_cache: dict[str, tuple[dict, float]] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour


def get_cache_stats() -> dict:
    """Get current cache statistics."""
    return {
        "cached_urls": len(_fetch_cache),
        "urls": list(_fetch_cache.keys())[:20],  # First 20 for debugging
    }


def clear_fetch_cache():
    """Clear the fetch cache (useful between pipeline runs)."""
    global _fetch_cache
    _fetch_cache.clear()
    logger.debug("Fetch cache cleared")

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

def validate_url(url: str) -> tuple[bool, str]:
    """
    Validate and normalize a URL.

    Returns:
        Tuple of (is_valid, normalized_url_or_error_message)
    """
    if not url or not isinstance(url, str):
        return False, "URL must be a non-empty string"

    # Add scheme if missing
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        parsed = urlparse(url)

        # Validate basic URL structure
        if not parsed.netloc:
            return False, "URL must have a valid domain"

        # Check for valid scheme
        if parsed.scheme not in ("http", "https"):
            return False, "URL must use http or https scheme"

        # Basic domain validation
        domain = parsed.netloc
        if "." not in domain and domain != "localhost":
            return False, f"Invalid domain: {domain}"

        return True, url

    except Exception as e:
        return False, f"URL parsing error: {str(e)}"


def extract_text_from_html(html_content: str, max_length: int = 15000) -> str:
    """
    Extract readable text from HTML content.

    Uses BeautifulSoup if available, falls back to regex.
    """
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Get text
        text = soup.get_text(separator=" ", strip=True)

        # Normalize whitespace
        import re
        text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > max_length:
            text = text[:max_length] + "... [truncated]"

        return text

    except ImportError:
        # Fallback to regex-based extraction
        logger.debug("BeautifulSoup not available, using regex fallback for HTML parsing")
        import re
        content = html_content
        content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
        content = re.sub(r'<[^>]+>', ' ', content)
        content = re.sub(r'\s+', ' ', content).strip()

        if len(content) > max_length:
            content = content[:max_length] + "... [truncated]"

        return content


async def handle_web_fetch(url: str, extract_prompt: str = None) -> dict:
    """
    Fetch a URL and return its content.

    Args:
        url: The URL to fetch
        extract_prompt: Optional prompt for extraction (not currently used)

    Returns:
        Dict with success status, content or error message
    """
    # Validate URL
    is_valid, result = validate_url(url)
    if not is_valid:
        logger.warning(f"Invalid URL rejected: {url} - {result}")
        return {
            "success": False,
            "url": url,
            "error": f"Invalid URL: {result}"
        }

    validated_url = result

    # Check cache first (normalize URL for cache key)
    cache_key = validated_url.lower().rstrip('/')
    if cache_key in _fetch_cache:
        cached_result, cached_at = _fetch_cache[cache_key]
        if time.time() - cached_at < CACHE_TTL_SECONDS:
            logger.info(f"Cache hit for {validated_url}")
            return {**cached_result, "from_cache": True}
        else:
            # Expired - remove from cache
            del _fetch_cache[cache_key]

    logger.debug(f"Fetching URL: {validated_url}")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                "User-Agent": "FluencyAI-Research/1.0 (https://fluency.ai)"
            }
            response = await client.get(validated_url, headers=headers)
            response.raise_for_status()

            # Extract text content from HTML
            content = extract_text_from_html(response.text)

            logger.debug(f"Successfully fetched {validated_url} - {len(content)} chars")

            result = {
                "success": True,
                "url": str(response.url),
                "status_code": response.status_code,
                "content": content
            }

            # Cache successful results
            _fetch_cache[cache_key] = (result, time.time())

            return result

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
        logger.warning(f"HTTP error fetching {validated_url}: {error_msg}")
        return {
            "success": False,
            "url": validated_url,
            "error": error_msg
        }

    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching {validated_url}")
        return {
            "success": False,
            "url": validated_url,
            "error": "Request timed out after 30 seconds"
        }

    except httpx.RequestError as e:
        logger.warning(f"Request error fetching {validated_url}: {str(e)}")
        return {
            "success": False,
            "url": validated_url,
            "error": f"Request failed: {str(e)}"
        }

    except Exception as e:
        logger.exception(f"Unexpected error fetching {validated_url}")
        return {
            "success": False,
            "url": validated_url,
            "error": f"Unexpected error: {str(e)}"
        }


# handle_web_search removed - now handled by Claude's native web_search capability


async def handle_crt_sh_lookup(domain: str) -> dict:
    """
    Query crt.sh for SSL certificate transparency data.
    Returns list of subdomains found in certificate logs.
    """
    logger.debug(f"Looking up certificate transparency data for: {domain}")

    # Validate domain
    if not domain or not isinstance(domain, str):
        logger.warning("Invalid domain provided to crt.sh lookup")
        return {
            "success": False,
            "domain": domain,
            "error": "Domain must be a non-empty string"
        }

    # Basic domain validation
    domain = domain.lower().strip()
    if "." not in domain:
        logger.warning(f"Invalid domain format: {domain}")
        return {
            "success": False,
            "domain": domain,
            "error": "Invalid domain format"
        }

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

            identity_patterns = ["sso", "okta", "auth", "login", "identity", "saml", "ping", "sts", "adfs", "idp", "azure", "onelogin", "duo", "jumpcloud"]
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

            logger.debug(f"Found {len(subdomains)} subdomains for {domain}")

            return {
                "success": True,
                "domain": domain,
                "total_subdomains": len(subdomains),
                "categories": categories,
                "all_subdomains": sorted(subdomains)[:50]  # Limit to 50
            }

    except httpx.TimeoutException:
        logger.warning(f"Timeout querying crt.sh for {domain}")
        return {
            "success": False,
            "domain": domain,
            "error": "Request timed out after 30 seconds"
        }

    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error querying crt.sh for {domain}: {e.response.status_code}")
        return {
            "success": False,
            "domain": domain,
            "error": f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
        }

    except Exception as e:
        logger.exception(f"Unexpected error querying crt.sh for {domain}")
        return {
            "success": False,
            "domain": domain,
            "error": f"Unexpected error: {str(e)}"
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
