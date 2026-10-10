
import os
from urllib.parse import urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

TIMEOUT = 20


def get_setting(name, default=None):
    value = os.getenv(name)

    if value:
        return value

    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


def web_search(query: str) -> list:
    """Search using a SearXNG instance and return normalized sources."""

    base_url = get_setting("SEARXNG_URL")

    if not base_url:
        raise RuntimeError(
            "SEARXNG_URL is missing. Configure your SearXNG instance URL."
        )

    base_url = base_url.rstrip("/")

    try:
        response = requests.get(
            f"{base_url}/search",
            params={
                "q": query,
                "format": "json",
                "language": "en",
                "safesearch": 1,
            },
            headers={"User-Agent": "MultiAgentResearchApp/1.0"},
            timeout=TIMEOUT,
        )

        if response.status_code == 403:
            raise RuntimeError(
                "SearXNG returned 403. JSON output may be disabled "
                "on this instance."
            )

        response.raise_for_status()
        data = response.json()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not connect to SearXNG: {exc}"
        ) from exc
    except ValueError as exc:
        raise RuntimeError(
            "SearXNG did not return JSON. Check SEARXNG_URL and "
            "whether the instance supports format=json."
        ) from exc

    results = data.get("results", [])

    sources = []

    for item in results:
        url = str(item.get("url", "")).strip()

        if not url:
            continue

        sources.append({
            "title": item.get("title", "Untitled"),
            "url": url,
            "snippet": item.get("content", ""),
            "content": item.get("content", ""),
        })

    return sources


def scrape_url(url: str) -> str:
    """Fetch a web page and extract readable text."""

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError("Only valid HTTP and HTTPS URLs are supported.")

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Could not fetch source page: {exc}"
        ) from exc

    soup = BeautifulSoup(response.text, "html.parser")

    for element in soup([
        "script", "style", "nav", "footer", "header",
        "noscript", "svg", "form",
    ]):
        element.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Avoid sending excessively large pages to Gemini.
    return text[:15000]
