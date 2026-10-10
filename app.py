
import streamlit as st
from pipeline import run_research_pipeline

st.set_page_config(
    page_title="Multi-Agent Research Assistant",
    page_icon="🔎",
    layout="wide",
)

st.title("🔎 Multi-Agent Research Assistant")
st.write(
    "Research a topic using web search, webpage reading, "
    "AI report writing, and critic review."
)

topic = st.text_area(
    "Research topic",
    placeholder="For example: Latest developments in agentic AI",
    height=100,
)

if st.button("Generate research report", type="primary"):
    if not topic.strip():
        st.warning("Please enter a research topic.")
    else:
        try:
            with st.spinner("Research agents are working..."):
                result = run_research_pipeline(topic.strip())

            st.success("Research completed!")

            st.subheader("Research report")
            st.markdown(result.get("report", "No report generated."))

            st.subheader("Critic feedback")
            st.markdown(result.get("feedback", "No feedback generated."))

            with st.expander("View search results"):
                st.write(result.get("search_results", ""))

            with st.expander("View scraped content"):
                st.write(result.get("scraped_content", ""))

        except Exception as exc:
            st.error("The research pipeline failed.")
            st.exception(exc)
