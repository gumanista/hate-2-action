"""
Show organizations pipeline.

Flow:
1. Enrich user's category query.
2. Run semantic similarity search over organizations/projects.
3. Generate a concise recommendation reply in selected style.
"""

import logging

from db import queries
from utils import llm

from .change_style import resolve_style

logger = logging.getLogger(__name__)


async def pipeline_show_orgs(
    user_id: int,
    chat_id: int,
    chat_type: str,
    category_message: str,
    tg_message_id: int = None,
) -> str:
    """Find organizations by user-specified category."""
    try:
        queries.get_or_create_user(user_id)
        queries.get_or_create_chat(chat_id, chat_type)
        style = resolve_style(user_id, chat_id)

        enriched = llm.enrich_query(category_message)
        emb = llm.get_embedding(enriched)

        orgs = queries.find_orgs_by_embedding(emb, top_n=5)
        projects = queries.find_projects_by_embedding(emb, top_n=5)

        reply = llm.generate_org_reply(category_message, orgs, projects, style)
        queries.save_message(
            chat_id,
            user_id,
            category_message,
            reply,
            tg_message_id=tg_message_id,
            pipeline_used="show_orgs",
        )
        return reply
    except Exception as e:
        logger.error(f"show_orgs pipeline error: {e}", exc_info=True)
        return "⚠️ Зараз не вдалося знайти організації. Спробуй ще раз."
