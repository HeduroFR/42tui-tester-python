"""Legacy reports must not claim unverified successes."""

import json
import sys

import pytest

from germinette.core import BaseTester


def test_legacy_report_never_invents_passes():
    tester = BaseTester()
    report = tester.report()
    assert report["passed"] == report["failed"] == 0
    assert report["total"] == report["skipped"] == 1
    assert report["incomplete"] is True
    tester.record_error("Exercise 1", "Mismatch", "bad output")
    report = tester.report()
    assert (
        report["total"],
        report["passed"],
        report["failed"],
        report["skipped"],
    ) == (2, 0, 1, 1)


def test_cli_legacy_missing_files_reports_recorded_failures(
    tmp_path, monkeypatch
):
    from germinette import __main__

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        __main__, "check_update", lambda _: (False, None, False)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["germinette", "python_module_00", "--report", "result.json"],
    )
    with pytest.raises(SystemExit) as exit_code:
        __main__.main()
    assert exit_code.value.code == 1
    report = json.loads((tmp_path / "result.json").read_text())
    assert report["version"] == 1
    assert report["failed"] > 0 and report["skipped"] == 1
    assert report["passed"] == 0 and report["incomplete"] is True


def test_incomplete_report_does_not_announce_all_passed(
    tmp_path, monkeypatch, capsys
):
    from germinette import __main__

    class Runner:
        def __init__(self):
            self.last_tester = BaseTester()

        def list_modules(self):
            return ["python_module_00"]

        def run_module(self, *args, **kwargs):
            return True

        @staticmethod
        def cleanup_pycache():
            pass

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(__main__, "GerminetteRunner", Runner)
    monkeypatch.setattr(
        __main__, "check_update", lambda _: (False, None, False)
    )
    monkeypatch.setattr(
        sys,
        "argv",
        ["germinette", "python_module_00", "--report", "result.json"],
    )
    with pytest.raises(SystemExit) as exit_code:
        __main__.main()
    assert exit_code.value.code == 0
    assert "All exercises passed" not in capsys.readouterr().out
    assert json.loads((tmp_path / "result.json").read_text())["incomplete"]
