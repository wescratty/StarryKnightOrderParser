"""
Tests for utility_modules.models.Batch, in particular
get_try_big_runner_size() / get_addon_categorized(), which infer big
runner (spare sole) sizes from the shoes in the same order.
"""

from utility_modules import helper
from utility_modules.models import Addon, OrderItem, Batch


def make_order_item(order_num, size):
    return OrderItem(
        time_stamp="2026-01-01 10:00:00",
        original_order_string=f"Some Shoe - {size}",
        order_num=order_num,
        size=size,
    )


def make_big_runner(order_num, color):
    return Addon(
        time_stamp="2026-01-01 10:00:00",
        original_order_string=f"{color} Big Runner",
        order_num=order_num,
        add_type=helper.AddonType.SOLE,
        color=color,
    )


def test_order_item_get_display_empty_string_does_not_fall_back_to_raw_text():
    """
    Regression test: display_text="" (extract_display_text() legitimately
    filtered everything away) used to be treated the same as
    display_text=None (never computed) by a truthy check, so get_display()
    incorrectly fell all the way back to the fully unfiltered
    product_name/original_order_string instead of showing blank.
    """

    item = OrderItem(
        time_stamp="2026-01-01 10:00:00",
        original_order_string="Some Raw Unfiltered Product Name - 3",
        product_name="Some Raw Unfiltered Product Name",
        display_text="",
    )

    assert item.get_display() == ""


def test_order_item_get_display_none_still_falls_back_to_product_name():
    item = OrderItem(
        time_stamp="2026-01-01 10:00:00",
        original_order_string="Some Raw Unfiltered Product Name - 3",
        product_name="Some Raw Unfiltered Product Name",
        display_text=None,
    )

    assert item.get_display() == "Some Raw Unfiltered Product Name"


def test_addon_get_display_empty_string_does_not_fall_back_to_raw_text():
    add = Addon(
        time_stamp="2026-01-01 10:00:00",
        original_order_string="Big Sky Mountains Leather PURSE Toddler & Kids",
        icon="👜",
        color="Big Sky Mountains",
        display_text="",
    )

    assert add.get_display() == "👜(Big Sky Mountains)"


def test_big_runner_size_inferred_when_counts_match():
    batch = Batch()
    batch.add_order(make_order_item("1001", "8"))
    batch.add_add_on(make_big_runner("1001", "Tan"))
    batch.__post_init__()

    events = batch.get_try_big_runner_size()

    runner = batch.get_order_addon_items("1001")[0]
    assert runner.size == "8"
    assert events == []


def test_big_runner_size_ambiguous_when_counts_do_not_match():
    # two big runners but only one pair of shoes in the order -- can't
    # confidently say which runner matches which pair
    batch = Batch()
    batch.add_order(make_order_item("1002", "8"))
    batch.add_add_on(make_big_runner("1002", "Tan"))
    batch.add_add_on(make_big_runner("1002", "Black"))
    batch.__post_init__()

    events = batch.get_try_big_runner_size()

    assert len(events) == 1
    assert events[0].order_num == "1002"
    assert "big runner" in events[0].message.lower()


def test_get_addon_categorized_groups_big_runners_by_color_and_returns_events():
    batch = Batch()
    batch.add_order(make_order_item("1003", "9"))
    batch.add_add_on(make_big_runner("1003", "Tan"))
    batch.__post_init__()

    addon_rows, events = batch.get_addon_categorized()

    assert events == []
    assert any("Tan" in key for key in addon_rows.keys())
