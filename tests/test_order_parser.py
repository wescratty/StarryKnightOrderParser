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


def test_get_size_and_prefix_with_spelled_out_men():
    """
    Regression test: adult Men's listings sometimes spell out "Men" instead
    of abbreviating to "M" (e.g. "...Wool Insert included - Men 10.5 (foot
    measures...)"). Previously only a single "M" character was recognized,
    so "Men 10.5" failed to match the size pattern at all and the item came
    out with size=None, prefix=None -- and, as a side effect, got miscounted
    as a Toddler-bucket leather order instead of Adult.
    """
    item = _FakeItem()
    orderParser.get_size_and_prefix(item, "Men's LOAFERS - Men 10.5 (foot measures 11\")")
    assert item.size == "10.5"
    assert item.prefix == "M"


def test_get_size_and_prefix_with_spelled_out_women():
    item = _FakeItem()
    orderParser.get_size_and_prefix(item, "Women's BLOSSOMS - Women 9 (foot measures 10\")")
    assert item.size == "9"
    assert item.prefix == "W"


def test_get_size_and_prefix_with_womens_no_apostrophe():
    # seen verbatim in real CSV data: "...for Any size - Womens 9"
    item = _FakeItem()
    orderParser.get_size_and_prefix(item, "Some Product - Womens 9")
    assert item.size == "9"
    assert item.prefix == "W"


# ----------------------------------------
# parse_order_item_data
# ----------------------------------------

def test_daisy_print_on_mary_janes_keeps_daisy_drops_mary_and_designs(workspace):
    """
    Regression test for a real production report: "Daisy Mary Janes Shoes
    with Designs - 3 (9m)4.75\"" categorizes as "Mary" (first CATEGORY
    match), and the owner wants the *display* to read just "Daisy" -- the
    "Mary"/"Jane"/"Janes" words are redundant with the item's own category
    (already shown as that table's header), and "Shoes with Designs" is
    plain boilerplate. "Daisy" is the one piece of real information (the
    print name) and must survive even though it happens to share a name
    with the "Daisy" category elsewhere in CATEGORY.
    """

    from utility_modules.models import OrderItem

    item = OrderItem(
        time_stamp="2026-01-01 10:00:00",
        original_order_string='Daisy Mary Janes Shoes with Designs - 3   (9m)4.75"',
    )
    orderParser.parse_order_item_data(item)

    assert item.category == "Mary"
    assert item.display_text == "Daisy"


def test_big_kids_bella_display_drops_size_tier_words(workspace):
    """
    Regression test: "Big Kids"/"kids" in the product's own header (not
    just the size block) used to leak into the display text alongside the
    color, e.g. "chestnut Big Kids kids". The size tier is already shown
    by its own group-divider row, so it's redundant here too.
    """

    from utility_modules.models import OrderItem

    item = OrderItem(
        time_stamp="2026-01-01 10:00:00",
        original_order_string=(
            'Big Kids BELLA Janes // Pick Your Color & Size - kids 3 / '
            'W4.5 (foot measures 8.5") shoes measures 8.75" / Chestnut / BELLA JANES'
        ),
    )
    orderParser.parse_order_item_data(item)

    assert item.category == "BELLA"
    assert item.display_text == "chestnut"


def test_big_kids_rainey_display_drops_size_tier_words_and_finds_rhubarb(workspace):
    from utility_modules.models import OrderItem

    item = OrderItem(
        time_stamp="2026-01-01 10:00:00",
        original_order_string=(
            'Big Kids Rainey Janes // Pick Your Color & Size - kids 2.5 '
            '(foot measures 8.25") shoe measures 8.5" / Rhubarb / RAINEY JANES'
        ),
    )
    orderParser.parse_order_item_data(item)

    assert item.category == "RAINEY"
    assert item.colors == ["rhubarb"]
    assert item.display_text == "rhubarb"


def test_mens_possessive_s_does_not_leak_into_display_text(workspace):
    """
    Regression test: "Men's" was reduced to "Men" + a stray bare "s" by
    the ignore-words filter (which drops "men" but has nothing to catch a
    lone "s"), leaving "tumbleweed s" instead of just "tumbleweed". The
    possessive marker is now stripped before tokenizing.
    """

    from utility_modules.models import OrderItem

    item = OrderItem(
        time_stamp="2026-01-01 10:00:00",
        original_order_string=(
            "Men's LOAFERS Darker Colors// Pick Your Color & Size// Wool "
            'Insert included - Men 10.5 (foot measures 11”) shoe length '
            "11.25” / Tumbleweed"
        ),
    )
    orderParser.parse_order_item_data(item)

    assert item.category == "Loafer"
    assert item.display_text == "tumbleweed"


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
