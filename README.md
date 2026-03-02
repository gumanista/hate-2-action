# 🔥 Hate-2-Action Bot

A Telegram bot that turns complaints into action by recommending NGOs and projects.

## How It Works

1. User sends a complaint/rant to the bot
2. LLM extracts the underlying **problems** and **solution concepts**
3. Vector similarity search finds matching **organizations** and **projects**
4. Bot replies with a styled, structured message (validation → guidance → encouragement)

## Pipelines

| Pipeline | Trigger | What it does |
|---|---|---|
| `process_message` | Any complaint/rant | Extracts problems → finds orgs → generates styled reply |
| `show_orgs` | `/orgs` or asking for orgs | Direct org search by category |
| `change_style` | `/style` or style-related message | Updates user's tone preference |
| `about_me` | `/about` | Bot description |
| `start` | `/start` | Welcome message |

## Response Styles

`polite` · `funny` · `sarcastic` · `normal` · `rude`

Style priority: **user preference > chat preference > default (normal)**

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector)
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API Key

### Option A: Docker (recommended)

```bash
cp .env.example .env
# Fill in TELEGRAM_BOT_TOKEN and OPENAI_API_KEY in .env

docker-compose up -d db
sleep 5
docker-compose run bot python init_db.py
docker-compose up bot
```

### Option B: Local

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up environment
cp .env.example .env
# Edit .env with your credentials

# 3. Initialize database (creates tables, seeds data, generates embeddings)
python init_db.py

# 4. Run the bot
python bot/main.py
```

## Project Structure

```
hate2action/
├── bot/
│   └── main.py              # Telegram bot handlers
├── db/
│   ├── queries.py           # All database operations
│   ├── schema.sql           # Table definitions
│   └── seed.sql             # Initial organizations, projects, problems, solutions
├── pipelines/
│   ├── message_orchestrator.py  # Intent routing + start/about pipelines
│   ├── problem_solution.py      # Main complaint-to-action pipeline
│   ├── show_organizations.py    # Organization search pipeline
│   └── change_style.py          # Style configuration pipeline
├── utils/
│   └── llm.py               # OpenAI API helpers (embeddings, LLM calls)
├── tests/
│   └── test_pipelines.py    # Unit tests (no DB/API required)
├── init_db.py               # One-time DB setup + embedding generation
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Database Schema

```
users           → user preferences (style)
chats           → chat preferences
messages_history → full conversation log
organizations   → NGOs (manually verified)
projects        → specific NGO projects (manually verified)
problems        → extracted problem concepts (AI generated)
solutions       → solution concepts (AI generated)
*_vec           → embedding tables for each entity
problems_solutions     → problem ↔ solution similarity
projects_solutions     → project ↔ solution similarity
organizations_solutions → org ↔ solution similarity
```

## Running Tests

```bash
python -m pytest tests/ -v
# or
python tests/test_pipelines.py
```

Tests mock all DB and LLM calls — no credentials needed.

## Adding Organizations

Manually insert into the `organizations` and `projects` tables, then re-run embedding:

```python
from utils.llm import get_embedding
from db.queries import db_cursor

with db_cursor() as cur:
    cur.execute("INSERT INTO organizations (name, description, website) VALUES (%s, %s, %s) RETURNING organization_id",
                ("New Org", "Description", "https://example.org"))
    org_id = cur.fetchone()["organization_id"]
    emb = get_embedding("New Org: Description")
    emb_str = "[" + ",".join(str(v) for v in emb) + "]"
    cur.execute("INSERT INTO organizations_vec (organization_id, text_to_embed, embedding) VALUES (%s, %s, %s::vector)",
                (org_id, "New Org: Description", emb_str))
```

## MVP Checklist

- [x] Database schema with all tables
- [x] Seed data (organizations, projects, problems, solutions)
- [x] Embedding generation + storage
- [x] Similarity computation (problems↔solutions↔orgs/projects)
- [x] `process_message` pipeline with deduplication
- [x] `show_orgs` pipeline
- [x] `change_style` pipeline
- [x] `start` and `about_me` pipelines
- [x] Conversation memory (messages_history)
- [x] Style priority resolution (user > chat > default)
- [x] Group chat support (mention-triggered)
- [x] Inline keyboard buttons in DM
- [x] Unit tests for all evaluation factors
