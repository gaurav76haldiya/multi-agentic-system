
from agents import (
    build_search_agent,
    build_reader_agent,
    writer_chain,
    critic_chain,
)
from tools import web_search, scrape_url


def run_research_pipeline(topic: str, config=None) -> dict:
    """
    Run the research pipeline:
    1. Search the web using Freesea.
    2. Collect and deduplicate source URLs.
    3. Read source content.
    4. Generate a report using Gemini.
    5. Review the report using Gemini.
    """

    topic = topic.strip()

    if not topic:
        raise ValueError("Research topic cannot be empty.")

    # Search different aspects of the topic.
    queries = [
        topic,
        f"{topic} recent developments and evidence",
        f"{topic} challenges, limitations and risks",
    ]

    sources_by_url = {}

    # Step 1: Search using Freesea.
    for query in queries:
        try:
            results = web_search(query)
        except Exception as exc:
            print(f"Search failed for query '{query}': {exc}")
            continue

        # Handle a list of source dictionaries.
        if isinstance(results, list):
            for source in results:
                if not isinstance(source, dict):
                    continue

                url = str(source.get("url", "")).strip()

                if url:
                    sources_by_url.setdefault(url, source)

        # Also support a dictionary containing a results list.
        elif isinstance(results, dict):
            items = results.get("results", [])

            if isinstance(items, list):
                for source in items:
                    if not isinstance(source, dict):
                        continue

                    url = str(source.get("url", "")).strip()

                    if url:
                        sources_by_url.setdefault(url, source)

    sources = list(sources_by_url.values())

    if not sources:
        raise RuntimeError(
            "Freesea returned no usable search results. "
            "Check your FREESEA_API_KEY, API quota, and tools.py response format."
        )

    # Step 2: Read the source pages.
    research_parts = []

    for source in sources:
        url = str(source.get("url", "")).strip()

        if not url:
            continue

        title = source.get("title", "Untitled")
        snippet = source.get("snippet", source.get("content", ""))

        try:
            page_content = scrape_url(url)

            if isinstance(page_content, dict):
                page_content = (
                    page_content.get("content")
                    or page_content.get("text")
                    or page_content.get("markdown")
                    or ""
                )

            if page_content is None:
                page_content = ""

            page_content = str(page_content).strip()

            if page_content:
                research_parts.append(
                    f"Title: {title}\n"
                    f"URL: {url}\n"
                    f"Content:\n{page_content}"
                )
            else:
                research_parts.append(
                    f"Title: {title}\n"
                    f"URL: {url}\n"
                    f"Search snippet: {snippet}"
                )

        except Exception as exc:
            print(f"Could not read source {url}: {exc}")

            research_parts.append(
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Search snippet: {snippet}"
            )

    research = "\n\n".join(research_parts)

    if not research.strip():
        raise RuntimeError(
            "Sources were found, but no readable research content was collected."
        )

    # Step 3: Generate the research report using Gemini.
    draft = writer_chain.invoke(
        {
            "topic": topic,
            "research": research,
        }
    )

    # Step 4: Review the report using Gemini.
    review = critic_chain.invoke(
        {
            "report": draft,
        }
    )

    # Combine the report and review.
    final_report = (
        f"{draft}\n\n"
        f"## Report Review\n\n"
        f"{review}"
    )

    return {
        "topic": topic,
        "plan": queries,
        "sources": sources,
        "draft": draft,
        "report": final_report,
    }
