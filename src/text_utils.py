"""Chuẩn hóa / tách từ tiếng Việt mức âm tiết + glossary Anh–Việt (không cần thư viện ngoài).

Bộ dữ liệu của môn trộn tiếng Anh (topics, schedule, resources) và tiếng Việt (faq, quy định),
còn câu hỏi của sinh viên chủ yếu là tiếng Việt. `canonical()` đưa các mã về cùng một dạng
(WEEK 03 / tuần 3, CH04 / Chapter 4 / chương 4, L.O.2.5 / LO2.5) và bổ sung từ tương đương
Anh–Việt để BM25 và cổng chống ảo giác so khớp được cả hai ngôn ngữ.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Iterable, List, Set, Tuple

_WORD_RE = re.compile(r"[0-9a-zà-ỹđ%]+", re.IGNORECASE)

FUNCTION_WORDS: Set[str] = set(
    """
    là gì nào khi bao nhiêu mấy có không của ở đâu những các được như thế ra sao tôi em mình
    cho hỏi về và thì nó này đó kia ạ vậy hả nhé với muốn biết xin vui lòng hãy một trong
    bị đã sẽ đang thể ai còn đến cái
    """.split()
)
# Từ "mềm": có ích khi truy xuất nhưng không chứng minh được KB có câu trả lời.
SOFT_WORDS: Set[str] = set("nội dung thông tin chi tiết cách nằm nói cần phải học liên quan gồm vào lúc chính dạy bằng làm theo khác".split())
STOPWORDS: Set[str] = FUNCTION_WORDS | SOFT_WORDS

DOMAIN_GENERIC: Set[str] = set("môn học nlp co3085 xử lý ngôn ngữ tự nhiên".split())
# Từ cấu trúc: ý nghĩa đã nằm trong intent/entity, không dùng để quyết định "có thông tin hay không".
ANSWER_GENERIC: Set[str] = DOMAIN_GENERIC | set(
    "bài tập lớn btl project sinh viên chương tuần tài liệu tham khảo giáo trình quy định".split())

_CANON_RULES = [
    (re.compile(r"\bget_[a-z_]+\b"), " "),  # tên intent (GET_INSTRUCTOR) trong tài liệu không phải nội dung
    (re.compile(r"_"), " "),
    (re.compile(r"\bl\.?\s?o\.?\s?(\d)\.(\d)\b"), r" lo\1\2 "),
    (re.compile(r"\bch0?(\d{1,2})\b"), r" chương \1 "),
    (re.compile(r"\b(?:week|tuần)\s*0?(\d{1,2})\b"), r" tuần \1 "),
    (re.compile(r"\b(?:chapter|chương)\s*0?(\d{1,2})\b"), r" chương \1 "),
    (re.compile(r"\bpart\s+(iv|iii|ii|i)\b"), r" phần \1 "),
    (re.compile(r"\bmidterm(?: exam)?\b|\b(?:thi )?giữa (?:kỳ|kì)\b"), " midterm "),
    (re.compile(r"\bfinal(?: exam)?\b|\b(?:thi )?cuối (?:kỳ|kì)\b"), " final "),
    (re.compile(r"\bminutes?\b"), " phút "),
    (re.compile(r"\bcredits?\b"), " tín chỉ "),
    (re.compile(r"\bpercent\b"), " % "),
]

# (biểu thức, từ bổ sung). Áp dụng cho cả tài liệu và câu hỏi -> khớp được hai chiều.
GLOSSARY: List[Tuple[str, str]] = [
    (r"requirements?|yêu cầu", "requirements yêu cầu"),
    (r"bài tập lớn|\bbtl\d*\b|major assignment|\bproject\b", "bài tập lớn major assignment btl"),
    (r"question answering|hỏi đáp|\bqa\b", "question answering hỏi đáp qa"),
    (r"%|phần trăm|tỉ lệ|tỷ lệ|trọng số|chiếm", "% phần trăm tỉ lệ chiếm"),
    (r"bao lâu|thời gian|thời lượng|kéo dài|phút", "phút thời lượng thời gian bao lâu"),
    (r"bản cuối|nộp cuối|final submission", "final submission bản cuối"),
    (r"thư viện|librar(?:y|ies)", "thư viện library external"),
    (r"\bdùng\b|sử dụng|\busage\b", "sử dụng dùng"),
    (r"phần chính|(?:những|các|mấy) phần\b|main parts?", "main parts phần chính"),
    (r"phương pháp|\bmethods?\b|\bstrateg(?:y|ies)\b", "methods strategies phương pháp"),
    (r"semantic grammars?|văn phạm ngữ nghĩa", "semantic grammar văn phạm ngữ nghĩa"),
    (r"knowledge representation|biểu diễn tri thức", "knowledge representation biểu diễn tri thức"),
    (r"dependency grammar|văn phạm phụ thuộc", "dependency grammar văn phạm phụ thuộc"),
    (r"augmented grammars?|văn phạm gia tố", "augmented grammar văn phạm gia tố"),
    (r"logical form|dạng luận lý", "logical form dạng luận lý"),
    (r"selectional restrictions?|giới hạn lựa chọn", "selectional restriction giới hạn lựa chọn"),
    (r"semantic networks?|mạng ngữ nghĩa", "semantic network mạng ngữ nghĩa"),
    (r"word sense disambiguation|\bwsd\b|khử nhập nhằng nghĩa", "word sense disambiguation wsd"),
    (r"thematic roles?|vai trò chủ đề", "thematic role vai trò chủ đề"),
    (r"local discourse context|ngữ cảnh diễn ngôn cục bộ", "local discourse context ngữ cảnh diễn ngôn"),
    (r"\bdiscourse\b|diễn ngôn", "discourse diễn ngôn"),
    (r"\banaphora\b|đồng tham chiếu", "anaphora đồng tham chiếu"),
    (r"\bcentering\b|xác định tâm", "centering xác định tâm"),
    (r"\bunification\b|hợp nhất", "unification hợp nhất"),
    (r"part[- ]of[- ]speech tagging|pos tagging|gán nhãn từ loại", "pos tagging gán nhãn từ loại"),
    (r"\bparsing\b|\bparser\b|phân tích cú pháp", "parsing parser phân tích cú pháp"),
    (r"\bgrammar\b|văn phạm", "grammar văn phạm"),
    (r"\bsyntactic\b|\bsyntax\b|cú pháp", "syntactic cú pháp"),
    (r"\bsemantics?\b|ngữ nghĩa", "semantic ngữ nghĩa"),
    (r"\bambiguity\b|nhập nhằng", "ambiguity nhập nhằng"),
    (r"\bprobabilit(?:y|ies)\b|xác suất", "probability xác suất"),
    (r"\bstatistical\b|thống kê", "statistical thống kê"),
    (r"\breference\b|tham chiếu", "reference tham chiếu"),
    (r"\bevaluation\b|\bevaluate\b|đánh giá", "evaluation đánh giá"),
    (r"\bassessment\b", "assessment đánh giá điểm"),
    (r"\btextbook\b|giáo trình|\bsách\b", "textbook giáo trình sách"),
    (r"\bresources?\b|tài liệu", "resources tài liệu"),
    (r"\bpython\b", "python lập trình"),
    (r"\battendance\b|điểm danh|chuyên cần", "attendance điểm danh chuyên cần"),
    (r"academic integrity|liêm chính học thuật|gian lận", "academic integrity liêm chính học thuật"),
    (r"\bsubmission\b|nộp bài|\bnộp\b", "submission nộp"),
    (r"\bmilestone\b|\bcheckpoint\b|deadline|hạn nộp|mốc", "milestone checkpoint deadline hạn nộp"),
    (r"\btopics?\b|chủ đề", "topics chủ đề nội dung"),
    (r"\boutputs?\b|\bxuất\b", "output xuất file"),
    (r"\blearning outcomes?\b|chuẩn đầu ra|\blo\d\d\b", "learning outcome chuẩn đầu ra"),
    (r"\binstructor\b|\blecturer\b|giảng viên", "instructor giảng viên"),
    (r"\bteam\b|thành viên|nhóm|mấy người|bao nhiêu người", "team nhóm thành viên người students"),
    (r"\bexams?\b|\bthi\b", "exam thi"),
    (r"\bsummary\b|tóm tắt", "summary tóm tắt"),
    (r"\bintroduction\b|giới thiệu|tổng quan", "introduction giới thiệu tổng quan"),
]
_GLOSSARY = [(re.compile(p), add) for p, add in GLOSSARY]


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    return re.sub(r"\s+", " ", text).strip()


def canonical(text: str, expand: bool = True) -> str:
    text = normalize(text).lower()
    for pattern, repl in _CANON_RULES:
        text = pattern.sub(repl, text)
    text = re.sub(r"\s+", " ", text).strip()
    if expand:
        extra = [add for pattern, add in _GLOSSARY if pattern.search(text)]
        if extra:
            text = text + " | " + " ".join(extra)
    return text


def tokenize(text: str, expand: bool = False) -> List[str]:
    return _WORD_RE.findall(canonical(text, expand))


def content_tokens(text: str, extra_stop: Iterable[str] = ()) -> List[str]:
    stop = STOPWORDS | set(extra_stop)
    return [t for t in tokenize(text) if t not in stop]


def bigrams(tokens: List[str]) -> List[str]:
    return [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]


def terms(text: str, expand: bool = True) -> List[str]:
    """Đặc trưng cho BM25: âm tiết + bigram âm tiết (xấp xỉ từ ghép tiếng Việt)."""
    toks = tokenize(text, expand)
    return toks + bigrams(toks)


def key_units(text: str, ignore: Set[str]) -> Tuple[List[str], List[str]]:
    """Từ khóa của câu hỏi (không mở rộng glossary): âm tiết + bigram của 2 từ khóa liền kề."""
    toks = tokenize(text)
    keys = [t for t in toks if t not in ignore]
    bis = [f"{a}_{b}" for a, b in zip(toks, toks[1:]) if a not in ignore and b not in ignore]
    return keys, bis


def unit_coverage(text: str, vocab: Set[str], ignore: Set[str]) -> Tuple[float, List[str]]:
    """Độ phủ = 0.5*phủ âm tiết + 0.5*phủ bigram (chỉ âm tiết nếu câu không có bigram khóa)."""
    keys, bis = key_units(text, ignore)
    if not keys:
        return 1.0, []
    missing = [k for k in keys + bis if k not in vocab]
    uni = sum(k in vocab for k in keys) / len(keys)
    if not bis:
        return uni, missing
    return 0.5 * uni + 0.5 * sum(b in vocab for b in bis) / len(bis), missing


_CODE_RE = re.compile(r"\b(chương \d+|tuần \d+|lo\d\d|phần (?:iv|iii|ii|i))\b")


def codes(text: str) -> Set[str]:
    """Mã định danh trong câu/tài liệu: "chương 4", "tuần 3", "lo25", "phần i"."""
    return set(_CODE_RE.findall(canonical(text, expand=False)))


def asked_type(text: str) -> str:
    """Loại đối tượng được hỏi: 'chương' (chương nào?), 'tuần' (tuần nào?) hoặc ''."""
    low = canonical(text, expand=False)
    if re.search(r"\bchương (?:nào|mấy)\b", low):
        return "chương"
    if re.search(r"\btuần (?:nào|mấy)\b|học vào (?:lúc )?nào", low):
        return "tuần"
    return ""
