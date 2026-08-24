"""
Tests for utility_modules.makeHtml.sort_size -- the sort key that decides
row order within each collection's table on the report.
"""

from utility_modules.makeHtml import sort_size
from utility_modules.models import OrderItem, Addon


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
