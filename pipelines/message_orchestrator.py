"""
Message orchestrator pipeline.

Purpose:
- Serve as the single entrypoint for incoming user text.
- Select pipeline intent and delegate execution to a factory-created handler.
"""

import logging

from db import queries
from utils import llm

from .change_style import resolve_style
from .pipeline_factory import PipelineContext, PipelineFactory

logger = logging.getLogger(__name__)

PIPELINE_FACTORY = PipelineFactory()
INTENT_PIPELINES = PIPELINE_FACTORY.intents


def _apply_style_filter(reply: str, style: str, pipeline_name: str) -> str:
    if not reply:
        return reply
    if pipeline_name == "change_style":
        return reply
    if style == "normal":
        return reply
    try:
        return llm.rewrite_reply_with_style(reply, style)
    except Exception as e:
        logger.warning(f"Style filter failed for pipeline={pipeline_name}: {e}")
        return reply


def _detect_pipeline_name(
    message_text: str,
    last_message_context: dict | None = None,
) -> str:
    """Safely detect the intent pipeline. Fall back to problem_solution."""
    try:
        detected = llm.detect_pipeline(
            message_text,
            previous_message=(
                last_message_context.get("message_text")
                if isinstance(last_message_context, dict)
                else None
            ),
            previous_reply=(
                last_message_context.get("reply_text")
                if isinstance(last_message_context, dict)
                else None
            ),
            previous_pipeline=(
                last_message_context.get("pipeline_used")
                if isinstance(last_message_context, dict)
                else None
            ),
        )
    except Exception as e:
        logger.warning(
            f"Pipeline detection failed, defaulting to problem_solution: {e}"
        )
        return "problem_solution"
    if not isinstance(detected, str):
        return "problem_solution"
    detected = detected.strip().lower()
    if detected == "process_message":
        detected = "problem_solution"
    return detected if detected in INTENT_PIPELINES else "problem_solution"


def _get_last_message_context(chat_id: int, user_id: int) -> dict | None:
    try:
        context = queries.get_last_message_context(chat_id, user_id)
    except Exception as e:
        logger.warning(f"Could not load last message context for routing: {e}")
        return None
    return context if isinstance(context, dict) else None


async def pipeline_process_message(
    user_id: int,
    chat_id: int,
    chat_type: str,
    message_text: str,
    tg_message_id: int = None,
    forced_pipeline: str | None = None,
) -> str:
    """
    Main message entrypoint:
    - classify intent via LLM or explicit command override
    - execute selected pipeline through factory
    - apply style filter and persist response
    """
    try:
        queries.get_or_create_user(user_id)
        queries.get_or_create_chat(chat_id, chat_type)
        last_message_context = _get_last_message_context(chat_id, user_id)
        pipeline_name = (
            forced_pipeline.strip().lower()
            if isinstance(forced_pipeline, str)
            and forced_pipeline.strip().lower() in INTENT_PIPELINES
            else _detect_pipeline_name(
                message_text=message_text,
                last_message_context=last_message_context,
            )
        )
        logger.info(f"Detected pipeline: {pipeline_name} for user {user_id}")
        style = resolve_style(user_id, chat_id)
        context = PipelineContext(
            user_id=user_id,
            chat_id=chat_id,
            chat_type=chat_type,
            message_text=message_text,
            tg_message_id=tg_message_id,
        )
        pipeline = PIPELINE_FACTORY.create(pipeline_name)
        result = await pipeline.run(context)
        reply = (
            _apply_style_filter(result.reply, style, result.pipeline_used)
            if result.apply_style_filter
            else result.reply
        )
        queries.save_message(
            chat_id,
            user_id,
            message_text,
            reply,
            tg_message_id=tg_message_id,
            pipeline_used=result.pipeline_used,
        )
        return reply

    except Exception as e:
        logger.error(f"problem_solution pipeline error: {e}", exc_info=True)
        return "⚠️ Під час обробки повідомлення сталася помилка. Спробуй ще раз."
