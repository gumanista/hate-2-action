"""
Message orchestrator pipeline.

Flow:
1. Ensure user/chat records exist.
2. Detect intent pipeline from the incoming text.
3. Route to concrete pipeline implementation.
4. Persist message history with selected pipeline metadata.
"""

import logging
import re

from db import queries
from utils import llm

from .change_style import pipeline_change_style
from .problem_solution import pipeline_problem_solution
from .show_organizations import pipeline_show_orgs
from .shared import INTENT_PIPELINES
from .static_texts import pipeline_about_me

logger = logging.getLogger(__name__)


def _detect_pipeline_name(message_text: str) -> str:
    """Safely detect the intent pipeline. Fall back to process_message."""
    try:
        detected = llm.detect_pipeline(message_text)
    except Exception as e:
        logger.warning(f"Pipeline detection failed, defaulting to process_message: {e}")
        return "process_message"

    if not isinstance(detected, str):
        return "process_message"
    detected = detected.strip().lower()
    return detected if detected in INTENT_PIPELINES else "process_message"


def _needs_org_category_clarification(message_text: str) -> bool:
    """Detect if user asked to find orgs but did not provide a clear category."""
    cleaned = re.sub(r"[^\w\s]", " ", message_text.lower())
    tokens = [t for t in cleaned.split() if t]
    if len(tokens) <= 2:
        return True

    generic = {
        "show",
        "find",
        "org",
        "orgs",
        "organization",
        "organizations",
        "ngo",
        "ngos",
        "знайди",
        "покажи",
        "організація",
        "організації",
        "організацію",
        "нго",
    }
    return all(token in generic for token in tokens)


async def pipeline_process_message(
    user_id: int,
    chat_id: int,
    chat_type: str,
    message_text: str,
    tg_message_id: int = None,
) -> str:
    """
    Main message entrypoint:
    - classify intent via LLM
    - execute the appropriate pipeline
    """
    try:
        queries.get_or_create_user(user_id)
        queries.get_or_create_chat(chat_id, chat_type)

        pipeline_name = _detect_pipeline_name(message_text)
        logger.info(f"Detected pipeline: {pipeline_name} for user {user_id}")

        if pipeline_name == "about_me":
            reply = pipeline_about_me()
            queries.save_message(
                chat_id,
                user_id,
                message_text,
                reply,
                tg_message_id=tg_message_id,
                pipeline_used="about_me",
            )
            return reply

        if pipeline_name == "change_style":
            requested_style = llm.detect_style_from_message(message_text)
            reply = await pipeline_change_style(
                user_id,
                chat_id,
                chat_type,
                message=message_text,
                requested_style=requested_style,
            )
            queries.save_message(
                chat_id,
                user_id,
                message_text,
                reply,
                tg_message_id=tg_message_id,
                pipeline_used="change_style",
            )
            return reply

        if pipeline_name == "show_orgs":
            if _needs_org_category_clarification(message_text):
                reply = (
                    "🏢 Організації якої категорії тебе цікавлять?\n\n"
                    "Напиши тему, наприклад: клімат, корупція, освіта, здоровʼя."
                )
                queries.save_message(
                    chat_id,
                    user_id,
                    message_text,
                    reply,
                    tg_message_id=tg_message_id,
                    pipeline_used="show_orgs",
                )
                return reply

            return await pipeline_show_orgs(
                user_id,
                chat_id,
                chat_type,
                message_text,
                tg_message_id=tg_message_id,
            )

        return await pipeline_problem_solution(
            user_id,
            chat_id,
            chat_type,
            message_text,
            tg_message_id=tg_message_id,
        )

    except Exception as e:
        logger.error(f"process_message pipeline error: {e}", exc_info=True)
        return "⚠️ Під час обробки повідомлення сталася помилка. Спробуй ще раз."
