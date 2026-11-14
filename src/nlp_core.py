import os
import random
import re
from collections import defaultdict

class CourseGrammarEngine:
    def __init__(self, grammar_path):
        self.rules = defaultdict(list)
        self.start_symbol = "S"
        self.load_grammar(grammar_path)

    def load_grammar(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                lhs, rhs = line.split('->')
                lhs = lhs.strip()
                productions = rhs.split('|')
                for prod in productions:
                    tokens = []
                    # Tách các token non-terminal và terminal ("...")
                    for part in prod.strip().split():
                        if part.startswith('"') and part.endswith('"'):
                            val = part[1:-1]
                            if val != "":  # Bỏ qua chuỗi rỗng epsilon
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

    # ---------------------------------------------------------
    # 1. GIẢI THUẬT SINH CÂU (Tối đa 10.000 câu)[cite: 3]
    # ---------------------------------------------------------
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
            # Ghép từ và chuẩn hóa dấu hỏi chấm
            text = " ".join(tokens).replace(" ?", "?")
            if text:
                text = text[0].upper() + text[1:]
                samples.add(text)
            attempts += 1

        with open(output_path, 'w', encoding='utf-8') as f:
            for s in sorted(samples):
                f.write(s + "\n")
        print(f"[INFO] Đã sinh {len(samples)} câu hợp lệ vào {output_path}")

    # ---------------------------------------------------------
    # 2. BỘ PHÂN TÍCH CÚ PHÁP (PARSER)[cite: 3]
    # ---------------------------------------------------------
    def tokenize(self, sentence):
        sentence = sentence.lower().strip()
        # Tách dấu ? thành token riêng nếu dính liền chữ
        sentence = re.sub(r'(\?)', r' \1 ', sentence)
        return sentence.split()

    def _parse_symbol(self, symbol, tokens, pos):
        """Trả về list các tuple: (next_pos, tree_string, extracted_entities)"""
        results = []
        for prod in self.rules.get(symbol, []):
            # Bắt đầu khớp từng phần tử trong một vế phải (production)
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
                            # Lưu các cụm danh từ làm Entity
                            if val.endswith("_NP"):
                                raw_phrase = re.sub(r'\([A-Z_]+\s+|\)', '', sub_tree).strip()
                                merged_ents[val] = raw_phrase
                            next_states.append((next_p, curr_trees + [sub_tree], merged_ents))
                states = next_states

            for final_pos, trees, ents in states:
                tree_str = f"({symbol} {' '.join(trees)})" if trees else f"({symbol})"
                results.append((final_pos, tree_str, ents))
        return results

    def parse(self, sentence):
        tokens = self.tokenize(sentence)
        if not tokens:
            return "()", "UNKNOWN", {}

        matches = self._parse_symbol(self.start_symbol, tokens, 0)
        for next_pos, tree_str, entities in matches:
            if next_pos == len(tokens):
                # Trích xuất Intent từ nhánh con đầu tiên của S
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
                return tree_str, intent, entities

        return "()", "OUT_OF_DOMAIN", {}

    def process_input_file(self, input_path, output_path):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(input_path, 'r', encoding='utf-8') as fin, \
             open(output_path, 'w', encoding='utf-8') as fout:
            for line in fin:
                sent = line.strip()
                if not sent:
                    continue
                tree, intent, entities = self.parse(sent)
                # Xuất đúng định dạng cây cú pháp hoặc () theo đề bài[cite: 3]
                fout.write(f"{tree}\n")
        print(f"[INFO] Đã xuất kết quả phân tích cú pháp vào {output_path}")

# =========================================================
# CHẠY THỬ NGHIỆM ĐỘC LẬP CHO PHẦN I
# =========================================================
if __name__ == "__main__":
    engine = CourseGrammarEngine("data/grammar.cfg")
    
    # 1. Xuất file grammar.txt[cite: 3]
    engine.export_grammar("output/grammar.txt")
    
    # 2. Sinh tối đa 10.000 câu mẫu[cite: 3]
    engine.generate_samples("output/samples.txt", max_samples=10000)
    
    # 3. Phân tích cú pháp file input/sentences.txt[cite: 3]
    if os.path.exists("input/sentences.txt"):
        engine.process_input_file("input/sentences.txt", "output/parse-results.txt")