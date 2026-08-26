"""
Tests for utility_modules.makeHtml.sort_size (the sort key that decides
row order within each collection's table on the report) and the
Big Kids/Men's/Women's group-divider rows built on top of it.
"""

from utility_modules import helper
from utility_modules.makeHtml import sort_size, get_size_tier, build_main_table_html, get_bottoms_report, Table, _Divider, Report
from utility_modules.models import OrderItem, Addon, Batch


def _order(size, prefix, quantity=1):
    item = OrderItem(time_stamp="", original_order_string="")
    item.size = size
    item.prefix = prefix
    item.quantity = quantity
    return item


def test_toddler_sizes_sort_before_kids_men_and_women():
    """
    Regression test for the "scattered adult sizes" complaint: Big Kids/
    Men's/Women's OrderItems must sort into their own tier *after* every
    plain numeric toddler size, not interleaved by raw number. Previously
    sort_size() only ever looked at .size (a bare number for OrderItems --
    the prefix lives in a separate field), so it never actually grouped
    them; it just happened to also mislabel "kids"-prefixed sizes as the
    same tier as toddler sizes even when it did see a prefix.
    """

    items = [
        _order("00", None),
        _order("2", None),
        _order("7.5", "W"),   # would sort between "6" and "8" by raw number
        _order("6", None),
        _order("10.5", "M"),
        _order("2.5", "Kids"),  # would sort right after "2" by raw number
        _order("8", None),
    ]

    ordered = sorted(items, key=sort_size)
    ordered_sizes = [(o.size, o.prefix) for o in ordered]

    assert ordered_sizes == [
        ("00", None),
        ("2", None),
        ("6", None),
        ("8", None),
        ("2.5", "Kids"),
        ("10.5", "M"),
        ("7.5", "W"),
    ]


def test_missing_size_sorts_last():
    items = [_order("4", None), _order(None, None)]
    ordered = sorted(items, key=sort_size)
    assert ordered[-1].size is None


def test_addon_wool_size_with_embedded_kids_prefix_still_groups_correctly():
    # Addon.prefix is never populated -- the prefix word lives inside the
    # size string itself (e.g. "Kids 2.5" from classify_addon's WOOL branch)
    kids_addon = Addon(time_stamp="", original_order_string="", size="Kids 2.5")
    toddler_addon = Addon(time_stamp="", original_order_string="", size="5")
    womens_addon = Addon(time_stamp="", original_order_string="", size="Womens 9")

    ordered = sorted([kids_addon, womens_addon, toddler_addon], key=sort_size)
    assert [a.size for a in ordered] == ["5", "Kids 2.5", "Womens 9"]


# ----------------------------------------
# get_size_tier / group-divider rows
# ----------------------------------------

def test_get_size_tier_labels():
    assert get_size_tier(_order("6", None))[1] == "Toddler"
    assert get_size_tier(_order("2.5", "Kids"))[1] == "Big Kids"
    assert get_size_tier(_order("10.5", "M"))[1] == "Men's"
    assert get_size_tier(_order("7", "W"))[1] == "Women's"
    assert get_size_tier(_order(None, None))[1] is None


def _category_batch(items):
    batch = Batch()
    for item in items:
        batch.add_order(item)
    batch.__post_init__()
    return batch


def test_mixed_tier_table_gets_divider_rows():
    """
    A category with both toddler and adult/Big Kids sizes must get a
    group-divider row inserted right before each new tier starts, so the
    size jump is obvious at a glance -- per the owner's follow-up request
    after the first sort-order fix ("we have kids, mens and then womens in
    the same table... add some kind of a group... so at a glance its easy
    to tell").
    """

    items = [_order("2", None), _order("6", None), _order("2.5", "Kids"), _order("10.5", "M"), _order("7", "W")]
    for item in items:
        item.category = "Loafer"
        item.order_num = "1"

    batch = _category_batch(items)
    report = build_main_table_html(batch)

    table = report.tables[0]
    dividers = [row.label for row in table.rows if isinstance(row, _Divider)]
    assert dividers == ["Toddler", "Big Kids", "Men's", "Women's"]


