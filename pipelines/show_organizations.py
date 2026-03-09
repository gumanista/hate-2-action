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

# Import logging for structured error reporting.
import logging

# Import database access helpers for user/chat/message persistence and search.
from db import queries
# Import LLM helpers for query enrichment, embeddings, and reply generation.
from utils import llm

# Create module-level logger instance.
logger = logging.getLogger(__name__)


# TODO: response style is applied by message orchestrator,
# Message orchestrator is responsible for llm call to generate the final message output.
# Uses styles as the filters.

# Pipeline that returns organizations/projects relevant to a requested category.
async def pipeline_show_orgs(
    # Telegram user identifier.
    user_id: int,
    # Telegram chat identifier.
    chat_id: int,
    # Telegram chat type (private/group/etc).
    chat_type: str,
    # Raw user message containing desired category/topic.
    category_message: str,
    # Optional Telegram message id for traceability in storage.
    tg_message_id: int = None,
) -> str:
    """Find organizations by user-specified category."""
    try:
        # Ensure user exists before saving/querying related data.
        queries.get_or_create_user(user_id)
        # Ensure chat exists before saving/querying related data.
        queries.get_or_create_chat(chat_id, chat_type)
        # Message persistence is handled by message orchestrator.
        _ = tg_message_id

        # Expand/clarify short category message to improve semantic retrieval quality.
        enriched = llm.enrich_query(category_message)
        # Convert enriched query text into embedding vector for similarity search.
        emb = llm.get_embedding(enriched)

        # Retrieve nearest organizations by vector similarity.
        orgs = queries.find_orgs_by_embedding(emb, top_n=5)
        # Retrieve nearest projects by vector similarity.
        projects = queries.find_projects_by_embedding(emb, top_n=5)

        # Tone/style post-processing is applied by message orchestrator.
        reply = llm.generate_org_reply(category_message, orgs, projects, "normal")
        return reply
    except Exception as e:
        logger.error(f"show_orgs pipeline error: {e}", exc_info=True)
        return "⚠️ Зараз не вдалося знайти організації. Спробуй ще раз."
