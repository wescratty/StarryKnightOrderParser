"""
Tests for config.get_debug_mode / config.set_debug_mode.

DEBUG used to be a hardcoded `DEBUG = True` constant in orderItem.py that
silently disabled the "skip already-processed orders" feature no matter
what the GUI's Last Processed Order Timestamp field said. It's now a
per-workspace config file (config/debug_mode.txt) so it can be toggled
without touching code.
"""

import config as app_config


def test_default_debug_mode_is_true_when_no_file_written_yet(workspace):
    # initialize_app() already wrote the default file; this exercises the
    # "no workspace at all" fallback path directly
    app_config.DEBUG_FILE = None
    assert app_config.get_debug_mode() is True


def test_get_debug_mode_reads_default_file_written_by_initialize_app(workspace):
    assert app_config.get_debug_mode() is True


def test_set_debug_mode_false_then_read_back(workspace):
    result = app_config.set_debug_mode(False)
    assert result["success"] is True
    assert app_config.get_debug_mode() is False


def test_set_debug_mode_true_then_read_back(workspace):
    app_config.set_debug_mode(False)
    app_config.set_debug_mode(True)
    assert app_config.get_debug_mode() is True


def test_get_debug_mode_ignores_comment_header(workspace):
    # ensure_text_file() writes a "# Auto-generated..." comment header on
    # first creation -- this used to break naive whole-file parsing
    raw = app_config.DEBUG_FILE.read_text(encoding="utf-8")
    assert raw.startswith("#")
    assert app_config.get_debug_mode() is True
