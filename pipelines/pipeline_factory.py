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
def pipeline_about_me() -> str:
    return ABOUT_TEXT
def pipeline_start() -> str:
    return START_TEXT
@dataclass(slots=True, frozen=True)
class PipelineContext:
    user_id: int
    chat_id: int
    chat_type: str
    message_text: str
    tg_message_id: int | None = None
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
        _ = ctx
        return PipelineResult(reply=pipeline_about_me(), pipeline_used=self.name)
class StartPipeline(BasePipeline):
    name = "start"
    async def run(self, ctx: PipelineContext) -> PipelineResult:
        _ = ctx
        return PipelineResult(reply=pipeline_start(), pipeline_used=self.name)
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
