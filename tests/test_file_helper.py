"""
Tests for utility_modules.fileHelper.FileHelper.parse_csv_to_dict.

Covers the crash bugs found in review:
- missing file -> used to raise FileNotFoundError
- empty file -> used to raise TypeError iterating reader.fieldnames (None)
- BOM'd file (re-saved from Excel) -> used to mangle the header row
- ragged rows -> used to KeyError
"""

from tests.conftest import FIXTURES_DIR
from utility_modules.fileHelper import FileHelper


def test_missing_file_returns_empty_dict_not_exception():
    result = FileHelper.parse_csv_to_dict(str(FIXTURES_DIR / "does_not_exist.csv"))
    assert result == {}


def test_empty_file_returns_empty_dict_not_exception():
    result = FileHelper.parse_csv_to_dict(str(FIXTURES_DIR / "empty.csv"))
    assert result == {}


def test_bom_file_parses_header_correctly():
    result = FileHelper.parse_csv_to_dict(str(FIXTURES_DIR / "bom.csv"))
    # a stray BOM used to get glued onto the first header name, e.g.
    # "﻿Name" instead of "Name", silently breaking every downstream
    # csv_tree["Name"] lookup
    assert "Name" in result
    assert result["Name"] == ["#1001"]


def test_ragged_row_does_not_raise_keyerror():
    result = FileHelper.parse_csv_to_dict(str(FIXTURES_DIR / "ragged_row.csv"))
    assert result["Name"] == ["#1001", "#1002"]
    # short row: DictReader pads missing trailing columns with None
    assert result["Lineitem name"][0] is None
    assert result["Notes"][0] is None
    assert result["Lineitem name"][1] == "Tan Big Runner"


def test_happy_path_parses_all_columns():
    result = FileHelper.parse_csv_to_dict(str(FIXTURES_DIR / "happy_path.csv"))
    assert set(result.keys()) == {"Name", "Created at", "Lineitem quantity", "Lineitem name", "Notes"}
    assert len(result["Name"]) == 3
