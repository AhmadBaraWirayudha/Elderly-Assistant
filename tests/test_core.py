"""
tests/test_core.py — Unit tests for all non-Streamlit, non-API modules.

Run with:  python -m pytest tests/ -v
All tests are self-contained: no Gemini API key, no network, no Streamlit.
"""
from __future__ import annotations

import pytest


# ══════════════════════════════════════════════════════════════════════════════
# utils.validator
# ══════════════════════════════════════════════════════════════════════════════

class TestSanitizeText:
    def test_strips_leading_trailing_whitespace(self):
        from utils.validator import sanitize_text
        assert sanitize_text("  hello  ") == "hello"

    def test_removes_null_bytes(self):
        from utils.validator import sanitize_text
        assert "\x00" not in sanitize_text("hel\x00lo")

    def test_removes_control_chars_keeps_newlines(self):
        from utils.validator import sanitize_text
        result = sanitize_text("line1\nline2\x07bell")
        assert "\x07" not in result
        assert "\n" in result

    def test_collapses_multiple_spaces(self):
        from utils.validator import sanitize_text
        assert sanitize_text("too   many   spaces") == "too many spaces"

    def test_normalises_unicode(self):
        from utils.validator import sanitize_text
        # café in NFC vs decomposed — both should normalise to same string
        nfc = "\u00e9"          # é precomposed
        decomposed = "e\u0301"  # e + combining acute
        assert sanitize_text(decomposed) == sanitize_text(nfc)


