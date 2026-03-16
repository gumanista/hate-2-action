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
def _detect_pipeline_name(message_text: str) -> str:
    """Safely detect the intent pipeline. Fall back to process_message."""
    try:
        detected = llm.detect_pipeline(message_text)
    except Exception as e:
        logger.warning(
            f"Pipeline detection failed, defaulting to process_message: {e}"
        )
        return "process_message"
    if not isinstance(detected, str):
        return "process_message"
    detected = detected.strip().lower()
    return detected if detected in INTENT_PIPELINES else "process_message"
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
        pipeline_name = (
            forced_pipeline.strip().lower()
            if isinstance(forced_pipeline, str)
            and forced_pipeline.strip().lower() in INTENT_PIPELINES
            else _detect_pipeline_name(message_text)
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
        logger.error(f"process_message pipeline error: {e}", exc_info=True)
        return "⚠️ Під час обробки повідомлення сталася помилка. Спробуй ще раз."
