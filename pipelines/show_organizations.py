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
2. Resolve response style (`resolve_style`) for consistent tone.
3. Enrich category query text through LLM to improve semantic recall.
4. Convert enriched query into embedding vector.
5. Run nearest-neighbor search for organizations and projects.
6. Generate a concise styled response from retrieved candidates.
7. Persist request/reply pair with `pipeline_used="show_orgs"`.

Failure behavior:
- Exceptions are logged with stack traces and return a safe retry message.
"""

# Import logging for structured error reporting.
import logging

# Import database access helpers for user/chat/message persistence and search.
from db import queries
# Import LLM helpers for query enrichment, embeddings, and reply generation.
from utils import llm

# Reuse style resolution logic to keep answer tone consistent.
from .change_style import resolve_style

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
        # Determine active response style (user override -> chat fallback -> normal).
        style = resolve_style(user_id, chat_id)

        # Expand/clarify short category message to improve semantic retrieval quality.
        enriched = llm.enrich_query(category_message)
        # Convert enriched query text into embedding vector for similarity search.
        emb = llm.get_embedding(enriched)

        # Retrieve nearest organizations by vector similarity.
        orgs = queries.find_orgs_by_embedding(emb, top_n=5)
        # Retrieve nearest projects by vector similarity.
        projects = queries.find_projects_by_embedding(emb, top_n=5)

        # Generate final response text from matches in requested tone/style.
        reply = llm.generate_org_reply(category_message, orgs, projects, style)
        # Persist user input and bot reply for history/analytics.
        queries.save_message(
            # Chat context id.
            chat_id,
            # User context id.
            user_id,
            # Original message text from user.
            category_message,
            # Final reply produced by LLM.
            reply,
            # Telegram message identifier if provided.
            tg_message_id=tg_message_id,
            # Pipeline marker for later debugging/metrics.
            pipeline_used="show_orgs",
        )
        # Return generated reply to caller.
        return reply
    except Exception as e:
        # Log full error with stack trace for diagnostics.
        logger.error(f"show_orgs pipeline error: {e}", exc_info=True)
        # Return safe user-facing fallback error message.
        return "⚠️ Зараз не вдалося знайти організації. Спробуй ще раз."