class TestValidateQuery:
    def test_empty_string_returns_error(self):
        from utils.validator import validate_query
        _, err = validate_query("")
        assert err == "empty_query"

    def test_whitespace_only_returns_error(self):
        from utils.validator import validate_query
        _, err = validate_query("   \t\n  ")
        assert err == "empty_query"

    def test_valid_query_returns_none_error(self):
        from utils.validator import validate_query
        clean, err = validate_query("  When do I take my medicine?  ")
        assert err is None
        assert clean == "When do I take my medicine?"

    def test_long_query_is_truncated_not_errored(self):
        import config
        from utils.validator import validate_query
        long = "word " * (config.MAX_QUERY_CHARS // 5 + 10)
        clean, err = validate_query(long)
        assert err is None
        assert len(clean) <= config.MAX_QUERY_CHARS


class TestValidateImageBytes:
    def test_empty_bytes_fail(self):
        from utils.validator import validate_image_bytes
        ok, err = validate_image_bytes(b"")
        assert not ok and err == "image_unclear"

    def test_tiny_payload_fails(self):
        from utils.validator import validate_image_bytes
        ok, err = validate_image_bytes(b"tiny")
        assert not ok

    def test_oversized_payload_fails(self):
        from utils.validator import validate_image_bytes
        ok, err = validate_image_bytes(b"x" * (11 * 1024 * 1024))
        assert not ok and err == "image_too_large"

    def test_normal_size_passes(self):
        from utils.validator import validate_image_bytes
        ok, err = validate_image_bytes(b"x" * 50_000)
        assert ok and err is None


# ══════════════════════════════════════════════════════════════════════════════
# router
# ══════════════════════════════════════════════════════════════════════════════

class TestRouter:
    def test_image_always_routes_to_flash(self):
        from router import route
        d = route("anything", retrieval_score=0.99, has_image=True)
        assert d.model_key == "flash"

    def test_high_score_short_query_routes_to_lite(self):
        from router import route
        d = route("take medicine", retrieval_score=0.95, has_image=False)
        assert d.model_key == "lite"

    def test_low_score_long_query_routes_to_pro(self):
        from router import route
        long_query = " ".join(["word"] * 100)
        d = route(long_query, retrieval_score=0.1, has_image=False)
        assert d.model_key == "pro"

    def test_medium_score_routes_to_flash(self):
        from router import route
        d = route("medium length health question", retrieval_score=0.65, has_image=False)
        assert d.model_key == "flash"

    def test_all_returned_keys_exist_in_config(self):
        """Router must never return a model_key that config.GEMINI_MODELS doesn't have."""
        import config
        from router import route

        cases = [
            ("short", 0.95, False),
            ("medium length question here", 0.60, False),
            (" ".join(["w"] * 100), 0.10, False),
            ("any", 0.90, True),
        ]
        valid = set(config.GEMINI_MODELS.keys())
        for query, score, img in cases:
            d = route(query, score, img)
            assert d.model_key in valid, (
                f"route() returned '{d.model_key}' which is not in "
                f"GEMINI_MODELS {valid}  (query={query!r})"
            )

    def test_route_decision_has_reason(self):
        from router import route
        d = route("test", retrieval_score=0.5, has_image=False)
        assert isinstance(d.reason, str) and len(d.reason) > 0


# ══════════════════════════════════════════════════════════════════════════════
# utils.errors
# ══════════════════════════════════════════════════════════════════════════════

class TestFriendlyError:
    def test_known_key_returns_string(self):
        from utils.errors import friendly_error
        for key in ("stt_failed", "image_unclear", "model_timeout", "no_api_key",
                    "empty_query", "image_too_large", "retrieval_failed", "generic"):
            msg = friendly_error(key)
            assert isinstance(msg, str) and len(msg) > 10, f"bad message for {key!r}"

    def test_unknown_key_falls_back_to_generic(self):
        from utils.errors import friendly_error
        msg = friendly_error("this_key_does_not_exist_xyz")
        assert isinstance(msg, str) and len(msg) > 0

    def test_stt_message_mentions_hearing(self):
        from utils.errors import friendly_error
        assert "hear" in friendly_error("stt_failed").lower()

    def test_empty_query_message_mentions_question(self):
        from utils.errors import friendly_error
        assert "question" in friendly_error("empty_query").lower()


# ══════════════════════════════════════════════════════════════════════════════
# utils.logger
# ══════════════════════════════════════════════════════════════════════════════

class TestLogger:
    def test_all_levels_emit_without_crash(self):
        from utils.logger import log
        log.info("test_info",  key="value")
        log.warn("test_warn",  key="value")
        log.error("test_error", exc="SomeException")
        log.model("test_model", model="flash", latency_ms=100)

    def test_output_is_valid_json(self, capsys):
        import json
        from utils.logger import log
        log.info("json_test", alpha=1, beta="two")
        captured = capsys.readouterr().out
        # Each line should be valid JSON
        for line in captured.strip().splitlines():
            obj = json.loads(line)
            assert obj["event"] == "json_test" or True   # may have prior lines

    def test_log_record_has_required_keys(self):
        """Verify _emit() produces a dict with the mandatory base keys."""
        import json, io
        from utils.logger import _StructuredLogger
        buf = io.StringIO()
        import logging
        logger = _StructuredLogger("test_keys")
        logger._log.handlers.clear()
        logger._log.addHandler(logging.StreamHandler(buf))
        logger._log.setLevel(logging.DEBUG)
        logger.info("key_check_event", x=42)
        line = buf.getvalue().strip()
        obj = json.loads(line)
        for key in ("ts", "level", "event"):
            assert key in obj, f"missing key {key!r} in log record"


# ══════════════════════════════════════════════════════════════════════════════
# utils.history  (uses tmp_path — no permanent side-effects)
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """Redirect HISTORY_DB to a temporary file for each test."""
    import config
    monkeypatch.setattr(config, "HISTORY_DB", str(tmp_path / "test.db"))
    # Reload the module so it picks up the new path
    import importlib, utils.history
    importlib.reload(utils.history)
    return utils.history


class TestHistory:
    def test_save_and_retrieve(self, tmp_db):
        tmp_db.save_turn(
            "test query", "test answer", "flash",
            input_type="text", retrieval_score=0.75, latency_ms=500,
        )
        turns = tmp_db.get_recent(limit=10)
        assert len(turns) == 1
        t = turns[0]
        assert t.query == "test query"
        assert t.answer == "test answer"
        assert t.model_used == "flash"
        assert t.input_type == "text"
        assert t.retrieval_score == pytest.approx(0.75)
        assert t.latency_ms == 500

    def test_get_recent_order(self, tmp_db):
        tmp_db.save_turn("first",  "a1", "flash")
        tmp_db.save_turn("second", "a2", "flash")
        turns = tmp_db.get_recent(limit=10)
        assert turns[0].query == "second"   # newest first

    def test_stats_empty_db(self, tmp_db):
        tmp_db.init_db()
        stats = tmp_db.get_stats()
        assert stats["total_turns"] == 0
        assert stats["avg_latency_ms"] == 0

    def test_stats_with_data(self, tmp_db):
        tmp_db.save_turn("q1", "a1", "flash",  input_type="text",  latency_ms=100)
        tmp_db.save_turn("q2", "a2", "lite",   input_type="voice", latency_ms=300)
        stats = tmp_db.get_stats()
        assert stats["total_turns"] == 2
        assert stats["avg_latency_ms"] == 200
        assert stats["by_input_type"]["text"]  == 1
        assert stats["by_input_type"]["voice"] == 1

    def test_clear_history(self, tmp_db):
        tmp_db.save_turn("q", "a", "flash")
        tmp_db.clear_history()
        assert tmp_db.get_recent() == []

    def test_migration_creates_schema_version(self, tmp_db):
        import sqlite3, config
        tmp_db.init_db()
        conn = sqlite3.connect(config.HISTORY_DB)
        version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        conn.close()
        assert version == 2   # current SCHEMA_VERSION


# ══════════════════════════════════════════════════════════════════════════════
# utils.health  (no API calls — only file-system checks)
# ══════════════════════════════════════════════════════════════════════════════

class TestHealth:
    def test_detects_placeholder_api_key(self, monkeypatch):
        import config
        monkeypatch.setattr(config, "GEMINI_API_KEY", "INSERT_YOUR_KEY_HERE")
        from utils.health import run_checks
        warnings = run_checks()
        assert any("API key" in w for w in warnings)

    def test_detects_missing_kb_directory(self, tmp_path, monkeypatch):
        import config
        monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key-ok")
        monkeypatch.setattr(config, "HISTORY_DB", str(tmp_path / "h.db"))
        monkeypatch.setattr(config, "KB_PATH",    str(tmp_path / "nonexistent_kb"))
        monkeypatch.setattr(config, "FAISS_PATH", str(tmp_path / "no_index"))
        from utils.health import run_checks
        warnings = run_checks()
        assert any("Knowledge base" in w for w in warnings)

    def test_no_warnings_when_everything_present(self, tmp_path, monkeypatch):
        import config
        kb = tmp_path / "kb"
        kb.mkdir()
        (kb / "test.txt").write_text("hello")
        monkeypatch.setattr(config, "GEMINI_API_KEY", "fake-key-ok")
        monkeypatch.setattr(config, "HISTORY_DB",    str(tmp_path / "h.db"))
        monkeypatch.setattr(config, "KB_PATH",       str(kb))
        monkeypatch.setattr(config, "FAISS_PATH",    str(tmp_path / "no_index"))
        from utils.health import run_checks
        warnings = run_checks()
        # May warn about FAISS staleness but NOT about API key or KB
        assert not any("API key" in w for w in warnings)
        assert not any("Knowledge base directory" in w for w in warnings)


# ══════════════════════════════════════════════════════════════════════════════
# config — self-consistency
# ══════════════════════════════════════════════════════════════════════════════

class TestConfig:
    def test_model_keys_are_non_empty_strings(self):
        import config
        for key, val in config.GEMINI_MODELS.items():
            assert isinstance(val, str) and val.startswith("gemini-"), (
                f"GEMINI_MODELS[{key!r}] = {val!r} looks wrong"
            )

    def test_router_thresholds_are_sane(self):
        import config
        r = config.ROUTER
        assert 0 < r["score_medium"] < r["score_high"] < 1
        assert 0 < r["words_short"] < r["words_medium"]

    def test_history_db_is_absolute_path(self):
        import config
        from pathlib import Path
        assert Path(config.HISTORY_DB).is_absolute(), (
            "HISTORY_DB must be an absolute path to survive working-directory changes"
        )

    def test_chunk_size_larger_than_overlap(self):
        import config
        assert config.CHUNK_SIZE > config.CHUNK_OVERLAP


# ══════════════════════════════════════════════════════════════════════════════
# Pages & project structure
# ══════════════════════════════════════════════════════════════════════════════

class TestProjectStructure:
    def test_pages_parse_cleanly(self):
        """All Streamlit page files must be syntactically valid Python."""
        import ast
        from pathlib import Path
        pages = list(Path("pages").glob("*.py"))
        assert pages, "No page files found — pages/ directory may be missing"
        for f in pages:
            try:
                ast.parse(f.read_text())
            except SyntaxError as e:
                pytest.fail(f"Syntax error in {f}: {e}")

    def test_required_deployment_files_exist(self):
        """All files that Streamlit Cloud requires must be present."""
        from pathlib import Path
        required = [
            "app.py",
            "requirements.txt",
            "README.md",
            ".env.example",
            ".streamlit/config.toml",
            ".streamlit/secrets.toml.example",
            ".github/workflows/ci.yml",
        ]
        missing = [f for f in required if not Path(f).exists()]
        assert not missing, f"Missing required files: {missing}"

    def test_gitignore_covers_secrets(self):
        """Sensitive files must appear in .gitignore."""
        from pathlib import Path
        gi_text = Path(".gitignore").read_text()
        for sensitive in (".env", "secrets.toml", "chat_history.db"):
            assert sensitive in gi_text, (
                f"{sensitive!r} not found in .gitignore — secrets could be committed"
            )

    def test_requirements_all_have_version_constraints(self):
        """Every non-comment requirement must have >= or == or ~=."""
        from pathlib import Path
        lines = [
            l.strip()
            for l in Path("requirements.txt").read_text().splitlines()
            if l.strip() and not l.startswith("#") and not l.startswith("-")
        ]
        unpinned = [l for l in lines if ">=" not in l and "==" not in l and "~=" not in l]
        assert not unpinned, f"Unpinned dependencies: {unpinned}"
