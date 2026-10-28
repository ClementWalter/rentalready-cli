#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "click==8.3.3",
#     "requests==2.34.2",
#     "beautifulsoup4==4.15.0",
#     "lxml==6.1.3",
#     "pycryptodome==4.2.0",
#     "pytest==9.1.1",
# ]
#
# [tool.uv]
# exclude-newer = "2026-10-27T00:00:00Z"
# ///
"""Terminal-free use from Claude Desktop: browser session discovery, renewal of
an expired stored session, and the not-logged-in error. No network, no keychain."""

import importlib.util
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import click
import pytest
from Crypto.Cipher import AES

_SPEC = importlib.util.spec_from_loader(
    "rr", importlib.machinery.SourceFileLoader("rr", str(Path(__file__).parent.parent / "rentalready_cli.py"))
)
rr = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(rr)

KEY = b"0123456789abcdef"
LOGIN_URL = rr.BASE + "/account/login/?next=/authentification/host_index/"
PAGE_URL = rr.BASE + "/authentification/host_index/"


def encrypt(value: str) -> bytes:
    """Encrypt like Chromium on macOS: `v10` + AES-CBC, PKCS7, IV of spaces."""
    data = value.encode()
    pad = 16 - len(data) % 16
    return b"v10" + AES.new(KEY, AES.MODE_CBC, iv=b" " * 16).encrypt(data + bytes([pad]) * pad)


def cookie_store(path: Path, rows: list[tuple[str, str, bytes]]) -> Path:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE cookies (host_key TEXT, name TEXT, encrypted_value BLOB)")
    con.executemany("INSERT INTO cookies VALUES (?, ?, ?)", rows)
    con.commit()
    con.close()
    return path


@pytest.fixture
def keychain(monkeypatch):
    """Record keychain lookups and answer each with KEY."""
    asked = []
    monkeypatch.setattr(rr, "_keychain_key", lambda service: asked.append(service) or KEY)
    return asked


def test_iter_sessionids_reads_the_browser_cookie(monkeypatch, tmp_path, keychain):
    store = cookie_store(tmp_path / "Cookies", [("pms.rentalready.io", "sessionid", encrypt("sid-1"))])
    monkeypatch.setattr(rr, "COOKIE_SOURCES", [("arc", str(store), "Arc Safe Storage")])
    assert list(rr.iter_sessionids()) == [("arc", "sid-1")]


def test_iter_sessionids_skips_the_keychain_when_logged_out(monkeypatch, tmp_path, keychain):
    store = cookie_store(tmp_path / "Cookies", [("pms.rentalready.io", "csrftoken", encrypt("x"))])
    monkeypatch.setattr(rr, "COOKIE_SOURCES", [("chrome", str(store), "Chrome Safe Storage")])
    list(rr.iter_sessionids())
    assert keychain == []


class StubSession:
    """A requests.Session whose GETs land on the queued URLs in turn."""

    def __init__(self, urls):
        self.urls = list(urls)
        self.cookies = SimpleNamespace(set=lambda name, value, domain: setattr(self, "sessionid", value))

    def get(self, url, **kwargs):
        return SimpleNamespace(url=self.urls.pop(0), text="")


def client_landing_on(urls, renew):
    client = rr.RentalReady("stale", renew=renew)
    client.s = StubSession(urls)
    return client


def test_expired_session_retries_with_the_browser_session():
    client = client_landing_on([LOGIN_URL, PAGE_URL], renew=lambda: "fresh")
    assert client.get("/authentification/host_index/").url == PAGE_URL


def test_expired_session_switches_the_cookie():
    client = client_landing_on([LOGIN_URL, PAGE_URL], renew=lambda: "fresh")
    client.get("/authentification/host_index/")
    assert client.s.sessionid == "fresh"


def test_expired_session_renews_only_once():
    client = client_landing_on([LOGIN_URL, LOGIN_URL], renew=lambda: "also-expired")
    with pytest.raises(click.ClickException):
        client.get("/authentification/host_index/")


def test_expired_session_without_browser_names_the_keychain_prompt():
    client = client_landing_on([LOGIN_URL], renew=lambda: None)
    with pytest.raises(click.ClickException) as exc:
        client.get("/authentification/host_index/")
    assert "Always Allow" in exc.value.message


@pytest.fixture
def no_env(monkeypatch):
    monkeypatch.delenv("RENTALREADY_SESSIONID", raising=False)
    monkeypatch.setattr(rr, "save_config", lambda cfg: None)


def test_stored_session_renews_from_another_browser_session(no_env, monkeypatch):
    monkeypatch.setattr(rr, "load_config", lambda: {"sessionid": "stored"})
    asked = []
    monkeypatch.setattr(rr, "browser_session", lambda exclude=None: asked.append(exclude))
    rr.get_client().renew()
    assert asked == ["stored"]


def test_browser_session_skips_the_excluded_session(no_env, monkeypatch):
    monkeypatch.setattr(rr, "load_config", lambda: {})
    monkeypatch.setattr(rr, "iter_sessionids", lambda: iter([("chrome", "stored"), ("arc", "new")]))
    monkeypatch.setattr(rr.RentalReady, "is_valid", lambda self: True)
    assert rr.browser_session(exclude="stored") == "new"


def test_no_session_anywhere_names_the_portal(no_env, monkeypatch):
    monkeypatch.setattr(rr, "load_config", lambda: {})
    monkeypatch.setattr(rr, "iter_sessionids", lambda: iter([]))
    with pytest.raises(click.ClickException) as exc:
        rr.get_client()
    assert "https://pms.rentalready.io" in exc.value.message


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