def test_purse_addon_does_not_piggyback_onto_unrelated_shoe_in_same_order():
    """
    Regression test for a real production report: a Critters shoe and a
    Purse add-on sharing an order number (a common Shopify multi-item
    order) used to get combined on the shoe's row, since every addon on
    the same order number was piggybacked regardless of type -- correct
    for WOOL/SOLE (things that literally attach to a specific pair) but
    wrong for a standalone accessory like PURSE, which has its own report
    table and shouldn't be stamped onto an unrelated shoe purchase.
    """

    shoe = OrderItem(
        time_stamp="2026-01-01 10:00:00",
        original_order_string="Papaya Fox// Cute Critters Leather Shoes",
        order_num="59243",
        category="Critters",
        size="10",
        display_text="papaya Fox",
    )
    purse = Addon(
        time_stamp="2026-01-01 10:00:00",
        original_order_string="Big Sky Mountains Leather PURSE Toddler & Kids",
        order_num="59243",
        add_type=helper.AddonType.PURSE,
        icon="👜",
        color="Big Sky Mountains",
        display_text="",
    )

    batch = Batch()
    batch.add_order(shoe)
    batch.add_add_on(purse)
    batch.__post_init__()

    report = build_main_table_html(batch)
    table = report.tables[0]
    html = "".join(str(row) for row in table.rows)

    # the tooltip (hover-only) legitimately still lists every addon on the
    # order, including the purse -- only the always-visible <summary> row
    # text is what must not be stamped with the unrelated purse's info
    import re
    summaries = re.findall(r"<summary>(.*?)</summary>", html)

    assert any("papaya Fox" in s for s in summaries)
    assert not any("Big Sky Mountains" in s for s in summaries)


def test_wool_addon_still_piggybacks_onto_its_shoe():
    shoe = OrderItem(
        time_stamp="2026-01-01 10:00:00",
        original_order_string="Some Shoe",
        order_num="2001",
        category="Loafer",
        size="6",
        display_text="tan",
    )
    wool = Addon(
        time_stamp="2026-01-01 10:00:00",
        original_order_string="Natural Wool Insert - Small",
        order_num="2001",
        add_type=helper.AddonType.WOOL,
        icon="🐑",
    )

    batch = Batch()
    batch.add_order(shoe)
    batch.add_add_on(wool)
    batch.__post_init__()

    report = build_main_table_html(batch)
    table = report.tables[0]
    html = "".join(str(row) for row in table.rows)

    assert "🐑" in html


def test_single_tier_toddler_table_gets_no_dividers():
    # every item is a plain toddler size -- nothing to distinguish, so no
    # divider rows should be added at all
    items = [_order("2", None), _order("4", None), _order("6", None)]
    for item in items:
        item.category = "Loafer"
        item.order_num = "1"

    batch = _category_batch(items)
    report = build_main_table_html(batch)

    table = report.tables[0]
    dividers = [row for row in table.rows if isinstance(row, _Divider)]
    assert dividers == []


def test_big_kids_only_table_still_gets_its_divider():
    """
    Regression test: a table with ONLY Big Kids sizes (no toddler sizes
    mixed in) used to get zero divider rows at all, since the old rule
    only added one when a table mixed more than one tier. With nothing
    labeling the table, the owner mistook it for a toddler-sized table --
    the size numbers alone don't look any different. A Big Kids/Men's/
    Women's-only table must always get its one divider up front now.
    """

    items = [_order("2", "Kids"), _order("2.5", "Kids"), _order("3", "Kids")]
    for item in items:
        item.category = "BELLA"
        item.order_num = "1"

    batch = _category_batch(items)
    report = build_main_table_html(batch)

    table = report.tables[0]
    dividers = [row.label for row in table.rows if isinstance(row, _Divider)]
    assert dividers == ["Big Kids"]


def test_mens_only_table_still_gets_its_divider():
    items = [_order("9", "M"), _order("10", "M"), _order("10.5", "M")]
    for item in items:
        item.category = "Loafer"
        item.order_num = "1"

    batch = _category_batch(items)
    report = build_main_table_html(batch)

    table = report.tables[0]
    dividers = [row.label for row in table.rows if isinstance(row, _Divider)]
    assert dividers == ["Men's"]


def test_womens_only_table_still_gets_its_divider():
    items = [_order("7", "W"), _order("8", "W")]
    for item in items:
        item.category = "Loafer"
        item.order_num = "1"

    batch = _category_batch(items)
    report = build_main_table_html(batch)

    table = report.tables[0]
    dividers = [row.label for row in table.rows if isinstance(row, _Divider)]
    assert dividers == ["Women's"]


def test_no_size_at_all_does_not_get_a_forced_divider():
    # every item has an unparseable/missing size (tier 99) -- a single
    # uniform tier, same as the toddler-only case, must not get forced
    # into always showing a divider the way Big Kids/M/W do
    items = [_order(None, None), _order(None, None)]
    for item in items:
        item.category = "Loafer"
        item.order_num = "1"

    batch = _category_batch(items)
    report = build_main_table_html(batch)

    table = report.tables[0]
    dividers = [row.label for row in table.rows if isinstance(row, _Divider)]
    assert dividers == []


