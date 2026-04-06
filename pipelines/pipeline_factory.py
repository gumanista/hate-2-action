"""
Pipeline factory and concrete pipeline handlers.

Purpose:
- Encapsulate pipeline creation and execution contracts behind a factory pattern.
- Keep pipeline-specific behavior out of message orchestrator routing glue.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable

from utils import llm

from .change_style import pipeline_change_style
from .problem_solution import pipeline_problem_solution
from .show_organizations import pipeline_show_orgs
ABOUT_TEXT = {
    "uk": (
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
    ),
    "en": (
        "👋 *Hate-2-Action Bot*\n\n"
        "I turn your frustration into action! 💪\n\n"
        "Tell me what bothers you — corruption, climate, inequality or anything else — "
        "and I'll suggest NGOs and projects that are actually working on it.\n\n"
        "*Commands:*\n"
        "• /start — Get started\n"
        "• /style — Change response style (polite/funny/sarcastic/normal/rude)\n"
        "• /orgs — Search organizations by category\n"
        "• /about — What I can do\n\n"
        "Just tell me what's wrong, and I'll help channel your energy into action. 🔥"
    ),
}

START_TEXT = {
    "uk": (
        "🚀 *Привіт! Я Hate-2-Action Bot!*\n\n"
        "Є щось у світі, що тебе дратує? Розкажи мені.\n"
        "Я вислухаю і підкажу людей та ініціативи, які вже працюють над "
        "розвʼязанням проблеми.\n\n"
        "Просто опиши проблему, і я знайду релевантні НГО та проєкти.\n\n"
        "Або скористайся /orgs для пошуку організацій, /style для зміни тону, "
        "або /about щоб дізнатись більше."
    ),
    "en": (
        "🚀 *Hi! I'm Hate-2-Action Bot!*\n\n"
        "Is there something in the world that frustrates you? Tell me about it.\n"
        "I'll listen and suggest people and initiatives that are already working on "
        "solving the problem.\n\n"
        "Just describe the issue, and I'll find relevant NGOs and projects.\n\n"
        "Or use /orgs to search organizations, /style to change the tone, "
        "or /about to learn more."
    ),
}


def pipeline_about_me(lang: str = "uk") -> str:
    return ABOUT_TEXT.get(lang, ABOUT_TEXT["uk"])


def pipeline_start(lang: str = "uk") -> str:
    return START_TEXT.get(lang, START_TEXT["uk"])


@dataclass(slots=True, frozen=True)
class PipelineContext:
    user_id: int
    chat_id: int
    chat_type: str
    message_text: str
    tg_message_id: int | None = None
    lang: str = "uk"


@dataclass(slots=True, frozen=True)
class PipelineResult:
    reply: str
    pipeline_used: str
    apply_style_filter: bool = True


class BasePipeline(ABC):
    name: str

    @abstractmethod
    async def run(self, ctx: PipelineContext) -> PipelineResult:
        raise NotImplementedError


class AboutPipeline(BasePipeline):
    name = "about_me"
    async def run(self, ctx: PipelineContext) -> PipelineResult:
        return PipelineResult(reply=pipeline_about_me(ctx.lang), pipeline_used=self.name)


class StartPipeline(BasePipeline):
    name = "start"
    async def run(self, ctx: PipelineContext) -> PipelineResult:
        return PipelineResult(reply=pipeline_start(ctx.lang), pipeline_used=self.name)


class ChangeStylePipeline(BasePipeline):
    name = "change_style"
    async def run(self, ctx: PipelineContext) -> PipelineResult:
        requested_style = llm.detect_style_from_message(ctx.message_text)
        reply = await pipeline_change_style(
            ctx.user_id,
            ctx.chat_id,
            ctx.chat_type,
            message=ctx.message_text,
            requested_style=requested_style,
            lang=ctx.lang,
        )
        return PipelineResult(
            reply=reply,
            pipeline_used=self.name,
            apply_style_filter=False,
        )


class ShowOrgsPipeline(BasePipeline):
    name = "show_orgs"
    async def run(self, ctx: PipelineContext) -> PipelineResult:
        reply = await pipeline_show_orgs(
            ctx.user_id,
            ctx.chat_id,
            ctx.chat_type,
            ctx.message_text,
            tg_message_id=ctx.tg_message_id,
            lang=ctx.lang,
        )
        return PipelineResult(reply=reply, pipeline_used=self.name)


class ProcessMessagePipeline(BasePipeline):
    name = "problem_solution"

    async def run(self, ctx: PipelineContext) -> PipelineResult:
        reply = await pipeline_problem_solution(
            ctx.user_id,
            ctx.chat_id,
            ctx.chat_type,
            ctx.message_text,
            tg_message_id=ctx.tg_message_id,
            lang=ctx.lang,
        )
        return PipelineResult(reply=reply, pipeline_used=self.name)


class PipelineFactory:
    def __init__(self):
        self._registry: dict[str, Callable[[], BasePipeline]] = {
            "about_me": AboutPipeline,
            "start": StartPipeline,
            "change_style": ChangeStylePipeline,
            "show_orgs": ShowOrgsPipeline,
            "problem_solution": ProcessMessagePipeline,
            "process_message": ProcessMessagePipeline,
        }
    @property
    def intents(self) -> set[str]:
        return set(self._registry.keys())
    def create(self, pipeline_name: str) -> BasePipeline:
        builder = self._registry.get(
            pipeline_name,
            self._registry["problem_solution"],
        )
        return builder()
