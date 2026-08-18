"""
utility_modules/helper.py

Shared lookup tables and small value types used across the parsing
pipeline: category keywords, addon type <-> icon/category/marker maps,
and the ParseEvent type used to report per-row warnings/errors back to
the GUI.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


@dataclass
class ParseEvent:
    """A single warning/error surfaced to the GUI while parsing a CSV or building the HTML report (see helper.CATEGORY/AddMarkers usage in orderItem.py/models.py)."""

    level: int   # 0=info(green) 1=warning(white/yellow) 2=error(red) -- indexes StarryKnightOrderParser.message_notify
    message: str
    order_num: Optional[str] = None
    order_str: Optional[str] = None
    timestamp: Optional[str] = None


class AddonType(Enum):
    WOOL = "wool"
    SOLE = "sole"
    PURSE = "purse"
    HEADBAND = "headband"
    GIFT = "gift"
    UNKNOWN = "unknown"


CATEGORY_MAP = {
    AddonType.WOOL: "Natural Wool Insert",
    AddonType.SOLE: "Big Runner",
    AddonType.PURSE: "Purse",
    AddonType.HEADBAND: "Headband",
    AddonType.GIFT: "Gift Card",
    AddonType.UNKNOWN: "Unknown",
}

# ----------------------------------------
# Headers
# ----------------------------------------

# orderParser.parse_order_item_data() matches these (case-insensitive
# substring) against the product name to set OrderItem.category -- first
# match wins. Unmatched items get category=None and are silently dropped
# from the main "Shoes" report table (see makeHtml.build_main_table_html,
# which only builds a table per category returned by Batch.get_headers()).
CATEGORY = [
    "Lotus",
    "T-strap",
    "RAINEY",
    "BELLA",
    "Mary",
    "SEQ",
    "SUN",
    "Daisy",
    "Moccs",
    "Two tone",
    "Loafer",
    "Designs",
    "Critters",
    "Scout"
]

# ----------------------------------------
# Maps and Filters
# ----------------------------------------


class AddMarkers(Enum):
    """Keywords orderItem.get_class() matches (case-insensitive substring) to classify a CSV row as an Addon rather than an OrderItem. First match wins."""

    WOOL = "natural wool insert"
    BIG_RUNNER = "big runner"
    PURSE = "purse"
    HEADBAND = "headband"
    GIFT = "gift card"


ICON_MAP = {
    AddonType.WOOL: "🐑",
    AddonType.SOLE: "👟",
    AddonType.PURSE: "👜",
    AddonType.HEADBAND: "🎀",
    AddonType.GIFT: "💳",
}


# AddMarkers value -> AddonType, used by orderItem.get_class() to translate
# the matched marker into the add_type addonParser.classify_addon() reads.
ADDON_TYPE_MAP = {
    "natural wool insert": AddonType.WOOL,
    "big runner": AddonType.SOLE,
    "purse": AddonType.PURSE,
    "headband": AddonType.HEADBAND,
    "gift card": AddonType.GIFT,
    "unknown": AddonType.UNKNOWN,
}

# Multi-item orders sometimes suffix a product name with a per-item
# placement note in parens (e.g. two headbands on the same order, one
# marked "(left)", one "(right)"). Stripped out before color/variant
# matching in orderParser.extract_varient()/extract_colors() so they don't
# get mistaken for a color name.
IGNORE_LOCATION = {
    "(bottom l)",
    "(bottom r)",
    "(top l)",
    "(top r)",
    "(middle)",
    "(left)",
    "(right)",
}
