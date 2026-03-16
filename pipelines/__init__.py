"""
Pipelines package exports.

Purpose:
- Provide a stable import surface for all pipeline entrypoints, constants,
  and helper functions used by the bot application.

Design:
- Each concrete pipeline lives in its own module.
- This file re-exports selected symbols and defines `__all__` so callers can
  import from `pipelines` without needing module-level knowledge.
"""
from .change_style import STYLES, STYLE_LABELS_UA, pipeline_change_style, resolve_style
from .message_orchestrator import pipeline_process_message
from .pipeline_factory import (
    ABOUT_TEXT,
    START_TEXT,
    pipeline_about_me,
    pipeline_start,
)
from .problem_solution import pipeline_problem_solution
from .show_organizations import pipeline_show_orgs
__all__ = [
    "pipeline_process_message",
    "pipeline_problem_solution",
    "pipeline_show_orgs",
    "pipeline_change_style",
    "pipeline_about_me",
    "pipeline_start",
    "resolve_style",
    "STYLES",
    "STYLE_LABELS_UA",
    "ABOUT_TEXT",
    "START_TEXT",
]
