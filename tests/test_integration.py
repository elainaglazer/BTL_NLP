"""Integration checks for TV4; fake components below are test-only, not NLP implementations."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from src.components import _load_factory, build_pipeline
from src.config import ROOT, load_config
from src.interfaces import Answer, ContextResolution, ParseResult, RetrievedChunk
from src.pipeline import CourseAssistantPipeline


class IntegrationTests(unittest.TestCase):
    def test_default_reports_pending_and_preserves_tv1_parse(self):
        pipe = build_pipeline(load_config())
        turn = pipe.ask("Môn NLP có bao nhiêu tín chỉ?")
        self.assertTrue(turn.parse.parsed)
        self.assertEqual(turn.parse.intent, "GET_COURSE_INFO")
        self.assertEqual(turn.status, "PENDING_INTEGRATION")
        self.assertEqual(len(turn.pending), 3)
        self.assertFalse(turn.answer.grounded)
        self.assertEqual(turn.retrieved, [])

    def wired(self):
        parser, context, retriever, generator = Mock(), Mock(), Mock(), Mock()
        parser.parse.side_effect = lambda text: ParseResult(text, "(S test)", "GET_TOPIC", {}, "GET_TOPIC()")
        context.resolve.side_effect = lambda text: ContextResolution(text, text)
        chunk = RetrievedChunk("fake#1", "fake.txt", "Test only", "fake content")
        retriever.retrieve.return_value = [chunk]
        generator.generate.return_value = Answer("test answer", ["fake#1"], True)
        return CourseAssistantPipeline(parser, context, retriever, generator, top_k=2)

    def test_order_context_reparse_semantic_retrieval_answer_memory(self):
        pipe = self.wired()
        calls = []
        def parse(text):
            calls.append("parse:" + text)
            return ParseResult(text, "(S test)", "GET_TOPIC", {}, "GET_TOPIC(chapter=3)")
        def resolve(text):
            calls.append("context")
            return ContextResolution(text, "chương 3", {"nó": "chương 3"})
        def retrieve(query, parsed, top_k):
            calls.append("retrieve")
            self.assertIn("GET_TOPIC(chapter=3)", query)
            self.assertEqual(parsed.sentence, "chương 3")
            self.assertEqual(top_k, 2)
            return [RetrievedChunk("fake#1", "fake.txt", "Test only", "test")]
        def generate(question, parsed, chunks):
            calls.append("answer")
            self.assertEqual(question, "chương 3")
            return Answer("test answer", [chunks[0].chunk_id], True)
        pipe.parser.parse.side_effect = parse
        pipe.context.resolve.side_effect = resolve
        pipe.retriever.retrieve.side_effect = retrieve
        pipe.generator.generate.side_effect = generate
        pipe.context.update.side_effect = lambda turn: calls.append("memory")
        turn = pipe.ask("nó")
        self.assertEqual(calls, ["parse:nó", "context", "parse:chương 3", "retrieve", "answer", "memory"])
        self.assertEqual(turn.status, "ANSWERED")
        self.assertEqual(turn.answer.sources, ["fake#1"])

    def test_empty_retrieval_does_not_call_generator(self):
        pipe = self.wired()
        pipe.retriever.retrieve.return_value = []
        self.assertEqual(pipe.ask("test").status, "NOT_FOUND")
        pipe.generator.generate.assert_not_called()

    def test_failed_parse_is_not_claimed_out_of_domain(self):
        pipe = self.wired()
        pipe.parser.parse.side_effect = lambda text: ParseResult(text)
        self.assertEqual(pipe.ask("test").status, "UNPARSED")
        pipe.retriever.retrieve.assert_not_called()

    def test_reset_delegates_to_context_module(self):
        pipe = self.wired()
        pipe.reset()
        pipe.context.reset.assert_called_once_with()

    def test_factory_passes_config_to_requested_function(self):
        # Existing stdlib factory validates module:function loading without adding an NLP module.
        result = _load_factory("builtins:dict", {"top_k": 2})
        self.assertEqual(result, {"top_k": 2})
        with self.assertRaises(ValueError):
            _load_factory("bad-format", {})
        with self.assertRaises(ImportError):
            _load_factory("not_an_installed_tv2_module:create", {})

    def test_cli_grading_paths_and_tv1_output_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            inputs = folder / "input"
            inputs.mkdir()
            (inputs / "sentences.txt").write_text("Môn NLP có bao nhiêu tín chỉ?\nnot a course question\n", encoding="utf-8")
            cfg = load_config()
            cfg["max_samples"] = 20
            config_path = folder / "config.json"
            config_path.write_text(json.dumps(cfg), encoding="utf-8")
            env = dict(os.environ, INPUT_DIR=str(inputs), OUTPUT_DIR=str(folder / "output"),
                       PYTHONIOENCODING="utf-8")
            result = subprocess.run([sys.executable, "-m", "src.main", "run-all", "--config", str(config_path)],
                                    cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            out = folder / "output"
            trees = (out / "parse-results.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(trees), 2)
            self.assertNotEqual(trees[0], "()")
            self.assertEqual(trees[1], "()")
            self.assertLessEqual(len((out / "samples.txt").read_text(encoding="utf-8").splitlines()), 20)
            turns = [json.loads(s) for s in (out / "integration-trace.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(turns), 2)
            self.assertTrue(all(t["status"] == "PENDING_INTEGRATION" for t in turns))

    def test_cli_missing_question_has_nonzero_exit(self):
        result = subprocess.run([sys.executable, "-m", "src.main", "ask"], cwd=ROOT,
                                capture_output=True)
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
