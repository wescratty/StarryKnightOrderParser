"""
Tests for utility_modules.orderItem: get_size_and_prefix and parse_orders
edge-case / crash handling.
"""

import csv

from tests.conftest import FIXTURES_DIR
from utility_modules import orderItem as oi


def load_csv_columns(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    cols = {name: [] for name in reader.fieldnames}
    for row in rows:
        for name in reader.fieldnames:
            cols[name].append(row.get(name))
    return cols


# ----------------------------------------
# get_size_and_prefix
# ----------------------------------------

class _FakeItem:
    size = None
    prefix = None


def test_get_size_and_prefix_with_no_size_pattern_does_not_raise():
    item = _FakeItem()
    # previously: AttributeError from calling size_match.groups() on None
    result = oi.get_size_and_prefix(item, "Rose Blush BELLA JANES Shoes Baby and Toddler")
    assert result == "Rose Blush BELLA JANES Shoes Baby and Toddler"
    assert item.size is None
    assert item.prefix is None


def test_get_size_and_prefix_with_size_pattern_still_works():
    item = _FakeItem()
    result = oi.get_size_and_prefix(item, "Some Product - 10")
    assert result == "Some Product"
    assert item.size == "10"


def test_get_size_and_prefix_with_wm_prefix():
    item = _FakeItem()
    result = oi.get_size_and_prefix(item, "Some Product - W 8")
    assert item.size == "8"
    assert item.prefix.lower() == "w"


# ----------------------------------------
# parse_orders: crash bugs
# ----------------------------------------

def test_non_numeric_quantity_does_not_crash_batch(workspace):
    cols = load_csv_columns(FIXTURES_DIR / "non_numeric_quantity.csv")

    batch, events = oi.parse_orders(
        order_strings=cols["Lineitem name"],
        timestamps=cols["Created at"],
        quantities=cols["Lineitem quantity"],
        notes=cols["Notes"],
        order_nums=cols["Name"],
    )

    # row 0 is a plain shoe order (non-numeric quantity "abc")
    # row 1 is "Tan Big Runner", which matches the Big Runner addon marker
    # and is classified as an Addon rather than an OrderItem (blank quantity)
    items = batch.get_all_order_items()
    addons = batch.get_all_addon_items()
    assert len(items) == 1
    assert len(addons) == 1
    assert items[0].quantity == 1
    assert addons[0].quantity == 1
    assert any("quantity" in e.message.lower() for e in events)


def test_blank_lineitem_name_is_skipped_not_phantom_item(workspace):
    cols = load_csv_columns(FIXTURES_DIR / "blank_lineitem_name.csv")

    batch, events = oi.parse_orders(
        order_strings=cols["Lineitem name"],
        timestamps=cols["Created at"],
        quantities=cols["Lineitem quantity"],
        notes=cols["Notes"],
        order_nums=cols["Name"],
    )

    # row 0 has a blank Lineitem name and must not become a phantom
    # OrderItem or Addon; row 1 ("Tan Big Runner") is a real Addon
    assert batch.get_all_order_items() == []
    addons = batch.get_all_addon_items()
    assert len(addons) == 1
    assert addons[0].original_order_string == "Tan Big Runner"
    assert any("blank" in e.message.lower() for e in events)


def test_ragged_row_none_values_do_not_crash_batch(workspace):
    cols = load_csv_columns(FIXTURES_DIR / "ragged_row.csv")

    # should not raise despite Lineitem name / Notes being None for row 0
    batch, events = oi.parse_orders(
        order_strings=cols["Lineitem name"],
        timestamps=cols["Created at"],
        quantities=cols["Lineitem quantity"],
        notes=cols["Notes"],
        order_nums=cols["Name"],
    )

    # row 0 is short (missing Lineitem name / Notes columns entirely,
    # DictReader fills them with None) and must be skipped, not crash;
    # row 1 ("Tan Big Runner") is a real Addon
    assert batch.get_all_order_items() == []
    addons = batch.get_all_addon_items()
    assert len(addons) == 1
    assert addons[0].original_order_string == "Tan Big Runner"


def test_one_bad_row_does_not_kill_the_whole_batch(workspace):
    # mix a guaranteed-bad row (None Lineitem name from a short row) with
    # good rows and confirm the good rows still come through
    order_strings = ["Lotus Shoe - 10", None, "Daisy Shoe - 8"]
    timestamps = ["2026-01-01 10:00:00"] * 3
    quantities = ["2", "1", "1"]
    notes = [None, None, None]
    order_nums = ["#1001", "#1002", "#1003"]

    batch, events = oi.parse_orders(order_strings, timestamps, quantities, notes, order_nums)

    items = batch.get_all_order_items()
    assert len(items) == 2
    assert {i.order_num for i in items} == {"1001", "1003"}


def test_missing_order_num_column_value_does_not_crash(workspace):
    # order_nums[i] is None (ragged row) -- used to crash on .startswith
    order_strings = ["Lotus Shoe - 10"]
    timestamps = ["2026-01-01 10:00:00"]
    quantities = ["1"]
    notes = [None]
    order_nums = [None]

    batch, events = oi.parse_orders(order_strings, timestamps, quantities, notes, order_nums)

    items = batch.get_all_order_items()
    assert len(items) == 1
    assert items[0].order_num is None


def test_happy_path_end_to_end(workspace):
    cols = load_csv_columns(FIXTURES_DIR / "happy_path.csv")

    batch, events = oi.parse_orders(
        order_strings=cols["Lineitem name"],
        timestamps=cols["Created at"],
        quantities=cols["Lineitem quantity"],
        notes=cols["Notes"],
        order_nums=cols["Name"],
    )

    assert len(batch.get_all_order_items()) == 1
    assert len(batch.get_all_addon_items()) == 2
    assert events == []
