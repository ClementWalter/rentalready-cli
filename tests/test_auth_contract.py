"""Credential broker contract tests use synthetic sessions without provider access."""
import importlib.machinery
import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
from click.testing import CliRunner

@pytest.fixture
def app(monkeypatch, tmp_path):
    path = Path(__file__).resolve().parents[1] / "bin/rr"
    loader = importlib.machinery.SourceFileLoader("auth_contract_rentalready", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    monkeypatch.setattr(module, "CONFIG_PATH", tmp_path / "config.json")
    if hasattr(module, "CONFIG_DIR"):
        monkeypatch.setattr(module, "CONFIG_DIR", tmp_path)
    if hasattr(module, "SESSION_BASE"):
        monkeypatch.setattr(module, "SESSION_BASE", tmp_path / "session")
    return module

def test_load_prefers_broker(app, monkeypatch):
    monkeypatch.setattr(app, "_auth_broker", lambda *args: {"api_id": 1, "api_hash": "vault"})
    assert app.load_config() == {"api_id": 1, "api_hash": "vault"}

def test_load_legacy_when_broker_unavailable(app, monkeypatch):
    monkeypatch.setattr(app, "_auth_broker", lambda *args: None)
    app.CONFIG_PATH.write_text('{"api_id": 2, "api_hash": "local"}')
    assert app.load_config() == {"api_id": 2, "api_hash": "local"}

@pytest.mark.parametrize("code", [0, 3])
def test_save_body_uses_stdin(app, monkeypatch, code):
    calls = []
    def run(argv, **kwargs):
        calls.append((argv, kwargs.get("input")))
        return SimpleNamespace(returncode=code, stdout='{"pending": false}')
    monkeypatch.setattr(subprocess, "run", run)
    app._auth_broker("save", {"password": "synthetic-secret"})
    assert calls == [(["claudine-secret", "auth", "save", "rentalready"], '{"password": "synthetic-secret"}')]

def test_status_never_emits_credentials(app, monkeypatch):
    monkeypatch.setattr(app, "_auth_broker", lambda *args: None)
    app.CONFIG_PATH.write_text('{"password": "synthetic-secret"}')
    result = CliRunner().invoke(app.cli, ["auth-status", "--json"])
    assert "synthetic-secret" not in result.output

def test_sync_pending_is_retryable(app, monkeypatch):
    monkeypatch.setattr(app, "_auth_broker", lambda *args: {"configured": True, "pending": True})
    assert CliRunner().invoke(app.cli, ["auth-sync"]).exit_code == 3
