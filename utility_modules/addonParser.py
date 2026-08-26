"""
utility_modules/addonParser.py

Builds and classifies Addon objects (wool insert, big runner, purse,
headband, gift card) from a CSV row already identified as an addon by
orderItem.get_class().
"""

import re

from utility_modules import helper
from utility_modules.models import Addon


def get_add_on_item(text, time_stamp, add_type, quantity=None, note=None, order_num=None):
    """Builds a bare Addon from a CSV row and immediately runs it through classify_addon() to fill in icon/color/size/category."""

    add = Addon(
        time_stamp=time_stamp,
        original_order_string=text,
        add_type=add_type,
        display_text=text,
        quantity=quantity,
        note=note,
        order_num=order_num
    )
    classify_addon(add)
    return add


def classify_addon(item):
    """
    Fills in an Addon's icon/category/color/size from its add_type and
    display_text. Each add_type has its own extraction rule since the
    Shopify product strings for each are shaped differently -- see the
    per-branch comments below.
    """

    if not isinstance(item, Addon):
        return

    item.icon = helper.ICON_MAP.get(item.add_type, "❓")
    item.category = helper.CATEGORY_MAP.get(item.add_type, helper.CATEGORY_MAP[helper.AddonType.UNKNOWN])

    if item.add_type == helper.AddonType.WOOL:
        # wool insert size is just whatever follows " - " verbatim,
        # e.g. "Natural Wool Insert - Small" -> "Small"
        if " - " in item.display_text:
            item.size = (
                item.display_text
                .split(" - ")[-1]
                .strip()
                .title()
            )

    elif item.add_type == helper.AddonType.SOLE:
        # big runner: color usually follows " - " ("Tan - Big Runner"),
        # otherwise fall back to whatever precedes the "Big Runner" marker
        if " - " in item.display_text:
            item.color = get_color_end_hyphen(item)
        if item.color is None:
            item.color = extract_big_runner_color(item.display_text)

    elif item.add_type == helper.AddonType.HEADBAND:
        item.color = get_color_end_hyphen(item)
        item.add_type = helper.AddonType.HEADBAND
        item.icon = helper.ICON_MAP.get(helper.AddonType.HEADBAND)
        item.size = "None"

    elif item.add_type == helper.AddonType.PURSE:
        item.add_type = helper.AddonType.PURSE
        item.color = extract_purse_color(item.display_text)
        item.icon = helper.ICON_MAP.get(helper.AddonType.PURSE)
        item.size = "None"
        # The color (the purse's name, e.g. "Big Sky Mountains") is the
        # only useful information in the product string -- the rest
        # ("Leather PURSE Toddler & Kids") is boilerplate that would
        # otherwise duplicate right after the color in get_display().
        item.display_text = ""

    elif item.add_type == helper.AddonType.GIFT:
        item.add_type = helper.AddonType.GIFT
        item.color = "None"
        item.size = "None"

    else:
        # get_class() only ever passes an add_type it found in
        # ADDON_TYPE_MAP, so this branch is effectively unreachable today;
        # kept as a safety net in case that mapping and AddMarkers drift
        # out of sync in the future.
        item.icon = "➕"
        item.add_type = helper.AddonType.UNKNOWN


def get_color_end_hyphen(item):
    """Returns whatever follows the last " - " in display_text, e.g. "Tan - Big Runner" -> "Big Runner" (title-cased)."""

    return item.display_text.split(" - ")[-1].strip().title()


def extract_big_runner_color(text):
    """Fallback big-runner color extraction: whatever text precedes the "Big Runner" marker (case-insensitive, since Shopify product strings vary in casing -- e.g. "BIG RUNNER" -- and a case-sensitive match would silently fail and return the whole string), e.g. "Tan Big Runner" -> "Tan"."""

    match = re.search("big runner", text, re.IGNORECASE)

    if not match:
        return "None"

    color = text[:match.start()].strip()
    # strip a trailing "Leather" -- "<Name> Leather Big Runner" -> "<Name>"
    color = re.sub(r"\s+leather\s*$", "", color, flags=re.IGNORECASE).strip()

    if not color:
        return "None"

    return color.title()


def extract_purse_color(text):
    """Purse color extraction: whatever text precedes "purse" (case-insensitive), e.g. "Tan Purse" -> "Tan". Matches case-insensitively against the original text (not text.split() against a lowercase marker) since Shopify product strings often have "PURSE" in caps, which a case-sensitive split would silently miss and return the whole string instead."""

    match = re.search("purse", text, re.IGNORECASE)

    if not match:
        return "None"

    color = text[:match.start()].strip()
    # strip a trailing "Leather" -- "<Name> Leather PURSE" -> "<Name>"
    color = re.sub(r"\s+leather\s*$", "", color, flags=re.IGNORECASE).strip()

    if not color:
        return "None"

    return color.title()
