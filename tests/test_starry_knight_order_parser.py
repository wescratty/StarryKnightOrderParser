"""
Tests for StarryKnightOrderParser.OrderParser.load_csv -- specifically the
DEBUG-mode gating around archiving the source CSV.

Builds an OrderParser instance without going through __init__/main() (which
would need a real Tk window), wiring just what load_csv touches: a real
FileHelper (so CSV parsing behaves normally) and MagicMocks standing in for
the Tk widgets so display_label_to_user() has something to call into.
"""

import csv
from unittest.mock import MagicMock

import config
import StarryKnightOrderParser as skop
from utility_modules import fileHelper


def _make_app(csv_path):
    app = skop.OrderParser.__new__(skop.OrderParser)
    app.file = fileHelper.FileHelper()
    app.file.find_file = lambda: str(csv_path)
    app.tk = MagicMock()
    app.search_text = MagicMock()
    app.set_button_instance = MagicMock()
    app.window = MagicMock()
    app.scroll_area = MagicMock()
    app.user_label = None
    app.var_info_label = None
    app.message_notify = ['#00FF00', 'white', 'yellow', 'red', 'blue']
    return app


def _write_csv(path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["Lineitem name", "Created at", "Lineitem quantity", "Notes", "Name"],
        )
        writer.writeheader()
        writer.writerow({
            "Lineitem name": "Lotus Shoe - 10",
            "Created at": "2026-01-01 10:00:00",
            "Lineitem quantity": "1",
            "Notes": "",
            "Name": "#1001",
        })


def test_debug_mode_on_does_not_archive_the_csv(workspace):
    """
    Regression test: archive_csv_file() used to run unconditionally on
    every load, regardless of DEBUG mode, so a file kept getting moved out
    from under the owner every time she reloaded it while debugging.
    """

    csv_path = workspace / "orders.csv"
    _write_csv(csv_path)

    config.set_debug_mode(True)
    app = _make_app(csv_path)
    app.load_csv(None)

    assert csv_path.exists()


def test_debug_mode_off_archives_the_csv_and_advances_timestamp(workspace):
    csv_path = workspace / "orders.csv"
    _write_csv(csv_path)

    config.set_debug_mode(False)
    app = _make_app(csv_path)
    app.load_csv(None)

    assert not csv_path.exists()
    assert config.get_last_processed_timestamp_string() == "2026-01-01 10:00:00"
