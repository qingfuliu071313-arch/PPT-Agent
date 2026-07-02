"""Tests for image download cache hardening and per-run search dedup."""

from __future__ import annotations

import asyncio
import hashlib

import pytest

from ppt_agent.pipeline.image_sourcer import ImageSourcer
from ppt_agent.utils import image_search


def _cache_name(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12] + ".jpg"


@pytest.fixture
def image_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(image_search, "_IMAGE_DIR", tmp_path)
    return tmp_path


def test_cache_hit_requires_min_size(image_dir, monkeypatch):
    """A truncated cached file must be discarded, not returned."""
    url = "http://example.com/a.jpg"
    stale = image_dir / _cache_name(url)
    stale.write_bytes(b"x" * 10)

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return type("R", (), {"returncode": 1})()

    monkeypatch.setattr(image_search.subprocess, "run", fake_run)
    assert image_search.download_image(url) is None
    assert not stale.exists()
    assert calls, "should have attempted a re-download"


def test_cache_hit_returns_valid_file_without_curl(image_dir, monkeypatch):
    url = "http://example.com/b.jpg"
    cached = image_dir / _cache_name(url)
    cached.write_bytes(b"x" * 2000)

    def boom(*a, **k):
        raise AssertionError("curl must not run on a valid cache hit")

    monkeypatch.setattr(image_search.subprocess, "run", boom)
    assert image_search.download_image(url) == str(cached)


def test_download_writes_atomically(image_dir, monkeypatch):
    """Successful download lands under the final name with no .part left."""
    url = "http://example.com/c.jpg"

    def fake_run(cmd, **kwargs):
        out = cmd[cmd.index("-o") + 1]
        with open(out, "wb") as f:
            f.write(b"y" * 2000)
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(image_search.subprocess, "run", fake_run)
    path = image_search.download_image(url)
    assert path and path.endswith(_cache_name(url))
    assert not list(image_dir.glob("*.part"))


def test_failed_download_leaves_no_partial(image_dir, monkeypatch):
    url = "http://example.com/d.jpg"

    def fake_run(cmd, **kwargs):
        out = cmd[cmd.index("-o") + 1]
        with open(out, "wb") as f:
            f.write(b"z" * 10)  # too small — simulated truncation
        return type("R", (), {"returncode": 0})()

    monkeypatch.setattr(image_search.subprocess, "run", fake_run)
    assert image_search.download_image(url) is None
    assert not list(image_dir.iterdir())


def test_search_error_counter(monkeypatch):
    image_search.reset_search_stats()

    def broken_backend(query, count):
        raise ConnectionError("offline")

    monkeypatch.setattr(image_search, "_search_wikimedia", broken_backend)
    monkeypatch.setattr(image_search, "_search_openverse", broken_backend)
    assert image_search.search_image_urls("anything", 3) == []
    assert image_search.get_search_stats()["search_errors"] > 0


def test_search_cached_searches_once_and_rotates(monkeypatch):
    sourcer = ImageSourcer()
    calls = []

    def fake_search(query, count):
        calls.append(query)
        return ["u1", "u2", "u3"]

    monkeypatch.setattr(
        "ppt_agent.pipeline.image_sourcer.search_image_urls", fake_search
    )

    first = asyncio.run(sourcer._search_cached("cnn architecture"))
    second = asyncio.run(sourcer._search_cached("cnn architecture"))
    assert calls == ["cnn architecture"], "same query must be searched once"
    assert first == ["u1", "u2", "u3"]
    assert second == ["u2", "u3", "u1"], "repeat use should prefer a different image"
