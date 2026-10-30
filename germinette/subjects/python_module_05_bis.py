"""The Codex: Packages, Environments and the Alchemist's Toolchain v1.0."""

import ast
import importlib.util
import os
import shutil
import sys
import tempfile
import venv
from pathlib import Path

from germinette.subjects.bis_common import BisTester


class Tester(BisTester):
    def __init__(self):
        super().__init__()
        self.title = (
            "[bold cyan]Testing Module 05 bis: The Codex (v1.0)[/bold cyan]"
        )
        self.exercises = [
            ("ex0", self.ex0),
            ("ex1", self.ex1),
            ("alembic", self.alembic),
            ("transmutation", self.transmutation),
            ("grimoire", self.grimoire),
        ]

    def ex0(self):
        if not self.files(
            "Exercise 0 files",
            [
                "ex0/construct.py",
                "ex0/loading.py",
                "ex0/requirements.txt",
                "ex0/pyproject.toml",
            ],
        ):
            return
        self.lint("Exercise 0 flake8", ["ex0/construct.py", "ex0/loading.py"])
        self.policy(
            "Exercise 0 forbidden operations",
            ["ex0/construct.py", "ex0/loading.py"],
            no_syspath=True,
        )
        with tempfile.TemporaryDirectory(prefix="germinette-05-") as directory:
            root = Path(directory)
            shutil.copytree("ex0", root / "ex0")
            venv.create(root / "venv", with_pip=False)
            virtual = (
                root
                / "venv"
                / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            )
            base = getattr(sys, "_base_executable", None) or sys.executable
            outside = self.process(
                "Outside virtual environment",
                [base, "ex0/construct.py"],
                cwd=root,
            )
            inside = self.process(
                "Inside virtual environment",
                [str(virtual), "ex0/construct.py"],
                cwd=root,
            )
            if outside is not None and inside is not None:
                self.check(
                    "Environment detection",
                    outside.returncode == inside.returncode == 0
                    and outside.stdout != inside.stdout,
                    "construct.py must succeed inside and outside a venv "
                    "and display different information.",
                )
                self.check(
                    "Environment setup instructions",
                    "venv" in outside.stdout.lower()
                    and "activat" in outside.stdout.lower(),
                    "Outside a venv, show creation and activation "
                    "instructions.",
                )
            missing = self.process(
                "Missing dependencies",
                [str(virtual), "-S", "ex0/loading.py"],
                cwd=root,
            )
            if missing is not None:
                output = (missing.stdout + missing.stderr).lower()
                self.check(
                    "Missing dependency guidance",
                    missing.returncode == 0
                    and "pip" in output
                    and "poetry" in output,
                    "loading.py must handle missing dependencies and show "
                    "pip and Poetry guidance.",
                )
            loaded = self.process(
                "Installed dependencies",
                [sys.executable, "ex0/loading.py"],
                cwd=root,
            )
            if loaded is not None:
                self.check(
                    "Loading dependencies",
                    loaded.returncode == 0,
                    "loading.py must not crash.\n"
                    + loaded.stdout
                    + loaded.stderr,
                )
            for name in ("requirements.txt", "pyproject.toml"):
                text = (root / "ex0" / name).read_text(encoding="utf-8")
                self.check(
                    "Dependency declaration: " + name,
                    bool(text.strip()),
                    "Declare the dependencies used by loading.py.",
                )

    def ex1(self):
        if not self.files(
            "Exercise 1 files",
            [
                "ex1/oracle.py",
                "ex1/requirements.txt",
                "ex1/.env.example",
                "ex1/.gitignore",
            ],
        ):
            return
        self.lint("Exercise 1 flake8", ["ex1/oracle.py"])
        self.policy(
            "Exercise 1 forbidden operations",
            ["ex1/oracle.py"],
            no_syspath=True,
        )
        ignore = (
            Path("ex1/.gitignore").read_text(encoding="utf-8").splitlines()
        )
        self.check(
            "Ignore .env",
            any(line.strip() in (".env", "/.env") for line in ignore),
            "List .env in ex1/.gitignore.",
        )
        example = Path("ex1/.env.example").read_text(encoding="utf-8")
        keys = (
            "MATRIX_MODE",
            "DATABASE_URL",
            "API_KEY",
            "LOG_LEVEL",
            "ZION_ENDPOINT",
        )
        missing = [
            key
            for key in keys
            if not any(
                line.strip().split("=", 1)[0].strip() == key
                for line in example.splitlines()
                if "=" in line
            )
        ]
        self.check(
            "Example configuration",
            not missing,
            "Missing keys: " + ", ".join(missing),
        )
        tree = self.tree("ex1/oracle.py")
        if tree:
            imports = [
                n
                for n in ast.walk(tree)
                if isinstance(n, (ast.Import, ast.ImportFrom))
            ]
            self.check(
                "Use python-dotenv",
                any(
                    isinstance(n, ast.ImportFrom)
                    and n.module == "dotenv"
                    or isinstance(n, ast.Import)
                    and any(a.name == "dotenv" for a in n.names)
                    for n in imports
                ),
                "The subject requires python-dotenv.",
            )
        if importlib.util.find_spec("dotenv") is None:
            self.record(
                "Oracle runtime",
                "skipped",
                "Install python-dotenv in the tester environment.",
            )
            return
        with tempfile.TemporaryDirectory(prefix="germinette-05-") as directory:
            root = Path(directory)
            shutil.copytree(
                "ex1", root / "ex1", ignore=shutil.ignore_patterns(".env")
            )
            env = {
                key: value
                for key, value in os.environ.items()
                if key not in keys
            }
            empty = self.process(
                "Oracle without configuration",
                [sys.executable, "ex1/oracle.py"],
                cwd=root,
                env=env,
            )
            if empty is not None:
                self.check(
                    "Oracle without configuration",
                    empty.returncode == 0,
                    "The oracle must handle missing configuration "
                    "without crashing.",
                )
            (root / "ex1" / ".env").write_text(
                "MATRIX_MODE=development\nAPI_KEY=example-only\n",
                encoding="utf-8",
            )
            dev = self.process(
                "Oracle development",
                [sys.executable, "ex1/oracle.py"],
                cwd=root,
                env=env,
            )
            prod = self.process(
                "Oracle production",
                [sys.executable, "ex1/oracle.py"],
                cwd=root,
                env={
                    **env,
                    "MATRIX_MODE": "production",
                    "API_KEY": "example-override",
                },
            )
            if dev is not None and prod is not None:
                self.check(
                    "Development and production",
                    dev.returncode == prod.returncode == 0
                    and dev.stdout != prod.stdout,
                    "Show a visible difference when MATRIX_MODE "
                    "is overridden.",
                )

    def alembic(self):
        if self.files(
            "Exercise 2 files",
            [
                "elements.py",
                "alchemy/__init__.py",
                "alchemy/elements.py",
                "ft_alembic_0.py",
                "ft_alembic_1.py",
            ],
        ):
            self.lint(
                "Exercise 2 flake8",
                [
                    "elements.py",
                    "alchemy/__init__.py",
                    "alchemy/elements.py",
                    "ft_alembic_0.py",
                    "ft_alembic_1.py",
                ],
            )
            self.policy(
                "Exercise 2 forbidden operations",
                [
                    "elements.py",
                    "alchemy/__init__.py",
                    "alchemy/elements.py",
                    "ft_alembic_0.py",
                    "ft_alembic_1.py",
                ],
                no_syspath=True,
            )
            self.script("ft_alembic_0.py")
            self.probe(
                "Alembic package exports",
                """
import elements, alchemy
from alchemy import elements as local_elements
assert elements.create_fire() == "Fire element created"
assert elements.create_water() == "Water element created"
assert local_elements.create_earth() == "Earth element created"
assert local_elements.create_air() == "Air element created"
assert alchemy.create_air() == "Air element created"
assert not hasattr(alchemy, "create_earth")
""",
            )
            tree = self.tree("ft_alembic_1.py")
            if tree:
                aliases = {
                    alias.asname or alias.name
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Import)
                    for alias in node.names
                    if alias.name == "alchemy"
                }
                hidden_call = any(
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id in aliases
                    and node.func.attr == "create_earth"
                    for node in ast.walk(tree)
                )
                self.check(
                    "Alembic hidden access",
                    hidden_call,
                    "Use import alchemy and try alchemy.create_earth().",
                )
            self.expected_exception("ft_alembic_1.py", "AttributeError")

    def transmutation(self):
        if self.files(
            "Exercise 3 files",
            [
                "alchemy/potions.py",
                "alchemy/transmutation/__init__.py",
                "alchemy/transmutation/recipes.py",
                "ft_distillation_0.py",
                "ft_transmutation_0.py",
            ],
        ):
            self.lint(
                "Exercise 3 flake8",
                [
                    "alchemy/potions.py",
                    "alchemy/transmutation/__init__.py",
                    "alchemy/transmutation/recipes.py",
                    "ft_distillation_0.py",
                    "ft_transmutation_0.py",
                ],
            )
            self.policy(
                "Exercise 3 forbidden operations",
                [
                    "alchemy/potions.py",
                    "alchemy/transmutation/__init__.py",
                    "alchemy/transmutation/recipes.py",
                    "ft_distillation_0.py",
                    "ft_transmutation_0.py",
                ],
                no_syspath=True,
            )
            self.script("ft_distillation_0.py")
            self.script("ft_transmutation_0.py")
            self.probe(
                "Potion behavior",
                """
from alchemy.potions import healing_potion, strength_potion
assert "Earth element created" in healing_potion()
assert "Air element created" in healing_potion()
assert "Fire element created" in strength_potion()
assert "Water element created" in strength_potion()
""",
            )
            tree = self.tree("alchemy/transmutation/recipes.py")
            if tree:
                imports = [
                    n
                    for n in ast.walk(tree)
                    if isinstance(n, (ast.Import, ast.ImportFrom))
                ]
                relative = any(
                    isinstance(n, ast.ImportFrom) and n.level for n in imports
                )
                absolute = any(
                    isinstance(n, ast.Import)
                    or isinstance(n, ast.ImportFrom)
                    and not n.level
                    for n in imports
                )
                self.check(
                    "Recipe import styles",
                    relative and absolute,
                    "Use both absolute and relative imports.",
                )

    def grimoire(self):
        paths = [
            "alchemy/grimoire/__init__.py",
            "alchemy/grimoire/light_spellbook.py",
            "alchemy/grimoire/light_validator.py",
            "alchemy/grimoire/dark_spellbook.py",
            "alchemy/grimoire/dark_validator.py",
            "ft_kaboom_0.py",
            "ft_kaboom_1.py",
        ]
        if self.files("Exercise 4 files", paths):
            self.lint("Exercise 4 flake8", paths)
            self.policy(
                "Exercise 4 forbidden operations", paths, no_syspath=True
            )
            self.script("ft_kaboom_0.py")
            self.probe(
                "Light grimoire",
                """
from alchemy.grimoire.light_spellbook import light_spell_record
from alchemy.grimoire.light_validator import validate_ingredients
assert "VALID" in validate_ingredients("EARTH").upper()
assert "INVALID" in validate_ingredients("unknown").upper()
assert "VALID" in light_spell_record("test", "earth").upper()
assert "INVALID" in light_spell_record("test", "unknown").upper()
""",
            )
            self.probe(
                "Dark circular import",
                """
try:
    import alchemy.grimoire.dark_spellbook
except ImportError as error:
    message = str(error).lower()
    assert "circular import" in message or "partially initialized" in message
else:
    raise AssertionError("The dark circular import should fail")
""",
            )
            tree = self.tree("ft_kaboom_1.py")
            if tree:
                direct = any(
                    isinstance(node, ast.Import)
                    and any(
                        alias.name == "alchemy.grimoire.dark_spellbook"
                        for alias in node.names
                    )
                    or isinstance(node, ast.ImportFrom)
                    and (
                        node.module == "alchemy.grimoire.dark_spellbook"
                        or node.module == "alchemy.grimoire"
                        and any(
                            alias.name == "dark_spellbook"
                            for alias in node.names
                        )
                    )
                    for node in ast.walk(tree)
                )
                self.check(
                    "Dark spellbook demonstration",
                    direct,
                    "Import the dark spellbook directly in ft_kaboom_1.py.",
                )
            self.expected_exception("ft_kaboom_1.py", "ImportError")
