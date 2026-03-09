"""
Pipeline factory and concrete pipeline handlers.

Purpose:
- Encapsulate pipeline creation and execution contracts behind a factory pattern.
- Keep pipeline-specific behavior out of message orchestrator routing glue.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from utils import llm

from .change_style import pipeline_change_style
from .problem_solution import pipeline_problem_solution
from .show_organizations import pipeline_show_orgs

# Static text response for the about pipeline.
ABOUT_TEXT = (
    "👋 *Hate-2-Action Bot*\n\n"
    "Перетворюю твоє обурення на дію! 💪\n\n"
    "Напиши, що тебе бісить — корупція, клімат, нерівність чи будь-що інше — "
    "і я підкажу НГО та проєкти, які реально цим займаються.\n\n"
    "*Команди:*\n"
    "• /start — Почати\n"
    "• /style — Змінити стиль відповіді (polite/funny/sarcastic/normal/rude)\n"
    "• /orgs — Пошук організацій за категорією\n"
    "• /about — Що я вмію\n\n"
    "Просто напиши, що болить, а я допоможу спрямувати енергію в дію. 🔥"
)

START_TEXT = (
    "🚀 *Привіт! Я Hate-2-Action Bot!*\n\n"
    "Є щось у світі, що тебе дратує? Розкажи мені.\n"
    "Я вислухаю і підкажу людей та ініціативи, які вже працюють над "
    "розвʼязанням проблеми.\n\n"
    "Просто опиши проблему, і я знайду релевантні НГО та проєкти.\n\n"
    "Або скористайся /orgs для пошуку організацій, /style для зміни тону, "
    "або /about щоб дізнатись більше."
)


# Public helper that returns static about text.
def pipeline_about_me() -> str:
    return ABOUT_TEXT


# Public helper that returns static start text.
def pipeline_start() -> str:
    return START_TEXT


# Define immutable context object that all pipeline handlers receive.
@dataclass(slots=True, frozen=True)
class PipelineContext:
    user_id: int
    chat_id: int
    chat_type: str
    message_text: str
    tg_message_id: int | None = None


# Define immutable result object returned by each concrete pipeline.
@dataclass(slots=True, frozen=True)
class PipelineResult:
    # User-facing text produced by pipeline.
    reply: str
    # Canonical pipeline identifier used in analytics/persistence.
    pipeline_used: str
    # Whether orchestrator should apply global style rewrite post-processing.
    apply_style_filter: bool = True


# Define common interface that all factory pipelines must implement.
class BasePipeline(ABC):
    # Canonical pipeline name each implementation declares.
    name: str

    # Abstract execution contract implemented by concrete pipelines.
    @abstractmethod
    async def run(self, ctx: PipelineContext) -> PipelineResult:
        # Force subclasses to provide implementation.
        raise NotImplementedError


# Concrete pipeline for static about response.
class AboutPipeline(BasePipeline):
    # Name used by router/factory for this handler.
    name = "about_me"

    # Execute about handler with shared pipeline interface.
    async def run(self, ctx: PipelineContext) -> PipelineResult:
        # Mark input as intentionally unused for this static response.
        _ = ctx
        # Return static about text with pipeline metadata.
        return PipelineResult(reply=pipeline_about_me(), pipeline_used=self.name)


# Concrete pipeline for static start response.
class StartPipeline(BasePipeline):
    # Name used by router/factory for this handler.
    name = "start"

    # Execute start handler with shared pipeline interface.
    async def run(self, ctx: PipelineContext) -> PipelineResult:
        # Mark input as intentionally unused for this static response.
        _ = ctx
        # Return static start text with pipeline metadata.
        return PipelineResult(reply=pipeline_start(), pipeline_used=self.name)


# Concrete pipeline for style configuration messages.
class ChangeStylePipeline(BasePipeline):
    # Name used by router/factory for this handler.
    name = "change_style"

    # Execute style-change flow and return confirmation/help text.
    async def run(self, ctx: PipelineContext) -> PipelineResult:
        # Extract requested style intent from user message when possible.
        requested_style = llm.detect_style_from_message(ctx.message_text)
        reply = await pipeline_change_style(
            ctx.user_id,
            ctx.chat_id,
            ctx.chat_type,
            message=ctx.message_text,
            requested_style=requested_style,
        )
        # Return pipeline result with style filter disabled to avoid rewriting config text.
        return PipelineResult(
            reply=reply,
            pipeline_used=self.name,
            apply_style_filter=False,
        )


# Helper that decides whether show-orgs request is too vague and needs clarification.
def _needs_org_category_clarification(message_text: str) -> bool:
    """Detect if user asked to find orgs but did not provide a clear category."""
    # Normalize punctuation/case to simplify token-level heuristics.
    cleaned = re.sub(r"[^\w\s]", " ", message_text.lower())
    # Tokenize on whitespace and discard empty tokens.
    tokens = [t for t in cleaned.split() if t]
    # Empty input cannot be searched meaningfully.
    if not tokens:
        return True

    # Generic command tokens that indicate "find orgs" intent without topic detail.
    generic = {
        # English generic query tokens.
        "show",
        "find",
        "org",
        "orgs",
        "organization",
        "organizations",
        "ngo",
        "ngos",
        "category",
        "topic",
        "please",
        # Ukrainian generic query tokens.
        "знайди",
        "покажи",
        "які",
        "яка",
        "якої",
        "мені",
        "тема",
        "теми",
        "категорія",
        "категорії",
        "організація",
        "організації",
        "організацію",
        "організацій",
        "нго",
    }
    # Clarify when every token is generic (meaning no domain/category token found).
    return all(token in generic for token in tokens)


# Concrete pipeline for organization lookup flow.
class ShowOrgsPipeline(BasePipeline):
    # Name used by router/factory for this handler.
    name = "show_orgs"

    # Execute show-orgs flow, including ambiguity guard.
    async def run(self, ctx: PipelineContext) -> PipelineResult:
        # Ask for category detail before retrieval when user query is too generic.
        if _needs_org_category_clarification(ctx.message_text):
            return PipelineResult(
                # Clarification prompt shown to user.
                reply=(
                    "🏢 Організації якої категорії тебе цікавлять?\n\n"
                    "Напиши тему, наприклад: клімат, корупція, освіта, здоровʼя."
                ),
                # Keep pipeline marker as show_orgs for analytics continuity.
                pipeline_used=self.name,
            )

        # Delegate to existing organizations retrieval pipeline.
        reply = await pipeline_show_orgs(
            ctx.user_id,
            ctx.chat_id,
            ctx.chat_type,
            ctx.message_text,
            tg_message_id=ctx.tg_message_id,
        )
        return PipelineResult(reply=reply, pipeline_used=self.name)


class ProcessMessagePipeline(BasePipeline):
    name = "process_message"

    async def run(self, ctx: PipelineContext) -> PipelineResult:
        reply = await pipeline_problem_solution(
            ctx.user_id,
            ctx.chat_id,
            ctx.chat_type,
            # Forward original user message text.
            ctx.message_text,
            # Forward optional Telegram message id for traceability.
            tg_message_id=ctx.tg_message_id,
        )
        # Return generated recommendation reply with pipeline metadata.
        return PipelineResult(reply=reply, pipeline_used=self.name)


# Factory responsible for creating concrete pipeline handlers by name.
class PipelineFactory:
    def __init__(self):
        self._registry: dict[str, Callable[[], BasePipeline]] = {
            "about_me": AboutPipeline,
            "start": StartPipeline,
            "change_style": ChangeStylePipeline,
            "show_orgs": ShowOrgsPipeline,
            "process_message": ProcessMessagePipeline,
        }

    # Expose available intents for validation and detection guards.
    @property
    def intents(self) -> set[str]:
        return set(self._registry.keys())

    # Create a concrete pipeline instance by name, with safe default fallback.
    def create(self, pipeline_name: str) -> BasePipeline:
        builder = self._registry.get(pipeline_name, self._registry["process_message"])
        return builder()
