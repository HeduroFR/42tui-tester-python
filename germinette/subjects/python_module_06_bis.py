"""Code Nexus: Abstract Architecture v1.0."""

import ast
from pathlib import Path

from germinette.subjects.bis_common import BisTester


class Tester(BisTester):
    def __init__(self):
        super().__init__()
        self.title = (
            "[bold cyan]Testing Module 06 bis: Code Nexus (v1.0)[/bold cyan]"
        )
        self.exercises = [
            ("data_processor", self.processor),
            ("data_stream", self.stream),
            ("data_pipeline", self.pipeline),
            ("ex3", self.factories),
            ("ex4", self.strategies),
        ]

    def classes(self, path, required):
        tree = self.tree(path)
        if tree is None:
            return
        classes = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef)
        }
        for name, methods in required.items():
            node = classes.get(name)
            found = (
                {
                    n.name
                    for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                if node
                else set()
            )
            self.check(
                f"{path}: {name}",
                node is not None and set(methods) <= found,
                f'{name} must define: {", ".join(methods)}',
            )

    def processor(self):
        path = "data_processor.py"
        if self.files("Exercise 0 files", [path]):
            self.lint(f"{path}: flake8", [path])
            self.policy(f"{path}: forbidden operations", [path])
            self.classes(
                path,
                {
                    "DataProcessor": ["validate", "ingest", "output"],
                    "NumericProcessor": ["validate", "ingest"],
                    "TextProcessor": ["validate", "ingest"],
                    "LogProcessor": ["validate", "ingest"],
                },
            )
            self.script(path)
            self.probe(
                "Processor validation and FIFO",
                """
from data_processor import NumericProcessor, TextProcessor, LogProcessor
for cls, valid, invalid in ((NumericProcessor, [1, 2.5], "text"),
                            (TextProcessor, ["one", "two"], 42),
                            (LogProcessor, [{"log_level": "INFO",
                                             "log_message": "ok"}], 42)):
    processor = cls()
    assert processor.validate(valid) is True
    assert processor.validate(invalid) is False
    try:
        processor.ingest(invalid)
    except Exception:
        pass
    else:
        raise AssertionError("Invalid ingestion must raise an exception")
    processor.ingest(valid)
    result = processor.output()
    assert isinstance(result, tuple) and len(result) == 2
    assert isinstance(result[0], int) and isinstance(result[1], str)
    if cls is NumericProcessor:
        assert result[1] == "1"
        assert processor.output()[1] == "2.5"
    if cls is TextProcessor:
        assert result[1] == "one"
        assert processor.output()[1] == "two"
""",
            )

    def stream(self):
        path = "data_stream.py"
        if self.files("Exercise 1 files", [path]):
            self.lint(f"{path}: flake8", [path])
            self.policy(f"{path}: forbidden operations", [path])
            self.classes(
                path,
                {
                    "DataStream": [
                        "register_processor",
                        "process_stream",
                        "print_processors_stats",
                    ]
                },
            )
            self.script(path)
            self.probe(
                "Stream routing",
                """
from data_stream import (DataStream, NumericProcessor, TextProcessor,
                         LogProcessor)
stream = DataStream()
numeric, text, logs = NumericProcessor(), TextProcessor(), LogProcessor()
for processor in (numeric, text, logs):
    stream.register_processor(processor)
stream.process_stream([42, "hello", {"log_level": "INFO",
                                     "log_message": "test"}])
assert numeric.output()[1] == "42"
assert text.output()[1] == "hello"
assert "test" in logs.output()[1]
stream.print_processors_stats()
""",
            )

    def pipeline(self):
        path = "data_pipeline.py"
        if self.files("Exercise 2 files", [path]):
            self.lint(f"{path}: flake8", [path])
            self.policy(f"{path}: forbidden operations", [path])
            self.classes(
                path,
                {
                    "ExportPlugin": ["process_output"],
                    "DataStream": ["output_pipeline"],
                },
            )
            self.script(path)
            self.probe(
                "Pipeline plugin dispatch",
                """
from data_pipeline import DataStream, NumericProcessor
class Plugin:
    def __init__(self): self.received = []
    def process_output(self, data): self.received.extend(data)
stream = DataStream()
stream.register_processor(NumericProcessor())
stream.process_stream([10, 20])
plugin = Plugin()
stream.output_pipeline(2, plugin)
assert len(plugin.received) == 2
assert [item[1] for item in plugin.received] == ["10", "20"]
""",
            )

    def factories(self):
        if self.files(
            "Exercise 3 files",
            ["ex3/__init__.py", "battle.py", "capacitor.py"],
        ):
            self.lint(
                "Exercise 3 flake8",
                ["battle.py", "capacitor.py", *Path("ex3").rglob("*.py")],
            )
            self.policy(
                "Exercise 3 forbidden operations",
                ["battle.py", "capacitor.py", *Path("ex3").rglob("*.py")],
            )
            self.script("battle.py")
            self.script("capacitor.py")
            self.probe(
                "Factory and capability behavior",
                """
import importlib
import inspect
import pkgutil
import sys
import ex3

modules = [ex3]
modules.extend(importlib.import_module(info.name) for info in
               pkgutil.walk_packages(ex3.__path__, ex3.__name__ + "."))
classes = {value for module in modules for value in vars(module).values()
           if inspect.isclass(value) and value.__module__.startswith("ex3")}

def abstract_with(methods):
    return [cls for cls in classes if inspect.isabstract(cls)
            and methods <= getattr(cls, "__abstractmethods__", set())]

creatures = [cls for cls in abstract_with({"attack"})
             if callable(getattr(cls, "describe", None))]
capabilities = abstract_with({"transform", "revert"})
factories = abstract_with({"create_base", "create_evolved"})
assert creatures and capabilities and factories, "Missing abstract interfaces"
assert all(not issubclass(cap, creature) for cap in capabilities
           for creature in creatures), "Capability must not inherit Creature"
concrete = [cls for cls in classes if not inspect.isabstract(cls)
            and any(issubclass(cls, base) for base in factories)]
assert len(concrete) >= 2, "Two concrete factories are required"
exported = {value for key, value in vars(ex3).items()
            if not key.startswith("_") and inspect.isclass(value)
            and value.__module__.startswith("ex3")}
assert all(inspect.isabstract(cls) or
           not any(issubclass(cls, creature) for creature in creatures)
           for cls in exported), "Do not expose concrete entities"
assert set(concrete) <= exported, "The package must expose the factories"
instances = []
for cls in concrete:
    try:
        inspect.signature(cls).bind()
    except TypeError:
        print("Factory constructor needs arguments; review behavior manually.")
        sys.exit(77)
    factory = cls()
    for method in (factory.create_base, factory.create_evolved):
        try:
            inspect.signature(method).bind()
        except TypeError:
            print("Factory creation needs arguments; review manually.")
            sys.exit(77)
        entity = method()
        assert any(isinstance(entity, base) for base in creatures)
        assert isinstance(entity.describe(), str)
        before = entity.attack()
        assert isinstance(before, str)
        if any(isinstance(entity, cap) for cap in capabilities):
            entity.transform()
            transformed = entity.attack()
            assert isinstance(transformed, str) and transformed != before
            entity.revert()
            assert isinstance(entity.attack(), str)
            assert entity.attack() != transformed
        instances.append(entity)
assert any(any(isinstance(entity, cap) for cap in capabilities)
           for entity in instances), "No transforming entity returned"
assert any(not any(isinstance(entity, cap) for cap in capabilities)
           for entity in instances), "No plain entity returned"
""",
                can_skip=True,
            )
            self.package_contract(
                "ex3",
                [
                    ("Creature interface", {"attack", "describe"}),
                    ("Transform capability", {"transform", "revert"}),
                    ("Factory interface", {"create_base", "create_evolved"}),
                ],
            )

    def strategies(self):
        if self.files(
            "Exercise 4 files", ["ex4/__init__.py", "tournament.py"]
        ):
            self.lint(
                "Exercise 4 flake8",
                ["tournament.py", *Path("ex4").rglob("*.py")],
            )
            self.policy(
                "Exercise 4 forbidden operations",
                ["tournament.py", *Path("ex4").rglob("*.py")],
            )
            self.script("tournament.py")
            self.probe(
                "Strategy behavior",
                """
import importlib
import inspect
import pkgutil
import sys
from unittest.mock import patch
import ex3
import ex4

def classes(package):
    modules = [package]
    modules.extend(importlib.import_module(info.name) for info in
                   pkgutil.walk_packages(package.__path__,
                                         package.__name__ + "."))
    return {value for module in modules for value in vars(module).values()
            if inspect.isclass(value)
            and value.__module__.startswith(package.__name__)}

def noargs(callable_):
    try:
        inspect.signature(callable_).bind()
    except TypeError:
        print("Factory or strategy requires arguments; review manually.")
        sys.exit(77)
    return callable_()

entity_classes = classes(ex3)
strategy_classes = classes(ex4)
capabilities = [cls for cls in entity_classes if inspect.isabstract(cls)
                and {"transform", "revert"} <= cls.__abstractmethods__]
factories = [cls for cls in entity_classes if not inspect.isabstract(cls)
             and callable(getattr(cls, "create_base", None))
             and callable(getattr(cls, "create_evolved", None))]
assert capabilities and factories, "Missing capability or concrete factories"
entities = [noargs(noargs(factory).create_base) for factory in factories]
plain = next((e for e in entities if not any(isinstance(e, c)
                                              for c in capabilities)), None)
morph = next((e for e in entities if any(isinstance(e, c)
                                          for c in capabilities)), None)
assert plain is not None and morph is not None, "Need both entity types"
strategies = [noargs(cls) for cls in strategy_classes
              if not inspect.isabstract(cls)
              and callable(getattr(cls, "act", None))
              and callable(getattr(cls, "is_valid", None))]
normal = next((s for s in strategies if s.is_valid(plain) is True
               and s.is_valid(morph) is True), None)
aggressive = next((s for s in strategies if s.is_valid(plain) is False
                   and s.is_valid(morph) is True), None)
assert normal is not None and aggressive is not None, "Missing strategies"
try:
    aggressive.act(plain)
except Exception:
    pass
else:
    raise AssertionError("Invalid strategy must raise an exception")

def calls(entity, strategy, names):
    events = []
    patches = []
    try:
        for name in names:
            original = getattr(entity, name)
            def wrapper(*args, _name=name, _original=original, **kwargs):
                events.append(_name)
                return _original(*args, **kwargs)
            item = patch.object(entity, name, side_effect=wrapper)
            try:
                item.start()
            except (AttributeError, TypeError):
                print("Cannot instrument entity methods; review manually.")
                sys.exit(77)
            patches.append(item)
        strategy.act(entity)
    finally:
        for item in reversed(patches):
            item.stop()
    return events

assert calls(plain, normal, ["attack"]) == ["attack"]
assert calls(morph, aggressive, ["transform", "attack", "revert"]) == [
    "transform", "attack", "revert"]
""",
                can_skip=True,
            )
            self.package_contract(
                "ex4", [("Strategy interface", {"act", "is_valid"})]
            )
            trees = [self.tree(path) for path in Path("ex4").rglob("*.py")]
            trees = [tree for tree in trees if tree]
            self.check(
                "Capability-based strategy",
                any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "isinstance"
                    for tree in trees
                    for node in ast.walk(tree)
                ),
                "The subject requires strategies to check capabilities "
                "using isinstance.",
            )

    def package_contract(self, directory, contracts):
        classes = []
        for path in Path(directory).rglob("*.py"):
            tree = self.tree(path)
            if tree:
                classes.extend(
                    node
                    for node in ast.walk(tree)
                    if isinstance(node, ast.ClassDef)
                )
        for label, required in contracts:
            abstract = required - {"describe"}
            candidates = []
            for cls in classes:
                methods = {
                    node.name: node
                    for node in cls.body
                    if isinstance(
                        node, (ast.FunctionDef, ast.AsyncFunctionDef)
                    )
                }
                if not required <= methods.keys():
                    continue

                def decorated(method):
                    return any(
                        (isinstance(d, ast.Name) and d.id == "abstractmethod")
                        or (
                            isinstance(d, ast.Attribute)
                            and d.attr == "abstractmethod"
                        )
                        for d in method.decorator_list
                    )

                bases = {
                    b.id if isinstance(b, ast.Name) else b.attr
                    for b in cls.bases
                    if isinstance(b, (ast.Name, ast.Attribute))
                }
                if "ABC" in bases and all(
                    decorated(methods[name]) for name in abstract
                ):
                    candidates.append(cls)
            self.check(
                label,
                bool(candidates),
                "Expected an ABC with abstract methods: "
                + ", ".join(sorted(abstract)),
            )
            if candidates and label in {
                "Factory interface",
                "Strategy interface",
            }:
                names = {candidate.name for candidate in candidates}
                concrete = [
                    cls
                    for cls in classes
                    if any(
                        (isinstance(base, ast.Name) and base.id in names)
                        or (
                            isinstance(base, ast.Attribute)
                            and base.attr in names
                        )
                        for base in cls.bases
                    )
                ]
                self.check(
                    label + " implementations",
                    len(concrete) >= 2,
                    "Expected at least two implementations of the "
                    "abstract interface.",
                )