# ----------------------------------------
# get_bottoms_report
# ----------------------------------------

def test_bottoms_report_tallies_pairs_by_size_across_categories():
    """
    Bottom/sole leather is cut the same color no matter the shoe's own
    category or color, so the owner asked for one flat by-size tally
    across every category combined, with a Total row -- e.g. two
    different categories both selling size 3 shoes must add into the
    same "3" row rather than needing to be added up by hand across
    separate category tables.
    """

    orders = [
        _order("3", None, quantity=5),
        _order("3", None, quantity=4),   # different category/color, same size -- must combine
        _order("4", None, quantity=2),
    ]

    report = get_bottoms_report(orders)
    table = report.tables[0]

    assert table.rows[0] == ["3", 9]
    assert table.rows[1] == ["4", 2]
    assert table.rows[-1] == ["<b>Total</b>", "<b>11</b>"]


def test_bottoms_report_labels_adult_and_big_kids_sizes_distinctly():
    """
    A toddler size "3" and a Big Kids/Men's/Women's size that happens to
    share the same number must NOT be merged into one row -- bottoms are
    cut to different dimensions per tier even at the "same" size number.
    """

    orders = [
        _order("3", None, quantity=2),          # toddler
        _order("3", "Kids", quantity=1),        # Big Kids -- same number, different tier
        _order("10.5", "M", quantity=1),
        _order("9", "W", quantity=1),
    ]

    report = get_bottoms_report(orders)
    table = report.tables[0]
    labels = [row[0] for row in table.rows]

    assert "3" in labels
    assert "Big Kids 3" in labels
    assert "Men's 10.5" in labels
    assert "Women's 9" in labels
    # confirm the toddler and Big Kids "3" rows stayed separate, not merged
    assert table.rows[labels.index("3")][1] == 2
    assert table.rows[labels.index("Big Kids 3")][1] == 1


def test_bottoms_report_sorts_toddler_before_kids_men_women():
    orders = [
        _order("9", "W", quantity=1),
        _order("2", None, quantity=1),
        _order("10.5", "M", quantity=1),
        _order("2.5", "Kids", quantity=1),
    ]

    report = get_bottoms_report(orders)
    table = report.tables[0]
    labels = [row[0] for row in table.rows if row[0] != "<b>Total</b>"]

    assert labels == ["2", "Big Kids 2.5", "Men's 10.5", "Women's 9"]


def test_bottoms_report_groups_missing_size_as_unknown():
    orders = [
        _order("3", None, quantity=2),
        _order(None, None, quantity=1),
    ]

    report = get_bottoms_report(orders)
    table = report.tables[0]
    labels = [row[0] for row in table.rows]

    assert "Unknown" in labels
    assert table.rows[-1] == ["<b>Total</b>", "<b>3</b>"]


# ----------------------------------------
# Report.get_grid_of_tables / .make() -- table layout
# ----------------------------------------
#
# Regression tests for the "one-row table surrounded by a big band of
# blank space" complaint: a fixed row-by-row CSS grid stretches every
# table in a row to match the tallest one sharing that row, so a short
# table (e.g. a collection with a single order) leaves a lot of visible
# blank space next to a much taller one. These confirm the report now
# uses a CSS multi-column layout instead, where the next table simply
# flows in underneath a short one within the same column.

def _table(title, n_rows):
    t = Table(title=title, columns=["Size", "Description"])
    for i in range(n_rows):
        t.add([str(i), "x"])
    return t


def test_report_uses_column_layout_not_a_fixed_grid():
    report = Report()
    report.add(_table("Lotus", 1))
    report.add(_table("Designs", 8))

    html = report.make(max_tables=4)

    assert "column-count:4" in html
    assert "display:grid" not in html
    assert "grid-template-columns" not in html


def test_every_table_gets_its_own_break_avoiding_block():
    report = Report()
    report.add(_table("Lotus", 1))
    report.add(_table("Moccs", 2))
    report.add(_table("Designs", 8))

    html = report.make(max_tables=4)

    # one table-block wrapper per table, not grouped into fixed-size rows
    assert html.count('class="table-block"') == 3
    assert html.count("<h1>Lotus</h1>") == 1
    assert html.count("<h1>Moccs</h1>") == 1
    assert html.count("<h1>Designs</h1>") == 1


def test_column_count_reflects_max_tables_argument():
    report = Report()
    report.add(_table("Only One", 3))

    assert "column-count:2" in report.make(max_tables=2)
    assert "column-count:5" in report.make(max_tables=5)


def test_empty_report_renders_nothing():
    report = Report()
    assert report.make(max_tables=4) == ""
