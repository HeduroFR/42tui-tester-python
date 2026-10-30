"""Shared checks and structured results for the version 1.0 bis subjects."""

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

from rich.markup import escape
from rich.panel import Panel
from germinette.core import BaseTester, console


class BisTester(BaseTester):
    def __init__(self):
        super().__init__()
        self.checks = []

    def run(self, exercise_name=None):
        if exercise_name and exercise_name.replace(".py", "") not in {
            name for name, _ in self.exercises
        }:
            self.record(
                "Exercise filter",
                "failed",
                f"Unknown exercise: {exercise_name}",
            )
            self.display_error_report()
            return
        super().run(exercise_name)

    def display_error_report(self):
        if self.grouped_errors:
            console.rule("[bold red]Detailed Error Report[/bold red]")
            for label, messages in self.grouped_errors.items():
                console.print(
                    Panel("\n\n".join(messages), title=escape(label))
                )
        report = self.report()
        console.rule("[bold cyan]Summary[/bold cyan]")
        console.print(
            f"Passed: {report['passed']}  Failed: {report['failed']}  "
            f"Errors: {report['errors']}  Skipped: {report['skipped']}"
        )
        if report["skipped"]:
            console.print("[yellow]Some checks did not run.[/yellow]")

    def record(self, name, status, message=""):
        self.checks.append(
            {"name": name, "status": status, "message": message}
        )
        if status == "passed":
            self.mark_ok()
            console.print(f"[green]OK[/green] {escape(name)}")
        elif status == "skipped":
            console.print(
                f"[yellow]SKIP[/yellow] {escape(name)}: {escape(message)}"
            )
        else:
            self.record_error(
                name,
                "Error" if status == "errors" else "Check failed",
                escape(message),
            )
            console.print(f"[red]KO[/red] {escape(name)}")
        return status == "passed"

    def check(self, name, condition, message):
        return self.record(
            name,
            "passed" if condition else "failed",
            "" if condition else message,
        )

    def files(self, name, paths):
        missing = [str(path) for path in paths if not Path(path).is_file()]
        return self.check(
            name, not missing, "Missing files: " + ", ".join(missing)
        )

    def process(self, name, args, *, cwd=None, env=None):
        try:
            return subprocess.run(
                args,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.record(name, "errors", str(exc))
            return None

    def script(self, path, *, env=None):
        result = self.process(str(path), [sys.executable, str(path)], env=env)
        if result is not None:
            self.check(
                str(path),
                result.returncode == 0,
                "Unexpected exit status.\n" + result.stdout + result.stderr,
            )
        return result

    def expected_exception(self, path, exception):
        result = self.process(str(path), [sys.executable, str(path)])
        if result is not None:
            self.check(
                str(path),
                result.returncode == 0 or exception in result.stderr,
                "Expected success with the exception handled, or an uncaught "
                + exception
                + ".\n"
                + result.stdout
                + result.stderr,
            )

    def probe(self, name, source, *, can_skip=False):
        result = self.process(name, [sys.executable, "-c", source])
        if result is not None:
            if can_skip and result.returncode == 77:
                return self.record(name, "skipped", result.stdout.strip())
            return self.check(
                name,
                result.returncode == 0,
                result.stdout + result.stderr
                or "Behavior did not match the subject.",
            )
        return False

    def tree(self, path):
        try:
            return ast.parse(Path(path).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, SyntaxError) as exc:
            self.check(f"{path}: syntax", False, str(exc))
            return None

    def lint(self, name, paths):
        if importlib.util.find_spec("flake8") is None:
            self.record(
                name, "skipped", "Install flake8 in the tester environment."
            )
            return
        result = self.process(
            name, [sys.executable, "-m", "flake8", *map(str, paths)]
        )
        if result is None:
            return
        if result.returncode > 1:
            self.record(name, "errors", result.stderr or result.stdout)
        else:
            self.check(
                name, result.returncode == 0, result.stdout or result.stderr
            )

    def policy(self, name, paths, *, no_syspath=False):
        violations = []
        for path in paths:
            tree = self.tree(path)
            if tree is None:
                continue
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in {"eval", "exec"}
                ):
                    violations.append(
                        f"{path}:{node.lineno}: forbidden {node.func.id}()"
                    )
                if no_syspath:
                    target = None
                    if isinstance(
                        node, (ast.Assign, ast.AnnAssign, ast.AugAssign)
                    ):
                        targets = (
                            node.targets
                            if isinstance(node, ast.Assign)
                            else [node.target]
                        )
                        target = any(
                            isinstance(part, ast.Attribute)
                            and part.attr == "path"
                            and isinstance(part.value, ast.Name)
                            and part.value.id == "sys"
                            for item in targets
                            for part in ast.walk(item)
                        )
                    if isinstance(node, ast.Call) and isinstance(
                        node.func, ast.Attribute
                    ):
                        obj = node.func.value
                        target = target or (
                            node.func.attr
                            in {
                                "append",
                                "insert",
                                "extend",
                                "remove",
                                "pop",
                                "clear",
                                "reverse",
                                "sort",
                            }
                            and isinstance(obj, ast.Attribute)
                            and obj.attr == "path"
                            and isinstance(obj.value, ast.Name)
                            and obj.value.id == "sys"
                        )
                    if target:
                        violations.append(
                            f"{path}:{node.lineno}: modifies sys.path"
                        )
        self.check(name, not violations, "\n".join(violations))

    def report(self):
        counts = {
            status: sum(item["status"] == status for item in self.checks)
            for status in ("passed", "failed", "errors", "skipped")
        }
        return {
            "version": 1,
            "total": len(self.checks),
            **counts,
            "checks": self.checks,
        }
