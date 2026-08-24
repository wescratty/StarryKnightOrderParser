"""
Tests for utility_modules.makeHtml.sort_size (the sort key that decides
row order within each collection's table on the report) and the
Big Kids/Men's/Women's group-divider rows built on top of it.
"""

from utility_modules import helper
from utility_modules.makeHtml import sort_size, get_size_tier, build_main_table_html, Table, _Divider
from utility_modules.models import OrderItem, Addon, Batch


def _order(size, prefix):
    item = OrderItem(time_stamp="", original_order_string="")
    item.size = size
    item.prefix = prefix
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


def test_single_tier_table_gets_no_dividers():
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
