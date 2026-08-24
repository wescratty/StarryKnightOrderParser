"""
Tests for utility_modules.addonParser: purse/big-runner color extraction
and the PURSE display-text/piggyback behavior.
"""

from utility_modules import helper
from utility_modules import addonParser


def test_extract_purse_color_is_case_insensitive_against_all_caps_marker():
    """
    Regression test: real Shopify product strings write the marker in all
    caps ("...Leather PURSE Toddler & Kids"), but the old code did
    text.split("purse") against the ORIGINAL (non-lowercased) text with a
    lowercase marker -- the split silently failed to match and returned
    the entire raw string as the "color".
    """

    color = addonParser.extract_purse_color(
        "Big Sky Mountains Leather PURSE Toddler & Kids"
    )
    assert color == "Big Sky Mountains"


def test_extract_purse_color_lowercase_marker_still_works():
    color = addonParser.extract_purse_color("Tan purse")
    assert color == "Tan"


def test_extract_big_runner_color_is_case_insensitive():
    color = addonParser.extract_big_runner_color("Tan Leather BIG RUNNER")
    assert color == "Tan"


def test_extract_big_runner_color_lowercase_marker_still_works():
    color = addonParser.extract_big_runner_color("Black Big Runner")
    assert color == "Black"


def test_classify_addon_purse_display_text_is_empty_so_color_is_not_duplicated():
    """
    Regression test: the purse's color/name (extracted separately, shown
    in parens by get_display()) used to also survive as the addon's
    display_text verbatim, so the report showed the same name twice, e.g.
    "(Big Sky Mountains Leather Purse Toddler & Kids)Big Sky Mountains
    Leather PURSE Toddler & Kids". The remaining text is boilerplate with
    no further information once the color has been pulled out, so
    display_text is now cleared instead.
    """

    item = addonParser.get_add_on_item(
        "Big Sky Mountains Leather PURSE Toddler & Kids",
        "2026-01-01 10:00:00",
        helper.AddonType.PURSE,
    )

    assert item.color == "Big Sky Mountains"
    assert item.display_text == ""
    assert item.get_display() == "👜(Big Sky Mountains)"
