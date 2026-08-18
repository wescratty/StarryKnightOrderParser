"""
Tests for utility_modules.orderItem.parse_orders -- the CSV-import
pipeline's edge-case / crash handling. See test_order_parser.py for
get_size_and_prefix and other single-field extraction tests.
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


def test_order_item_is_parsed_exactly_once(workspace):
    """
    Regression test for the double-parse bug found in review: parse_order_item()
    used to call parse_order_item_data() a second time on an OrderItem that
    get_class() had already fully parsed. Confirms parse_order_item_data is
    now called exactly once per OrderItem row.

    Patches utility_modules.orderParser.parse_order_item_data directly
    (rather than pytest's monkeypatch fixture) since get_order_item() looks
    it up by module-global name at call time, so a plain attribute swap is
    enough -- and it keeps this test runnable without a pytest dependency.
    """

    from utility_modules import orderParser

    call_count = {"n": 0}
    original = orderParser.parse_order_item_data

    def counting_wrapper(item):
        call_count["n"] += 1
        return original(item)

    orderParser.parse_order_item_data = counting_wrapper
    try:
        oi.parse_orders(
            order_strings=["Lotus Shoe - 10"],
            timestamps=["2026-01-01 10:00:00"],
            quantities=["1"],
            notes=[None],
            order_nums=["#1001"],
        )
    finally:
        orderParser.parse_order_item_data = original

    assert call_count["n"] == 1
