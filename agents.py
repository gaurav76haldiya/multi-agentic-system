
import os

import streamlit as st
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from tools import web_search, scrape_url

load_dotenv()


def get_setting(name, default=None):
    """Read configuration from environment variables or Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value

    try:
        return st.secrets.get(name, default)
    except Exception:
        return default


api_key = get_setting("GOOGLE_API_KEY") or get_setting("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "Google Gemini API key is missing. Set GOOGLE_API_KEY "
        "in your .env file or Streamlit Community Cloud Secrets."
    )

# Google Gemini model
llm = ChatGoogleGenerativeAI(
    model=get_setting("GEMINI_MODEL", "gemini-2.5-flash"),
    google_api_key=api_key,
    temperature=0,
)


# 1. Search agent
def build_search_agent():
    return create_agent(
        model=llm,
        tools=[web_search],
    )


# 2. Reader agent
def build_reader_agent():
    return create_agent(
        model=llm,
        tools=[scrape_url],
    )


# 3. Writer chain — original prompt preserved
writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert research writer. Write clear, structured "
        "and insightful reports.",
    ),
    (
        "human",
        """Write a detailed research report on the topic below.

Topic: {topic}

Research Gathered:
{research}

Structure the report as:
- Introduction
- Key Findings (minimum 3 well-explained points)
- Conclusion
- Sources (list all URLs found in the research)

Be detailed, factual and professional. If web search failed or
provided no sources, clearly disclose this and do not invent citations.""",
    ),
])

writer_chain = writer_prompt | llm | StrOutputParser()


# 4. Critic chain — original prompt preserved
critic_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a sharp and constructive research critic. "
        "Be honest and specific.",
    ),
    (
        "human",
        """Review the research report below and evaluate it strictly.

Report:
{report}

Respond in this exact format:

Score: X/10

Strengths:
- ...
- ...

Areas to Improve:
- ...
- ...

One line verdict:
...""",
    ),
])

critic_chain = critic_prompt | llm | StrOutputParser()
