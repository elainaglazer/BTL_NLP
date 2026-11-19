"""TV4 wrapper around the existing TV1 parser; does not alter its grammar or algorithm."""
import random
import unicodedata
from pathlib import Path

from src.interfaces import ParseResult
from src.nlp_core import CourseGrammarEngine


class ParserAdapter:
    def __init__(self, grammar_path: Path):
        self.engine = CourseGrammarEngine(str(grammar_path))

    def parse(self, sentence: str) -> ParseResult:
        clean = " ".join(unicodedata.normalize("NFC", sentence).split())
        result = self.engine.parse(clean)
        return ParseResult(sentence=sentence, tree=result["tree"], intent=result["intent"],
                           entities=result["entities"], semantic=result["semantic"])

    def run_part1(self, sentences: Path, output: Path, max_samples=10000, seed=42) -> None:
        if not 1 <= max_samples <= 10000:
            raise ValueError("max_samples phải nằm trong khoảng 1..10000")
        output.mkdir(parents=True, exist_ok=True)
        state = random.getstate()
        try:
            random.seed(seed)
            self.engine.export_grammar(str(output / "grammar.txt"))
            self.engine.generate_samples(str(output / "samples.txt"), max_samples=max_samples)
        finally:
            random.setstate(state)
        lines = [self.parse(s.strip()).tree for s in sentences.read_text(encoding="utf-8-sig").splitlines()
                 if s.strip()]
        (output / "parse-results.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
