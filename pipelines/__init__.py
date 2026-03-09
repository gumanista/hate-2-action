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

# Re-export style constants and style pipeline helpers.
from .change_style import STYLES, STYLE_LABELS_UA, pipeline_change_style, resolve_style
# Re-export orchestrator top-level message entrypoint.
from .message_orchestrator import pipeline_process_message
# Re-export static text helpers from factory module.
from .pipeline_factory import (
    # Static text used by about command.
    ABOUT_TEXT,
    # Static text used by start command.
    START_TEXT,
    # Function that returns ABOUT_TEXT.
    pipeline_about_me,
    # Function that returns START_TEXT.
    pipeline_start,
)
# Re-export core problem-solution pipeline.
from .problem_solution import pipeline_problem_solution
# Re-export organization lookup pipeline.
from .show_organizations import pipeline_show_orgs

# Public API of this package for wildcard imports and discoverability.
__all__ = [
    # Main message routing entrypoint.
    "pipeline_process_message",
    # Core recommendation pipeline.
    "pipeline_problem_solution",
    # Organization search pipeline.
    "pipeline_show_orgs",
    # Style change pipeline.
    "pipeline_change_style",
    # About text helper.
    "pipeline_about_me",
    # Start text helper.
    "pipeline_start",
    # Style resolution helper.
    "resolve_style",
    # Supported style keys list.
    "STYLES",
    # Localized style labels mapping.
    "STYLE_LABELS_UA",
    # About command text constant.
    "ABOUT_TEXT",
    # Start command text constant.
    "START_TEXT",
]
