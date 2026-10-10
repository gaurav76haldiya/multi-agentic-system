
import json
import os

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from langchain.tools import tool

load_dotenv()

FREESEA_URL = "https://freesea.dev/v1/search"


def get_freesea_key():
    key = os.getenv("FREESEA_API_KEY")
    if not key:
        raise ValueError("FREESEA_API_KEY is not configured.")
    return key


@tool
def web_search(query: str) -> str:
    """Search the web and return titles, URLs, snippets, and results."""
    response = requests.post(
        FREESEA_URL,
        headers={
            "Authorization": f"Bearer {get_freesea_key()}",
            "Content-Type": "application/json",
        },
        json={
            "query": query,
            "max_results": 5,
        },
        timeout=30,
    )
    response.raise_for_status()

    # Keep the full response instead of assuming a Tavily response schema.
    return json.dumps(response.json(), ensure_ascii=False)


@tool
def scrape_url(url: str) -> str:
    """Fetch a webpage and return readable text content."""
    try:
        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for tag in soup(
            ["script", "style", "nav", "footer", "header"]
        ):
            tag.decompose()

        return soup.get_text(separator=" ", strip=True)[:5000]

    except requests.RequestException as exc:
        return f"Could not scrape URL: {exc}"
