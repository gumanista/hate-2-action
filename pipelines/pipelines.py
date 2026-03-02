"""
Compatibility facade for all bot pipelines.

This module re-exports pipeline entrypoints so existing imports keep working
while implementations live in dedicated files.
"""

from .change_style import pipeline_change_style
from .message_orchestrator import pipeline_process_message
from .problem_solution import pipeline_problem_solution
from .shared import ABOUT_TEXT, START_TEXT, STYLES, STYLE_LABELS_UA
from .show_organizations import pipeline_show_orgs
from .static_texts import pipeline_about_me, pipeline_start

__all__ = [
    "pipeline_process_message",
    "pipeline_problem_solution",
    "pipeline_show_orgs",
    "pipeline_change_style",
    "pipeline_about_me",
    "pipeline_start",
    "STYLES",
    "STYLE_LABELS_UA",
    "ABOUT_TEXT",
    "START_TEXT",
]
