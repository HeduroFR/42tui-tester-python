"""Regression checks for the bis subjects and their portable report."""

import json
from pathlib import Path

import pytest

from germinette.subjects.python_module_05_bis import Tester as CodexTester
from germinette.subjects.python_module_06_bis import Tester as NexusTester


def test_missing_files_fail_for_both_subjects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for tester in (CodexTester(), NexusTester()):
        tester.run()
        report = tester.report()
        assert report["version"] == 1
        assert report["total"] == 5
        assert report["failed"] == 5
        assert report["passed"] == 0
        assert len(report["checks"]) == 5


def test_nexus_processor_checks_structure_and_execution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    Path("data_processor.py").write_text(
        "class DataProcessor:\n    pass\n", encoding="utf-8"
    )
    tester = NexusTester()
    tester.run("data_processor")
    assert tester.report()["failed"] == 5
    assert tester.report()["passed"] == 4


def test_cli_report_contains_failed_results(tmp_path, monkeypatch):
    from germinette import __main__

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        __main__, "check_update", lambda _: (False, None, False)
    )
    monkeypatch.setattr(
        "sys.argv",
        ["germinette", "python_module_05_bis", "--report", "result.json"],
    )
    with pytest.raises(SystemExit) as exit_code:
        __main__.main()
    assert exit_code.value.code == 1
    report = json.loads(Path("result.json").read_text())
    assert report["total"] == report["failed"] == 5


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_codex_environment_checks_inside_outside_and_missing_packages(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write(
        Path("ex0/construct.py"),
        """import sys
if sys.prefix == sys.base_prefix:
    print("open: python3 -m venv lab_env; source lab_env/bin/activate")
else:
    print("sealed:", sys.prefix)
""",
    )
    write(
        Path("ex0/loading.py"),
        """print("pip install -r requirements.txt; poetry install")
""",
    )
    write(Path("ex0/requirements.txt"), "numpy\n")
    write(Path("ex0/pyproject.toml"), '[project]\nname="student"\n')
    tester = CodexTester()
    tester.run("ex0")
    assert not tester.grouped_errors
    assert tester.report()["passed"] >= 5


def test_codex_alembic_accepts_expected_exception(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write(
        Path("elements.py"),
        'def create_fire(): return "Fire element created"\n'
        'def create_water(): return "Water element created"\n',
    )
    write(
        Path("alchemy/elements.py"),
        'def create_earth(): return "Earth element created"\n'
        'def create_air(): return "Air element created"\n',
    )
    write(
        Path("alchemy/__init__.py"),
        'from .elements import create_air\n\n__all__ = ["create_air"]\n',
    )
    write(
        Path("ft_alembic_0.py"),
        "import elements\nprint(elements.create_fire())\n",
    )
    write(Path("ft_alembic_1.py"), "import alchemy\nalchemy.create_earth()\n")
    tester = CodexTester()
    tester.run("alembic")
    assert not tester.grouped_errors
    write(Path("ft_alembic_1.py"), 'raise ValueError("wrong exception")\n')
    tester = CodexTester()
    tester.run("alembic")
    assert tester.report()["failed"] == 2
    write(Path("ft_alembic_1.py"), 'print("no demonstration")\n')
    tester = CodexTester()
    tester.run("alembic")
    hidden = next(
        c for c in tester.checks if c["name"] == "Alembic hidden access"
    )
    assert hidden["status"] == "failed"


def test_report_skipped_counts_and_incomplete_run(tmp_path, monkeypatch):
    from germinette.core import GerminetteRunner
    from germinette.subjects.bis_common import BisTester

    tester = BisTester()
    tester.record("missing dependency", "skipped", "not installed")
    report = tester.report()
    assert report["skipped"] == report["total"] == 1
    monkeypatch.chdir(tmp_path)
    write(Path("ex1/oracle.py"), "import dotenv\ndotenv.load_dotenv()\n")
    write(Path("ex1/requirements.txt"), "python-dotenv\n")
    write(
        Path("ex1/.env.example"),
        "\n".join(
            f"{key}="
            for key in (
                "MATRIX_MODE",
                "DATABASE_URL",
                "API_KEY",
                "LOG_LEVEL",
                "ZION_ENDPOINT",
            )
        ),
    )
    write(Path("ex1/.gitignore"), ".env\n")
    from importlib.util import find_spec

    monkeypatch.setattr(
        "germinette.subjects.python_module_05_bis.importlib.util.find_spec",
        lambda name: None if name == "dotenv" else find_spec(name),
    )
    runner = GerminetteRunner()
    assert runner.run_module("python_module_05_bis", "ex1") is None
    assert runner.last_tester.report()["skipped"] == 1


def test_unknown_exercise_produces_reported_failure(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    tester = CodexTester()
    tester.run("not-an-exercise")
    assert tester.report()["failed"] == 1
    assert tester.report()["total"] == 1


def test_policy_distinguishes_reading_and_mutating_sys_path(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    path = Path("example.py")
    path.write_text("import sys\nprint(sys.path)\n", encoding="utf-8")
    tester = CodexTester()
    tester.policy("policy", [path], no_syspath=True)
    assert tester.report()["passed"] == 1
    path.write_text(
        'import sys\nsys.path.append("example")\n', encoding="utf-8"
    )
    tester = CodexTester()
    tester.policy("policy", [path], no_syspath=True)
    assert tester.report()["failed"] == 1


def test_nexus_processor_passing_and_invalid_ingestion(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write(
        Path("data_processor.py"),
        """from abc import ABC, abstractmethod


class DataProcessor(ABC):
    def __init__(self):
        self.items = []
        self.rank = 0

    @abstractmethod
    def validate(self, data):
        pass

    @abstractmethod
    def ingest(self, data):
        pass

    def output(self):
        rank = self.rank
        self.rank += 1
        return rank, self.items.pop(0)


class NumericProcessor(DataProcessor):
    def validate(self, data):
        if isinstance(data, list):
            return all(isinstance(x, (int, float)) for x in data)
        return isinstance(data, (int, float))

    def ingest(self, data):
        if not self.validate(data):
            raise ValueError('invalid')
        values = data if isinstance(data, list) else [data]
        self.items.extend(str(x) for x in values)


class TextProcessor(DataProcessor):
    def validate(self, data):
        if isinstance(data, list):
            return all(isinstance(x, str) for x in data)
        return isinstance(data, str)

    def ingest(self, data):
        if not self.validate(data):
            raise ValueError('invalid')
        self.items.extend(data if isinstance(data, list) else [data])


class LogProcessor(DataProcessor):
    def validate(self, data):
        if isinstance(data, list):
            return all(isinstance(x, dict) for x in data)
        return isinstance(data, dict)

    def ingest(self, data):
        if not self.validate(data):
            raise ValueError('invalid')
        values = data if isinstance(data, list) else [data]
        self.items.extend(str(x) for x in values)
""",
    )
    tester = NexusTester()
    tester.run("data_processor")
    assert not tester.grouped_errors
    assert tester.report()["passed"] >= 8


def test_factory_contract_requires_two_implementations(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write(
        Path("ex3/factories.py"),
        """from abc import ABC, abstractmethod


class Family(ABC):
    @abstractmethod
    def create_base(self):
        pass

    @abstractmethod
    def create_evolved(self):
        pass


class FireFamily(Family):
    pass


class WaterFamily(Family):
    pass
""",
    )
    tester = NexusTester()
    tester.package_contract(
        "ex3", [("Factory interface", {"create_base", "create_evolved"})]
    )
    assert tester.report()["passed"] == 2
    file = Path("ex3/factories.py")
    file.write_text(
        file.read_text().replace(
            "class WaterFamily(Family):", "class WaterFamily:"
        ),
        encoding="utf-8",
    )
    tester = NexusTester()
    tester.package_contract(
        "ex3", [("Factory interface", {"create_base", "create_evolved"})]
    )
    assert tester.report()["failed"] == 1


def test_factory_runtime_checks_transform_and_package_exports(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write(
        Path("ex3/__init__.py"),
        """from .models import PlainFactory, MorphFactory

__all__ = ["PlainFactory", "MorphFactory"]
""",
    )
    write(
        Path("ex3/models.py"),
        """from abc import ABC, abstractmethod


class Being(ABC):
    @abstractmethod
    def attack(self):
        pass

    def describe(self):
        return "Being"


class Power(ABC):
    @abstractmethod
    def transform(self):
        pass

    @abstractmethod
    def revert(self):
        pass


class Plain(Being):
    def attack(self):
        return "normal"


class Morph(Being, Power):
    def __init__(self):
        self.active = False

    def attack(self):
        return "changed" if self.active else "normal"

    def transform(self):
        self.active = True

    def revert(self):
        self.active = False


class Family(ABC):
    @abstractmethod
    def create_base(self):
        pass

    @abstractmethod
    def create_evolved(self):
        pass


class PlainFactory(Family):
    def create_base(self):
        return Plain()

    def create_evolved(self):
        return Plain()


class MorphFactory(Family):
    def create_base(self):
        return Morph()

    def create_evolved(self):
        return Morph()
""",
    )
    write(Path("battle.py"), 'print("battle")\n')
    write(Path("capacitor.py"), 'print("transform")\n')
    tester = NexusTester()
    tester.run("ex3")
    check = next(
        c
        for c in tester.checks
        if c["name"] == "Factory and capability behavior"
    )
    assert check["status"] == "passed", check
    path = Path("ex3/models.py")
    path.write_text(
        path.read_text().replace("self.active = True", "self.active = False")
    )
    tester = NexusTester()
    tester.run("ex3")
    check = next(
        c
        for c in tester.checks
        if c["name"] == "Factory and capability behavior"
    )
    assert check["status"] == "failed", check
    text = path.read_text().replace(
        "def transform(self):\n        self.active = False",
        "def transform(self):\n        self.active = True",
    )
    text = text.replace(
        "class PlainFactory(Family):\n",
        "class PlainFactory(Family):\n    def __init__(self, name):\n"
        "        self.name = name\n\n",
    )
    path.write_text(text)
    from germinette.core import GerminetteRunner

    runner = GerminetteRunner()
    assert runner.run_module("python_module_06_bis", "ex3") is None
    check = next(
        c
        for c in runner.last_tester.checks
        if c["name"] == "Factory and capability behavior"
    )
    assert check["status"] == "skipped", check


def test_strategy_runtime_checks_order_and_invalid_entity(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    write(Path("ex3/__init__.py"), "")
    write(
        Path("ex3/models.py"),
        """from abc import ABC, abstractmethod


class Power(ABC):
    @abstractmethod
    def transform(self):
        pass

    @abstractmethod
    def revert(self):
        pass


class Plain:
    def attack(self):
        return "normal"


class Morph(Power):
    def attack(self):
        return "attack"

    def transform(self):
        pass

    def revert(self):
        pass


class Factory:
    def create_base(self):
        return Plain()

    def create_evolved(self):
        return Plain()


class MorphFactory:
    def create_base(self):
        return Morph()

    def create_evolved(self):
        return Morph()
""",
    )
    write(
        Path("ex4/__init__.py"),
        """from abc import ABC, abstractmethod
from ex3.models import Power


class Strategy(ABC):
    @abstractmethod
    def act(self, entity):
        pass

    @abstractmethod
    def is_valid(self, entity):
        pass


class Normal(Strategy):
    def is_valid(self, entity):
        return True

    def act(self, entity):
        entity.attack()


class Aggressive(Strategy):
    def is_valid(self, entity):
        return isinstance(entity, Power)

    def act(self, entity):
        if not self.is_valid(entity):
            raise ValueError("invalid")
        entity.transform()
        entity.attack()
        entity.revert()
""",
    )
    write(Path("tournament.py"), 'print("tournament")\n')
    tester = NexusTester()
    tester.run("ex4")
    result = next(c for c in tester.checks if c["name"] == "Strategy behavior")
    assert result["status"] == "passed", result
    path = Path("ex4/__init__.py")
    path.write_text(path.read_text().replace("        entity.revert()\n", ""))
    tester = NexusTester()
    tester.run("ex4")
    result = next(c for c in tester.checks if c["name"] == "Strategy behavior")
    assert result["status"] == "failed", result
