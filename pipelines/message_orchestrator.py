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
# Build allowed intent set directly from factory registry to avoid duplication.
INTENT_PIPELINES = PIPELINE_FACTORY.intents


# Apply response style rewrite unless pipeline/style rules say to skip it.
def _apply_style_filter(reply: str, style: str, pipeline_name: str) -> str:
    # Keep empty/None replies unchanged.
    if not reply:
        return reply
    # Never rewrite style-configuration replies for clarity and idempotence.
    if pipeline_name == "change_style":
        return reply
    # Skip extra rewrite cost when selected style is neutral.
    if style == "normal":
        return reply
    try:
        # Ask LLM to rewrite text in target style while preserving meaning.
        return llm.rewrite_reply_with_style(reply, style)
    except Exception as e:
        # Fail open on rewrite errors and keep original reply.
        logger.warning(f"Style filter failed for pipeline={pipeline_name}: {e}")
        return reply


# Safely map incoming text to a known pipeline name.
def _detect_pipeline_name(message_text: str) -> str:
    """Safely detect the intent pipeline. Fall back to process_message."""
    try:
        # Run LLM intent classification for the user message.
        detected = llm.detect_pipeline(message_text)
    except Exception as e:
        # Log classifier failure and degrade gracefully to default pipeline.
        logger.warning(
            f"Pipeline detection failed, defaulting to process_message: {e}"
        )
        return "process_message"

    # Guard against malformed non-string output from classifier.
    if not isinstance(detected, str):
        return "process_message"
    # Normalize output token before validation.
    detected = detected.strip().lower()
    # Return only known intents; otherwise fallback to default pipeline.
    return detected if detected in INTENT_PIPELINES else "process_message"


# Main orchestrator entrypoint called by Telegram adapter layer.
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

        # Respect forced pipeline when valid; otherwise detect intent from text.
        pipeline_name = (
            # Use explicit pipeline provided by caller when it is recognized.
            forced_pipeline.strip().lower()
            if isinstance(forced_pipeline, str)
            and forced_pipeline.strip().lower() in INTENT_PIPELINES
            # Fallback to automatic detection when no valid override exists.
            else _detect_pipeline_name(message_text)
        )
        # Log resolved pipeline choice for debugging/analytics.
        logger.info(f"Detected pipeline: {pipeline_name} for user {user_id}")
        # Compute effective response style once per request.
        style = resolve_style(user_id, chat_id)

        # Package request context for pipeline interface.
        context = PipelineContext(
            user_id=user_id,
            chat_id=chat_id,
            chat_type=chat_type,
            message_text=message_text,
            tg_message_id=tg_message_id,
        )
        # Instantiate concrete pipeline implementation via factory registry.
        pipeline = PIPELINE_FACTORY.create(pipeline_name)
        # Execute selected pipeline and collect structured result metadata.
        result = await pipeline.run(context)

        # Apply style rewrite only when pipeline result allows it.
        reply = (
            # Rewrite response into selected style.
            _apply_style_filter(result.reply, style, result.pipeline_used)
            # Branch condition: rewrite only when pipeline allows post-processing.
            if result.apply_style_filter
            # Keep pipeline output unchanged when post-processing is disabled.
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
