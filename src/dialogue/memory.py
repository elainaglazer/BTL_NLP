from typing import Dict
from src.interfaces import ContextResolver, ContextResolution, TurnResult

class RuleBasedContextResolver(ContextResolver):
    def __init__(self):
        self.history_entities: Dict[str, str] = {}

    def resolve(self, sentence: str) -> ContextResolution:
        resolved_sentence = sentence
        used_context = {}
        
        # Xử lý tham chiếu cục bộ cơ bản
        keywords = ["phần này", "nó", "đó", "nội dung đó"]
        if any(kw in sentence.lower() for kw in keywords):
            for key in ["TOPIC_NP", "ASSIGN_NP", "COURSE_NP"]:
                if key in self.history_entities:
                    used_context[key] = self.history_entities[key]
                    for kw in keywords:
                        resolved_sentence = resolved_sentence.replace(kw, self.history_entities[key])
                    break
                    
        return ContextResolution(
            original=sentence,
            resolved=resolved_sentence,
            used_context=used_context
        )

    def update(self, turn: TurnResult) -> None:
        if turn.parse and turn.parse.parsed:
            for k, v in turn.parse.entities.items():
                self.history_entities[k] = v

    def reset(self) -> None:
        self.history_entities.clear()

def create_context(config: dict):
    return RuleBasedContextResolver()