
import ipaddress
import socket
from urllib.parse import urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

TIMEOUT = 20
MAX_PAGE_CHARS = 15000
USER_AGENT = "MultiAgentResearchSystem/1.0"


def get_setting(name, default=None):
    """Read settings from environment variables or Streamlit secrets."""
    value = __import__("os").getenv(name)

    if value:
        return value

    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def web_search(query: str) -> list:
    """
    Search Purili's hosted index without a search API key.

    Returns normalized source dictionaries compatible with pipeline.py.
    """
    query = query.strip()

    if not query:
        return []

    endpoint = "https://puri.li/api/search"

    try:
        response = requests.get(
            endpoint,
            params={"q": query, "page": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Web search request failed: {exc}"
        ) from exc
    except ValueError as exc:
        raise RuntimeError(
            "The search service returned an invalid JSON response."
        ) from exc

    if not isinstance(data, dict):
        raise RuntimeError("Unexpected search response format.")

    results = data.get("results", [])

    if not isinstance(results, list):
        raise RuntimeError(
            "The search response does not contain a results list."
        )

    sources = []
    seen_urls = set()

    for item in results:
        if not isinstance(item, dict):
            continue

        url = str(item.get("url", "")).strip()

        if not url:
            continue

        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        snippet = (
            item.get("description")
            or item.get("snippet")
            or item.get("content")
            or ""
        )

        sources.append(
            {
                "title": item.get("title") or "Untitled",
                "url": url,
                "snippet": str(snippet),
                "content": str(snippet),
            }
        )

    return sources


def _validate_public_url(url: str) -> None:
    """
    Basic URL validation to reduce SSRF risks when fetching search results.
    """
    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Only valid HTTP and HTTPS URLs are allowed.")

    hostname = parsed.hostname.lower()

    if hostname in ("localhost",) or hostname.endswith(".localhost"):
        raise ValueError("Localhost URLs are not allowed.")

    try:
        addresses = socket.getaddrinfo(
            hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ValueError("Could not resolve the source hostname.") from exc

    for address in addresses:
        ip_text = address[4][0].split("%")[0]
        ip = ipaddress.ip_address(ip_text)

        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise ValueError("Private or non-public source URLs are not allowed.")


def scrape_url(url: str) -> str:
    """
    Fetch a public web page and extract readable text.

    Returns an empty string when a page cannot be read.
    """
    try:
        _validate_public_url(url)

        response = requests.get(
            url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; MultiAgentResearchSystem/1.0)"
                )
            },
            timeout=TIMEOUT,
            allow_redirects=False,
        )

        if response.is_redirect:
            return ""

        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()

        if content_type and not (
            "text/html" in content_type
            or "text/plain" in content_type
        ):
            return ""

        if "text/plain" in content_type:
            return response.text[:MAX_PAGE_CHARS]

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(
            [
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "noscript",
                "svg",
                "form",
            ]
        ):
            element.decompose()

        text = soup.get_text(separator="\n", strip=True)

        return text[:MAX_PAGE_CHARS]

    except (requests.RequestException, ValueError) as exc:
        print(f"Could not scrape {url}: {exc}")
        return ""
