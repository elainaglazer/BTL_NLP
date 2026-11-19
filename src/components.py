"""Wire real TV2/TV3 factories here via models/config.json when their modules arrive."""
from importlib import import_module

from src.config import project_path
from src.parser_adapter import ParserAdapter
from src.pipeline import CourseAssistantPipeline


def _load_factory(spec, config):
    if spec is None:
        return None
    module, sep, name = spec.partition(":")
    if not sep or not module or not name:
        raise ValueError("Factory phải có dạng package.module:create_component")
    return getattr(import_module(module), name)(config)


def build_pipeline(config):
    components = config.get("components", {})
    return CourseAssistantPipeline(
        parser=ParserAdapter(project_path(config["grammar"])),
        context=_load_factory(components.get("context"), config),
        retriever=_load_factory(components.get("retriever"), config),
        generator=_load_factory(components.get("generator"), config),
        top_k=config.get("top_k", 3))
