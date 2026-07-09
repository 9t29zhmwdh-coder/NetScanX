from __future__ import annotations

import sys

import pytest

from netscanx.storage import paths


def test_is_frozen_false_by_default():
    assert paths.is_frozen() is False


def test_is_frozen_true_when_pyinstaller_attrs_set(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", "/tmp/fake", raising=False)
    assert paths.is_frozen() is True


def test_is_frozen_false_when_only_frozen_set(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    assert paths.is_frozen() is False


def test_get_executable_dir_uses_sys_executable(monkeypatch, tmp_path):
    fake_exe = tmp_path / "NetScanX-Start-Windows.exe"
    fake_exe.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    assert paths.get_executable_dir() == tmp_path.resolve()


def test_resolve_db_path_explicit_override(tmp_path):
    override = tmp_path / "custom" / "mydb.sqlite"
    resolved = paths.resolve_db_path(override=str(override))
    assert resolved == override.resolve()
    assert override.parent.is_dir()


def test_resolve_db_path_env_var(monkeypatch, tmp_path):
    env_path = tmp_path / "envdir" / "netscanx.db"
    monkeypatch.setenv("NETSCANX_DB_PATH", str(env_path))
    resolved = paths.resolve_db_path()
    assert resolved == env_path.resolve()
    assert env_path.parent.is_dir()


def test_resolve_db_path_portable_mode(monkeypatch, tmp_path):
    fake_exe = tmp_path / "NetScanX-Start-Linux"
    monkeypatch.delenv("NETSCANX_DB_PATH", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", "/tmp/fake", raising=False)
    monkeypatch.setattr(sys, "executable", str(fake_exe))

    resolved = paths.resolve_db_path()

    assert resolved == tmp_path / "NetScanX-Data" / "netscanx.db"
    assert resolved.parent.is_dir()


def test_resolve_db_path_installed_mode_uses_platformdirs(monkeypatch, tmp_path):
    monkeypatch.delenv("NETSCANX_DB_PATH", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)
    monkeypatch.setattr(
        "platformdirs.user_data_dir", lambda name, appauthor=False: str(tmp_path / "appdata")
    )

    resolved = paths.resolve_db_path()

    assert resolved == tmp_path / "appdata" / "netscanx.db"


@pytest.fixture(autouse=True)
def _cleanup_sys_frozen_attrs():
    had_frozen = hasattr(sys, "frozen")
    had_meipass = hasattr(sys, "_MEIPASS")
    yield
    if not had_frozen and hasattr(sys, "frozen"):
        delattr(sys, "frozen")
    if not had_meipass and hasattr(sys, "_MEIPASS"):
        delattr(sys, "_MEIPASS")
