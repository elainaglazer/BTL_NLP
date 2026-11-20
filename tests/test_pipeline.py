"""Smoke test toàn pipeline: python -m unittest discover -s tests -v"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import ensure_utf8_stdio, load_config  # noqa: E402

ensure_utf8_stdio()
from src.interfaces import NOT_FOUND_MESSAGE  # noqa: E402
from src.parser_adapter import ParserAdapter  # noqa: E402
from src.pipeline import CourseAssistantPipeline  # noqa: E402
from src.rag.generator import LLMGenerator  # noqa: E402


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pipe = CourseAssistantPipeline(load_config(overrides={"provider": "none"}))

    def setUp(self):
        self.pipe.reset()

    def test_valid_question_is_parsed_and_grounded(self):
        t = self.pipe.ask("Môn NLP có bao nhiêu tín chỉ?")
        self.assertEqual(t.parse.intent, "GET_COURSE_INFO")
        self.assertIn("3", t.answer.text)
        self.assertEqual(t.status, "ANSWERED")
        self.assertTrue(t.answer.sources)
        self.assertIn("[Nguồn:", t.answer.text)

    def test_out_of_domain_is_rejected_without_retrieval(self):
        t = self.pipe.ask("Ai là tổng thống của Pháp?")
        self.assertEqual(t.status, "OUT_OF_DOMAIN")
        self.assertEqual(t.retrieved, [])

    def test_missing_info_is_not_hallucinated(self):
        for q in ("Giảng viên dạy môn NLP là ai?", "Chương 13 nói về gì?"):
            self.pipe.reset()
            t = self.pipe.ask(q)
            self.assertEqual(t.answer.text, NOT_FOUND_MESSAGE, q)

    def test_context_reference_is_resolved(self):
        # dialogues.txt chính thức: DIALOGUE 01, 04, 05
        self.pipe.ask("Tuần 3 học gì?")
        t = self.pipe.ask("Tài liệu của chương này là gì?")
        self.assertIn("chương 3", t.context.resolved)
        self.assertEqual(t.parse.intent, "GET_RESOURCE")
        self.assertTrue(any(c.source == "resources.txt" for c in t.retrieved))

    def test_ellipsis_next_chapter(self):
        self.pipe.ask("Chương 11 có hỏi đáp không?")
        t = self.pipe.ask("Còn chương sau?")
        self.assertIn("chương 12", t.context.resolved)
        self.assertEqual(t.answer.sources, ["topics.txt#12"])

    def test_lo_to_chapter(self):
        self.pipe.ask("L.O.2.5 học về gì?")
        t = self.pipe.ask("Nội dung này nằm ở chương nào?")
        self.assertIn("CHAPTER 6", t.answer.text)

    def test_reset_clears_context(self):
        self.pipe.ask("Tuần 3 học gì?")
        self.pipe.reset()
        t = self.pipe.ask("Tài liệu của chương này là gì?")
        self.assertFalse(t.context.changed)


class LLMGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.pipe = CourseAssistantPipeline(load_config(overrides={"provider": "none"}))

    def _ask_with(self, fake_reply):
        gen = LLMGenerator("openai", min_score=1.0, min_coverage=0.5)
        gen._call = lambda system, user: fake_reply(user)
        self.pipe.generator = gen
        return self.pipe.ask("Deadline của bài tập lớn là khi nào?")

    def test_llm_answer_keeps_valid_citation(self):
        t = self._ask_with(lambda u: "Checkpoint 1 ở tuần 8. [Nguồn: schedule.txt#9]")
        self.assertEqual(t.answer.sources, ["schedule.txt#9"])
        self.assertIn("CÂU HỎI", t.answer.prompt)

    def test_llm_not_found_reply_is_respected(self):
        t = self._ask_with(lambda u: NOT_FOUND_MESSAGE)
        self.assertEqual(t.status, "NOT_FOUND")

    def test_llm_error_falls_back_to_extractive(self):
        def boom(u):
            raise ConnectionError("offline")
        t = self._ask_with(boom)
        self.assertEqual(t.status, "ANSWERED")
        self.assertIn("fallback", t.answer.mode)


class Part1Test(unittest.TestCase):
    def test_part1_outputs(self):
        cfg = load_config()
        adapter = ParserAdapter(ROOT / cfg["grammar"])
        with tempfile.TemporaryDirectory() as d:
            adapter.run_part1(ROOT / "input" / "sentences.txt", Path(d), max_samples=200)
            for name in ("grammar.txt", "samples.txt", "parse-results.txt"):
                self.assertTrue((Path(d) / name).stat().st_size > 0, name)
            n_in = len([l for l in (ROOT / "input/sentences.txt").read_text(encoding="utf-8-sig").splitlines() if l.strip()])
            n_out = len((Path(d) / "parse-results.txt").read_text(encoding="utf-8").splitlines())
            self.assertEqual(n_in, n_out)
            self.assertLessEqual(len((Path(d) / "samples.txt").read_text(encoding="utf-8").splitlines()), 200)


if __name__ == "__main__":
    unittest.main()
