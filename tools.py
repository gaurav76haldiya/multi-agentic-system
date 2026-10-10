
import os
import time

import requests
import streamlit as st
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.tools import tool

load_dotenv()

FREESEA_URL = "https://freesea.dev/v1/search"
SEARCH_TIMEOUT = 30


def get_setting(name, default=None):
    """Read configuration from environment variables or Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value

    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


@tool
def web_search(query: str) -> str:
    """Search Freesea for recent information. Returns titles, URLs and snippets."""
    api_key = get_setting("FREESEA_API_KEY")

    if not api_key:
        return (
            "Web search is unavailable: FREESEA_API_KEY is missing. "
            "Configure it in .env or Streamlit Community Cloud Secrets."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    payload = {
        "query": query,
        "max_results": 5,
    }

    data = None

    # Freesea recommends waiting for Retry-After and retrying once on 429.
    for attempt in range(2):
        try:
            response = requests.post(
                FREESEA_URL,
                headers=headers,
                json=payload,
                timeout=SEARCH_TIMEOUT,
            )

            if response.status_code == 429:
                if attempt == 1:
                    return (
                        "Freesea search is temporarily rate-limited after "
                        "one retry. No search results were retrieved. "
                        "Please wait and run the research again. Details: "
                        + response.text[:300]
                    )

                retry_after = response.headers.get("Retry-After", "2")

                try:
                    wait_seconds = max(1.0, float(retry_after))
                except (TypeError, ValueError):
                    wait_seconds = 2.0

                time.sleep(wait_seconds)
                continue

            response.raise_for_status()
            data = response.json()
            break

        except requests.RequestException as exc:
            status = (
                exc.response.status_code
                if exc.response is not None
                else "network error"
            )
            details = (
                exc.response.text[:300]
                if exc.response is not None
                else str(exc)
            )
            return f"Freesea search failed ({status}): {details}"

        except ValueError:
            return "Freesea returned an invalid JSON response."

    if not isinstance(data, dict):
        return "Freesea returned no usable search response."

    results = (
        data.get("results")
        or data.get("data")
        or data.get("items")
        or []
    )

    if not isinstance(results, list) or not results:
        return (
            f"Freesea returned no search results for: {query}. "
            "Do not invent sources."
        )

    output = []

    for item in results:
        if not isinstance(item, dict):
            continue

        title = item.get("title") or item.get("name") or "Untitled"
        url = item.get("url") or item.get("link") or ""
        snippet = (
            item.get("content")
            or item.get("snippet")
            or item.get("description")
            or item.get("text")
            or ""
        )

        if url:
            output.append(
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Snippet: {str(snippet)[:500]}\n"
            )

    if not output:
        return "Freesea returned results without usable URLs."

    return "\n----\n".join(output)


@tool
def scrape_url(url: str) -> str:
    """Scrape and return clean text content from a URL for deeper reading."""
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()

        return soup.get_text(separator=" ", strip=True)[:3000]

    except Exception as exc:
        return f"Could not scrape URL: {exc}"
