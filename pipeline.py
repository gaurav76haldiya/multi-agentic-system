
from agents import writer_chain, critic_chain
from tools import web_search, scrape_url


def run_research_pipeline(topic: str, config=None) -> dict:
    topic = topic.strip()

    if not topic:
        raise ValueError("Research topic cannot be empty.")

    queries = [
        topic,
        f"{topic} recent developments and evidence",
        f"{topic} challenges, limitations and risks",
    ]

    sources_by_url = {}

    # Step 1: Search with SearXNG.
    for query in queries:
        results = web_search(query)

        for source in results:
            url = source.get("url", "").strip()

            if url:
                sources_by_url.setdefault(url, source)

    sources = list(sources_by_url.values())

    if not sources:
        raise RuntimeError(
            "SearXNG returned no usable search results. "
            "Check the SearXNG instance and its enabled search engines."
        )

    # Step 2: Read source pages.
    research_parts = []

    for source in sources:
        url = source["url"]

        try:
            content = scrape_url(url)

            if not content.strip():
                content = source.get("snippet", "")

        except Exception as exc:
            print(f"Could not read {url}: {exc}")
            content = source.get("snippet", "")

        if content:
            research_parts.append(
                f"Title: {source.get('title', 'Untitled')}\n"
                f"URL: {url}\n"
                f"Content: {content}"
            )

    research = "\n\n".join(research_parts)

    if not research.strip():
        raise RuntimeError(
            "Search results were found, but no source content "
            "could be collected."
        )

    # Step 3: Generate the report using Gemini.
    draft = writer_chain.invoke({
        "topic": topic,
        "research": research,
    })

    # Step 4: Review the report using Gemini.
    review = critic_chain.invoke({
        "report": draft,
    })

    final_report = (
        f"{draft}\n\n"
        f"## Report Review\n\n{review}"
    )

    return {
        "topic": topic,
        "plan": queries,
        "sources": sources,
        "draft": draft,
        "report": final_report,
    }
