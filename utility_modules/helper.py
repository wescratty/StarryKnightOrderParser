from dataclasses import dataclass
from enum import Enum
from typing import Optional


def get_table_category(order):

    if not order.original_order_string:
        return None

    name = order.original_order_string.lower()

    if "lotus" in name:
        return "Lotus"

    elif "t-strap" in name:
        return "T-strap"

    elif "rainey janes" in name:
        return "RAINEY Janes"

    elif "bella janes" in name:
        return "BELLA Jane"

    elif "mary janes" in name:
        return "Mary Jane"

    elif "sequoia" in name:
        return "SEQ"

    elif "sunrise" in name:
        return "SUN"

    elif "daisy" in name:
        return "Daisy"

    elif "moccs" in name:
        return "Moccs"

    elif "two tone" in name:
        return "Two tone"

    elif "loafer" in name or "loafers" in name:
        return "Loafers"

    elif "critters" in name:
        return "Critters"

    elif "designs" in name:
        return "Designs"

    elif "scout" in name:
        return "Scout"

    elif "gift card" in name:
        return "Gift Card"

    elif "big runner" in name:
        return "Big Runner"

    elif "natural wool insert" in name:
        return "Wool Insert"

    elif "purse" in name:
        return "Purse"

    else:
        print("~~~~~~~" + name)

    return None




@dataclass
class ParseEvent:
    level: int   # "info", "warning", "error"
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

CATEGORY = [
    "Lotus",
    "T-strap",
    "RAINEY Janes",
    "BELLA Jane",
    "Marry Jane", # check if this is correct
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


ADDON_TYPE_MAP = {
    "natural wool insert": AddonType.WOOL,
    "big runner": AddonType.SOLE,
    "purse": AddonType.PURSE,
    "headband": AddonType.HEADBAND,
    "gift card": AddonType.GIFT,
    "unknown": AddonType.UNKNOWN,
}

IGNORE_LOCATION = {
    "(bottom l)",
    "(bottom r)",
    "(top l)",
    "(top r)",
    "(top l)",
    "(middle)",
    "(left)",
    "(right)",
}
