"""
Show organizations pipeline.

Purpose:
- Return relevant organizations and projects for an explicit user category/topic.

Inputs:
- `user_id`, `chat_id`, `chat_type` for context and persistence.
- `category_message` containing the requested domain (for example climate, health).
- Optional `tg_message_id` for Telegram traceability.

Execution steps:
1. Ensure user/chat records exist.
2. Enrich category query text through LLM to improve semantic recall.
3. Convert enriched query into embedding vector.
4. Run nearest-neighbor search for organizations and projects.
5. Generate a baseline response (normal tone) from retrieved candidates.
6. Return text to orchestrator for tone filtering and persistence.

Failure behavior:
- Exceptions are logged with stack traces and return a safe retry message.
"""
import logging
from db import queries
from utils import llm

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
        _ = tg_message_id
        enriched = llm.enrich_query(category_message)
        emb = llm.get_embedding(enriched)
        orgs = queries.find_orgs_by_embedding(emb, top_n=5)
        projects = queries.find_projects_by_embedding(emb, top_n=5)
        reply = llm.generate_org_reply(category_message, orgs, projects, "normal")
        return reply
    except Exception as e:
        logger.error(f"show_orgs pipeline error: {e}", exc_info=True)
        return "⚠️ Зараз не вдалося знайти організації. Спробуй ще раз."
