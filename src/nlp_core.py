import os
import random
import re
from collections import defaultdict

class CourseGrammarEngine:
    def __init__(self, grammar_path):
        self.rules = defaultdict(list)
        self.start_symbol = "S"
        # Từ điển chuẩn hóa thực thể (Entity Normalization)
        self.entity_synonyms = {
            "btl": "BÀI TẬP LỚN",
            "project": "BÀI TẬP LỚN",
            "bài tập lớn": "BÀI TẬP LỚN",
            "môn nlp": "CO3085",
            "môn xử lý ngôn ngữ tự nhiên": "CO3085",
            "co3085": "CO3085",
            "công cụ ai": "AI_TOOLS",
            "chatgpt": "AI_TOOLS",
            "llm": "AI_TOOLS"
        }
        self.load_grammar(grammar_path)

    def load_grammar(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                lhs, rhs = line.split('->')
                lhs = lhs.strip()
                for prod in rhs.split('|'):
                    tokens = []
                    for part in prod.strip().split():
                        if part.startswith('"') and part.endswith('"'):
                            val = part[1:-1]
                            if val != "":
                                tokens.append(('T', val))
                        else:
                            tokens.append(('NT', part))
                    self.rules[lhs].append(tokens)

    def export_grammar(self, output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for lhs, prods in self.rules.items():
                rhs_strs = []
                for prod in prods:
                    if not prod:
                        rhs_strs.append('""')
                    else:
                        rhs_strs.append(" ".join([f'"{val}"' if typ == 'T' else val for typ, val in prod]))
                f.write(f"{lhs} -> {' | '.join(rhs_strs)}\n")

    def _generate_one(self, symbol):
        if symbol not in self.rules:
            return [symbol]
        prod = random.choice(self.rules[symbol])
        sentence = []
        for typ, val in prod:
            if typ == 'T':
                sentence.append(val)
            else:
                sentence.extend(self._generate_one(val))
        return sentence

    def generate_samples(self, output_path, max_samples=10000):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        samples = set()
        attempts = 0
        max_attempts = max_samples * 5

        while len(samples) < max_samples and attempts < max_attempts:
            tokens = self._generate_one(self.start_symbol)
            text = " ".join(tokens).replace(" ?", "?")
            if text:
                text = text[0].upper() + text[1:]
                samples.add(text)
            attempts += 1

        with open(output_path, 'w', encoding='utf-8') as f:
            for s in sorted(samples):
                f.write(s + "\n")
        print(f"[INFO] Đã sinh {len(samples)} câu hợp lệ vào {output_path}")

    def tokenize(self, sentence):
        sentence = sentence.lower().strip()
        sentence = re.sub(r'(\?)', r' \1 ', sentence)
        return sentence.split()

    def _parse_symbol(self, symbol, tokens, pos):
        results = []
        for prod in self.rules.get(symbol, []):
            states = [(pos, [], {})]
            for typ, val in prod:
                next_states = []
                for curr_pos, curr_trees, curr_ents in states:
                    if typ == 'T':
                        if curr_pos < len(tokens) and tokens[curr_pos] == val:
                            next_states.append((curr_pos + 1, curr_trees + [val], curr_ents))
                    else:
                        sub_results = self._parse_symbol(val, tokens, curr_pos)
                        for next_p, sub_tree, sub_ents in sub_results:
                            merged_ents = {**curr_ents, **sub_ents}
                            if val.endswith("_NP"):
                                raw_phrase = re.sub(r'\([A-Z_]+\s+|\)', '', sub_tree).strip()
                                normalized = self.entity_synonyms.get(raw_phrase, raw_phrase.upper())
                                merged_ents[val] = normalized
                            next_states.append((next_p, curr_trees + [sub_tree], merged_ents))
                states = next_states

            for final_pos, trees, ents in states:
                tree_str = f"({symbol} {' '.join(trees)})" if trees else f"({symbol})"
                results.append((final_pos, tree_str, ents))
        return results

    def build_semantic_repr(self, intent, entities):
        """Tạo biểu diễn ngữ nghĩa dạng logic: INTENT(key=value)"""
        if not entities:
            return f"{intent}()"
        args = ", ".join([f"{k.replace('_NP', '').lower()}={v}" for k, v in entities.items()])
        return f"{intent}({args})"

    def parse(self, sentence):
        tokens = self.tokenize(sentence)
        if not tokens:
            return {
                "tree": "()",
                "intent": "UNKNOWN",
                "entities": {},
                "semantic": "UNKNOWN()"
            }

        matches = self._parse_symbol(self.start_symbol, tokens, 0)
        for next_pos, tree_str, entities in matches:
            if next_pos == len(tokens):
                intent_match = re.search(r'\(S \((Q_[A-Z]+)', tree_str)
                intent_map = {
                    "Q_COURSE": "GET_COURSE_INFO",
                    "Q_TOPIC": "GET_TOPIC",
                    "Q_SCHEDULE": "GET_SCHEDULE",
                    "Q_ASSIGN": "GET_ASSIGNMENT",
                    "Q_DEADLINE": "GET_DEADLINE",
                    "Q_RESOURCE": "GET_RESOURCE",
                    "Q_RULE": "GET_RULE",
                    "Q_CONTEXT": "LOCAL_CONTEXT"
                }
                raw_q = intent_match.group(1) if intent_match else "UNKNOWN"
                intent = intent_map.get(raw_q, "UNKNOWN")
                semantic = self.build_semantic_repr(intent, entities)
                return {
                    "tree": tree_str,
                    "intent": intent,
                    "entities": entities,
                    "semantic": semantic
                }

        return {
            "tree": "()",
            "intent": "OUT_OF_DOMAIN",
            "entities": {},
            "semantic": "OUT_OF_DOMAIN()"
        }

    def process_input_file(self, input_path, output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(input_path, 'r', encoding='utf-8') as fin, \
             open(output_path, 'w', encoding='utf-8') as fout:
            for line in fin:
                sent = line.strip()
                if not sent:
                    continue
                res = self.parse(sent)
                fout.write(f"{res['tree']}\n")
        print(f"[INFO] Đã xuất kết quả phân tích cú pháp vào {output_path}")


if __name__ == "__main__":
    engine = CourseGrammarEngine("data/grammar.cfg")
    engine.export_grammar("output/grammar.txt")
    engine.generate_samples("output/samples.txt", max_samples=10000)
    if os.path.exists("input/sentences.txt"):
        engine.process_input_file("input/sentences.txt", "output/parse-results.txt")