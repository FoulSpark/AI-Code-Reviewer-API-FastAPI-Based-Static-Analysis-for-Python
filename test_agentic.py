import unittest
import json
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from app.Services.agentic_pipeline import parse_json, fmt_errors, run_agentic_task
from app.Schema.agentic import AgenticResponse
from app.Schema.review import Issues, Severity

class TestAgenticPipeline(unittest.TestCase):

    def test_parse_json_with_fences(self):
        text = "```json\n{\"key\": \"value\"}\n```"
        self.assertEqual(parse_json(text), {"key": "value"})

    def test_parse_json_no_fences(self):
        text = "{\"key\": \"value\"}"
        self.assertEqual(parse_json(text), {"key": "value"})

    def test_parse_json_messy(self):
        text = "Sure, here is the JSON: ```\n{\"key\": \"value\"}\n``` Hope that helps!"
        self.assertEqual(parse_json(text), {"key": "value"})

    def test_fmt_errors_empty(self):
        self.assertEqual(fmt_errors([]), "none")
        self.assertEqual(fmt_errors(None), "none")

    def test_fmt_errors_populated(self):
        errors = [{"issue": "bad syntax"}]
        self.assertIn("bad syntax", fmt_errors(errors))

class TestOrchestrator(unittest.IsolatedAsyncioTestCase):

    @patch("app.Services.agentic_pipeline.understand")
    @patch("app.Services.agentic_pipeline.plan")
    @patch("app.Services.agentic_pipeline.implement")
    @patch("app.Services.agentic_pipeline.check_syntax")
    @patch("app.Services.agentic_pipeline.check_semantic")
    @patch("app.Services.agentic_pipeline.save_review")
    async def test_run_agentic_task_happy_path(self, mock_save, mock_sem, mock_syn, mock_impl, mock_plan, mock_und):
        # Setup mocks
        mock_und.return_value = {"language": "python", "task": "generate"}
        mock_plan.return_value = {"symbol_table": {}}
        mock_impl.return_value = "print('hello')"
        mock_syn.return_value = {"passed": True}
        mock_sem.return_value = {"passed": True}

        result = await run_agentic_task("say hello")

        self.assertIsInstance(result, AgenticResponse)
        self.assertEqual(result.code, "print('hello')")
        self.assertEqual(result.retry_count, 0)
        mock_save.assert_called_once()

    @patch("app.Services.agentic_pipeline.understand")
    @patch("app.Services.agentic_pipeline.plan")
    @patch("app.Services.agentic_pipeline.implement")
    @patch("app.Services.agentic_pipeline.check_syntax")
    @patch("app.Services.agentic_pipeline.check_semantic")
    @patch("app.Services.agentic_pipeline.save_review")
    async def test_run_agentic_task_with_syntax_retry(self, mock_save, mock_sem, mock_syn, mock_impl, mock_plan, mock_und):
        # Setup mocks
        mock_und.return_value = {"language": "python"}
        mock_plan.return_value = {"symbol_table": {}}
        mock_impl.return_value = "code"
        
        # First call fails syntax, second passes
        mock_syn.side_effect = [{"passed": False, "errors": [{"issue": "syntax"}]}, {"passed": True}]
        mock_sem.return_value = {"passed": True}

        result = await run_agentic_task("test retry")

        self.assertEqual(result.retry_count, 1)
        self.assertEqual(mock_impl.call_count, 2)

if __name__ == "__main__":
    unittest.main()
