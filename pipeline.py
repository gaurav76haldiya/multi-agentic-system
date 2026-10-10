
from agents import create_research_plan, review_report, write_report
from config import AppConfig
from tools import search_web


def run_research_pipeline(
    topic: str,
    config: AppConfig,
) -> dict:
    topic = topic.strip()

    if not topic:
        raise ValueError("Research topic cannot be empty.")

    # Agent 1: create the research plan.
    plan = create_research_plan(topic, config)

    # Search different aspects of the topic.
    queries = [
        topic,
        f"{topic} recent developments and evidence",
        f"{topic} challenges, limitations and risks",
    ]

    # Remove duplicate URLs from results.
    sources_by_url = {}

    for query in queries:
        results = search_web(query, config)

        for source in results:
            url = source.get("url", "").strip()

            if url:
                sources_by_url.setdefault(url, source)

    sources = list(sources_by_url.values())

    if not sources:
        raise RuntimeError(
            "No usable search results were returned by Freesea. "
            "Try a different topic or check your search API configuration."
        )

    # Agent 2: write the research report.
    draft = write_report(topic, plan, sources, config)

    # Agent 3: review and refine the draft.
    final_report = review_report(topic, draft, config)

    return {
        "topic": topic,
        "plan": plan,
        "sources": sources,
        "draft": draft,
        "report": final_report,
    }
