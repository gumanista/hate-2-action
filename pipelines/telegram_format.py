"""
Telegram legacy Markdown compatibility helpers.

Purpose:
- Telegram's ParseMode.MARKDOWN (legacy Markdown) has no concept of ATX
  headers (`#`, `##`, `###`, ...). LLM-generated replies sometimes use
  headers for structure, which Telegram then renders as literal `#`
  characters instead of formatting them.

Execution steps:
- `sanitize_markdown` rewrites header lines into bold text (`*text*`),
  which Telegram's legacy Markdown does support, preserving the visual
  emphasis the header was going for.
"""

import re

_HEADER_RE = re.compile(r"^(\s*)#{1,6}\s*(.+?)\s*$")


def sanitize_markdown(text: str) -> str:
    """Rewrite Markdown ATX headers into Telegram-compatible bold text."""
    if not text:
        return text
    lines = text.split("\n")
    for i, line in enumerate(lines):
        match = _HEADER_RE.match(line)
        if match:
            indent, content = match.groups()
            lines[i] = f"{indent}*{content}*"
    return "\n".join(lines)
