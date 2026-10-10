
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from tools import web_search, scrape_url

load_dotenv()

api_key = os.getenv("LLM_MODEL_API_KEY")
if not api_key:
    raise ValueError("LLM_MODEL_API_KEY is not configured.")

llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL_NAME", "gemini-3.8-flash"),
    api_key=api_key,
    base_url=os.getenv(
        "LLM_MODEL_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    ),
    temperature=0,
)


def build_search_agent():
    return create_agent(
        model=llm,
        tools=[web_search],
    )


def build_reader_agent():
    return create_agent(
        model=llm,
        tools=[scrape_url],
    )


writer_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are an expert research writer. "
        "Write clear, structured and insightful reports.",
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

Be detailed, factual and professional.""",
    ),
])

writer_chain = writer_prompt | llm | StrOutputParser()


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
