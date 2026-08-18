"""
Tests for StarryKnightOrderParser.get_missing_required_columns, which
StarryKnightOrderParser.load_csv uses to turn a renamed/missing Shopify
export column into a readable GUI message instead of an uncaught KeyError.
"""

from utility_modules.fileHelper import FileHelper
from tests.conftest import FIXTURES_DIR
from StarryKnightOrderParser import get_missing_required_columns, REQUIRED_CSV_COLUMNS


def test_all_required_columns_present_reports_nothing_missing():
    csv_tree = FileHelper.parse_csv_to_dict(str(FIXTURES_DIR / "happy_path.csv"))
    assert get_missing_required_columns(csv_tree) == []


def test_missing_notes_column_is_reported():
    csv_tree = FileHelper.parse_csv_to_dict(str(FIXTURES_DIR / "missing_column.csv"))
    missing = get_missing_required_columns(csv_tree)
    assert missing == ["Notes"]


def test_empty_csv_tree_reports_all_columns_missing():
    assert get_missing_required_columns({}) == REQUIRED_CSV_COLUMNS
