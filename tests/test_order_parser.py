"""
Tests for utility_modules.orderParser: single-field extraction from a
product string (get_size_and_prefix, parse_order_item_data).
"""

from utility_modules import orderParser


class _FakeItem:
    size = None
    prefix = None


# ----------------------------------------
# get_size_and_prefix
# ----------------------------------------

def test_get_size_and_prefix_with_no_size_pattern_does_not_raise():
    item = _FakeItem()
    # previously: AttributeError from calling size_match.groups() on None
    result = orderParser.get_size_and_prefix(item, "Rose Blush BELLA JANES Shoes Baby and Toddler")
    assert result == "Rose Blush BELLA JANES Shoes Baby and Toddler"
    assert item.size is None
    assert item.prefix is None


def test_get_size_and_prefix_with_size_pattern_still_works():
    item = _FakeItem()
    result = orderParser.get_size_and_prefix(item, "Some Product - 10")
    assert result == "Some Product"
    assert item.size == "10"


def test_get_size_and_prefix_with_wm_prefix():
    item = _FakeItem()
    result = orderParser.get_size_and_prefix(item, "Some Product - W 8")
    assert item.size == "8"
    assert item.prefix.lower() == "w"


# ----------------------------------------
# parse_order_item_data
# ----------------------------------------

def test_parse_order_item_data_is_idempotent(workspace):
    """
    parse_order_item_data() always recomputes from
    item.original_order_string rather than mutating it, so calling it
    twice on the same object must produce the same result -- this is what
    makes the (now-fixed) double-parse in orderItem.parse_order_item safe
    even though it was wasted work.
    """

    from utility_modules.models import OrderItem

    item = OrderItem(
        time_stamp="2026-01-01 10:00:00",
        original_order_string="Rose Blush BELLA JANES Shoes Baby and Toddler - 6 (18m)5.5",
    )

    first = orderParser.parse_order_item_data(item)
    first_snapshot = (first.size, first.prefix, first.category, first.product_name, first.display_text, tuple(first.colors))

    second = orderParser.parse_order_item_data(item)
    second_snapshot = (second.size, second.prefix, second.category, second.product_name, second.display_text, tuple(second.colors))

    assert first_snapshot == second_snapshot
