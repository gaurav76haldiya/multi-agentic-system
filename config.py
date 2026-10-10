
import os
from dataclasses import dataclass

import streamlit as st


class ConfigurationError(Exception):
    pass


def get_setting(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value.strip()

    try:
        value = st.secrets.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    except Exception:
        pass

    return default


@dataclass(frozen=True)
class AppConfig:
    gemini_api_key: str
    gemini_model: str
    freesea_api_key: str
    max_results: int
    max_tokens: int


def get_config() -> AppConfig:
    gemini_key = get_setting("LLM_MODEL_API_KEY")
    freesea_key = get_setting("FREESEA_API_KEY")

    missing = []
    if not gemini_key:
        missing.append("LLM_MODEL_API_KEY")
    if not freesea_key:
        missing.append("FREESEA_API_KEY")

    if missing:
        raise ConfigurationError(
            "Missing settings: " + ", ".join(missing)
        )

    try:
        max_results = int(get_setting("SEARCH_MAX_RESULTS", "5"))
        max_tokens = int(get_setting("LLM_MAX_TOKENS", "3500"))
    except ValueError as exc:
        raise ConfigurationError(
            "SEARCH_MAX_RESULTS and LLM_MAX_TOKENS must be integers."
        ) from exc

    return AppConfig(
        gemini_api_key=gemini_key,
        gemini_model=get_setting(
            "LLM_MODEL_NAME", "gemini-3.8-flash"
        ),
        freesea_api_key=freesea_key,
        max_results=max(1, min(max_results, 10)),
        max_tokens=max(500, min(max_tokens, 8000)),
    )
