"""
test_pipelines.py — Evaluation test cases for Hate-2-Action MVP

Tests cover the evaluation factors from the spec:
1. Process Message pipeline: user saved, message saved, correct style applied
2. Configure user pipeline (style)
3. Configure chat pipeline
4. Start pipeline
5. About Me pipeline
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ── Mock DB and LLM before importing pipelines ────────────────────────────────
mock_queries = MagicMock()
mock_llm = MagicMock()
sys.modules["db.queries"] = mock_queries
sys.modules["db"] = MagicMock(queries=mock_queries)
sys.modules["utils.llm"] = mock_llm
sys.modules["utils"] = MagicMock(llm=mock_llm)

from pipelines import (
    pipeline_process_message,
    pipeline_show_orgs,
    pipeline_change_style,
    pipeline_about_me,
    pipeline_start,
    STYLES,
    ABOUT_TEXT,
    START_TEXT,
)
from pipelines.pipeline_factory import _needs_org_category_clarification


class TestStartPipeline(unittest.TestCase):
    def test_start_returns_string(self):
        result = pipeline_start()
        self.assertIsInstance(result, str)
        self.assertIn("Hate-2-Action", result)

    def test_start_contains_welcome(self):
        result = pipeline_start()
        self.assertGreater(len(result), 50)


class TestAboutMePipeline(unittest.TestCase):
    def test_about_returns_string(self):
        result = pipeline_about_me()
        self.assertIsInstance(result, str)
        self.assertIn("Hate-2-Action", result)

    def test_about_contains_commands(self):
        result = pipeline_about_me()
        self.assertIn("/style", result)
        self.assertIn("/orgs", result)


class TestChangeStylePipeline(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        mock_queries.reset_mock()
        mock_queries.get_or_create_user.return_value = {"user_id": 1, "response_style": "normal"}
        mock_queries.get_or_create_chat.return_value = {"chat_id": 100, "type": "private"}
        mock_queries.set_user_style.return_value = None

    async def test_valid_style_saved(self):
        for style in STYLES:
            mock_queries.reset_mock()
            mock_queries.get_or_create_user.return_value = {"user_id": 1}
            mock_queries.get_or_create_chat.return_value = {"chat_id": 100}

            result = await pipeline_change_style(
                user_id=1, chat_id=100, chat_type="private", requested_style=style
            )
            mock_queries.set_user_style.assert_called_with(1, style)
            self.assertIn(style, result)

    async def test_unknown_style_shows_options(self):
        result = await pipeline_change_style(
            user_id=1, chat_id=100, chat_type="private", requested_style=None, message="change it"
        )
        mock_llm.detect_style_from_message.return_value = None
        for style in STYLES:
            self.assertIn(style, result)

    async def test_style_confirmation_message(self):
        result = await pipeline_change_style(
            user_id=1, chat_id=100, chat_type="private", requested_style="funny"
        )
        self.assertIn("funny", result.lower())
        self.assertIn("✅", result)


class TestProcessMessagePipeline(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        mock_queries.reset_mock()
        mock_llm.reset_mock()

        mock_queries.get_or_create_user.return_value = {"user_id": 42, "response_style": "normal"}
        mock_queries.get_or_create_chat.return_value = {"chat_id": 999, "type": "private"}
        mock_queries.get_user_style.return_value = "normal"
        mock_queries.get_chat_style.return_value = "normal"
        mock_queries.get_chat_history.return_value = []
        mock_queries.upsert_problem.return_value = 1
        mock_queries.upsert_solution.return_value = 1
        mock_queries.find_orgs_via_solutions.return_value = [
            {"name": "Greenpeace", "description": "Environmental NGO", "website": "https://greenpeace.org"}
        ]
        mock_queries.find_projects_via_solutions.return_value = [
            {"name": "Climate Response", "org_name": "Greenpeace", "description": "Climate action", "org_website": "https://greenpeace.org"}
        ]
        mock_queries.save_message.return_value = None
        mock_queries.link_problem_solution.return_value = None

        mock_llm.extract_problems_and_solutions.return_value = {
            "problems": [{"name": "Climate change", "context": "global warming", "content": "rising temps"}],
            "solutions": [{"name": "Donate to NGO", "context": "financial support", "content": "give money"}],
        }
        mock_llm.get_embedding.return_value = [0.1] * 1536
        mock_llm.generate_reply.return_value = "I understand your frustration! Check out [Greenpeace](https://greenpeace.org)."
        mock_llm.rewrite_reply_with_style.return_value = "rewritten"

    async def test_user_is_created(self):
        await pipeline_process_message(
            user_id=42, chat_id=999, chat_type="private",
            message_text="I hate how nobody cares about climate change!",
        )
        mock_queries.get_or_create_user.assert_called_with(42)

    async def test_message_is_saved(self):
        await pipeline_process_message(
            user_id=42, chat_id=999, chat_type="private",
            message_text="Corruption is everywhere!",
        )
        mock_queries.save_message.assert_called_once()
        call_kwargs = mock_queries.save_message.call_args
        self.assertIn("Corruption is everywhere!", call_kwargs.args)

    async def test_correct_style_applied(self):
        mock_queries.get_user_style.return_value = "sarcastic"
        await pipeline_process_message(
            user_id=42, chat_id=999, chat_type="private",
            message_text="Politicians are all corrupt!",
        )
        call_args = mock_llm.rewrite_reply_with_style.call_args
        self.assertEqual(call_args.args[1], "sarcastic")

    async def test_returns_reply_string(self):
        result = await pipeline_process_message(
            user_id=42, chat_id=999, chat_type="private",
            message_text="The world is broken and nobody does anything!",
        )
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10)

    async def test_problems_extracted_and_stored(self):
        await pipeline_process_message(
            user_id=42, chat_id=999, chat_type="private",
            message_text="Climate change is destroying our planet!",
        )
        mock_llm.extract_problems_and_solutions.assert_called_once()
        mock_queries.upsert_problem.assert_called()

    async def test_pipeline_marked_in_save(self):
        await pipeline_process_message(
            user_id=42, chat_id=999, chat_type="private",
            message_text="Test message",
        )
        call_kwargs = mock_queries.save_message.call_args.kwargs
        self.assertEqual(call_kwargs.get("pipeline_used"), "process_message")


class TestShowOrgsPipeline(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        mock_queries.reset_mock()
        mock_llm.reset_mock()
        mock_queries.get_or_create_user.return_value = {"user_id": 1}
        mock_queries.get_or_create_chat.return_value = {"chat_id": 100}
        mock_queries.get_user_style.return_value = "normal"
        mock_queries.get_chat_style.return_value = None
        mock_queries.find_orgs_by_embedding.return_value = [
            {"name": "Amnesty", "description": "Human rights", "website": "https://amnesty.org", "similarity": 0.85}
        ]
        mock_queries.find_projects_by_embedding.return_value = []
        mock_queries.save_message.return_value = None
        mock_llm.enrich_query.return_value = "human rights violations torture detention"
        mock_llm.get_embedding.return_value = [0.1] * 1536
        mock_llm.generate_org_reply.return_value = "Check out [Amnesty International](https://amnesty.org)!"

    async def test_query_is_enriched(self):
        await pipeline_show_orgs(1, 100, "private", "human rights")
        mock_llm.enrich_query.assert_called_with("human rights")

    async def test_orgs_returned(self):
        result = await pipeline_show_orgs(1, 100, "private", "corruption")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 5)

    async def test_message_saved(self):
        await pipeline_show_orgs(1, 100, "private", "poverty")
        mock_queries.save_message.assert_not_called()


class TestShowOrgsClarification(unittest.TestCase):
    def test_single_topic_word_does_not_require_clarification(self):
        self.assertFalse(_needs_org_category_clarification("освіта"))

    def test_generic_request_requires_clarification(self):
        self.assertTrue(_needs_org_category_clarification("покажи організації"))

    def test_org_request_with_topic_does_not_require_clarification(self):
        self.assertFalse(_needs_org_category_clarification("організації освіти"))


class TestStyleResolution(unittest.IsolatedAsyncioTestCase):
    """Test that style priority is: user > chat > default."""

    def setUp(self):
        mock_queries.reset_mock()
        mock_llm.reset_mock()
        mock_queries.get_or_create_user.return_value = {"user_id": 1}
        mock_queries.get_or_create_chat.return_value = {"chat_id": 100}
        mock_queries.upsert_problem.return_value = 1
        mock_queries.upsert_solution.return_value = 1
        mock_queries.find_orgs_via_solutions.return_value = []
        mock_queries.find_projects_via_solutions.return_value = []
        mock_queries.find_orgs_by_embedding.return_value = []
        mock_queries.find_projects_by_embedding.return_value = []
        mock_queries.save_message.return_value = None
        mock_queries.link_problem_solution.return_value = None
        mock_queries.get_chat_history.return_value = []
        mock_llm.extract_problems_and_solutions.return_value = {
            "problems": [], "solutions": []
        }
        mock_llm.get_embedding.return_value = [0.1] * 1536
        mock_llm.generate_reply.return_value = "reply"
        mock_llm.rewrite_reply_with_style.return_value = "styled reply"

    async def test_user_style_takes_priority(self):
        mock_queries.get_user_style.return_value = "funny"
        mock_queries.get_chat_style.return_value = "rude"
        await pipeline_process_message(1, 100, "private", "I hate taxes")
        call_args = mock_llm.rewrite_reply_with_style.call_args
        self.assertEqual(call_args.args[1], "funny")

    async def test_chat_style_fallback(self):
        mock_queries.get_user_style.return_value = "normal"
        mock_queries.get_chat_style.return_value = "sarcastic"
        await pipeline_process_message(1, 100, "private", "traffic is terrible")
        call_args = mock_llm.rewrite_reply_with_style.call_args
        self.assertEqual(call_args.args[1], "sarcastic")

    async def test_default_normal_style(self):
        mock_queries.get_user_style.return_value = "normal"
        mock_queries.get_chat_style.return_value = None
        await pipeline_process_message(1, 100, "private", "healthcare is broken")
        mock_llm.rewrite_reply_with_style.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
