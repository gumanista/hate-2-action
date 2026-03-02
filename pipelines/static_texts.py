"""
Static response pipelines.

These pipelines return deterministic text and do not call LLM/DB.
"""

from .shared import ABOUT_TEXT, START_TEXT


def pipeline_about_me() -> str:
    return ABOUT_TEXT


def pipeline_start() -> str:
    return START_TEXT
