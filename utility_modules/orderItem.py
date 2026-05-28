from dataclasses import dataclass, field
from typing import Optional
import re
import config
from enum import Enum


addonList = list()


class AddonType(Enum):

    WOOL = "wool"
    SOLE = "sole"
    GIFT = "gift"
    UNKNOWN = "unknown"


ADDON_TYPE_MAP = {

    "Natural Wool Insert": AddonType.WOOL,

    "Big Runner": AddonType.SOLE,

    "Gift Card": AddonType.GIFT,
}

# ----------------------------------------
# master color list
# easy to extend later
# ----------------------------------------

# Get Notes and highlight if note
DEBUG = False

# ----------------------------------------
# words that do not matter operationally
# for display text generation
# ----------------------------------------
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


# ----------------------------------------
# final table headers
# ----------------------------------------

header = [
    "Size",
    "Lotus",
    "T-strap",
    "RAINEY Janes",
    "BELLA Jane",
    "SEQ",
    "SUN",
    "Daisy",
    "Moccs",
    "Two tone",
    "Loafers",
    "Designs",
    "Critters",
    "Scout"
]


@dataclass
class ParseEvent:
    level: int   # "info", "warning", "error"
    message: str
    orderNum: Optional[str] = None
    timestamp: Optional[str] = None


# ----------------------------------------
# order object
# ----------------------------------------
@dataclass()
class Addon:
    timeStamp: str
    original_order_string: str
    quantity: Optional[str] = None
    note: Optional[str] = None
    orderNum: Optional[str] = None
    category: Optional[str] = None

    type = AddonType.UNKNOWN
    description = None
    icon = None
    color = None
    display_text: Optional[str] = None


@dataclass
class OrderItem:

    # mandatory
    timeStamp: str

    # untouched original order string
    original_order_string: str
    addOns: list["Addon"] = field(default_factory=list)

    # order number
    orderNum: Optional[str] = None

    # quantity
    quantity: Optional[str] = None

    # parsed display string
    note: Optional[str] = None

    # parsed display string
    display_text: Optional[str] = None

    # parsed attributes
    product_name: Optional[str] = None
    category: Optional[str] = None

    size: Optional[str] = None
    age: Optional[str] = None
    measurement: Optional[str] = None

    variant: Optional[str] = None
    variant_full: Optional[str] = None
    variant_display: Optional[str] = None

    # multiple colors possible
    colors: list = field(default_factory=list)


def classify_addon(item):
    if not isinstance(item, Addon):
        return

    # ----------------------------------------
    # wool insert
    # ----------------------------------------

    if item.type == AddonType.WOOL:

        item.icon = "🐑"

    # ----------------------------------------
    # rubber sole
    # ----------------------------------------

    elif item.type == AddonType.SOLE:

        item.icon = "👟"

        if " - " in item.description:

            item.color = (
                item.description
                .split(" - ")[-1]
                .strip()
                .title()
            )

    # ----------------------------------------
    # fallback
    # ----------------------------------------

    else:

        item.icon = "➕"
        item.type = AddonType.UNKNOWN


def parse_gift_card(item, text):

    if "gift card" not in text.lower():
        return

    item.description = text
    item.icon = "💳"
    item.type = AddonType.GIFT


def extract_big_runner_color(text):

    marker = "Big Runner"

    if marker not in text:
        return None

    color = text.split(marker)[0].strip()

    if not color:
        return None

    return color.title()


# def detect_special_item(item, text):
#
#     lower = text.lower()
#
#     # ----------------------------------------
#     # structured ADD// addons
#     # ----------------------------------------
#     if text.startswith("ADD//"):
#
#         parse_addon(item, text)
#
#     # ----------------------------------------
#     # embedded sole addon
#     # ----------------------------------------
#
#     elif "big runner add to men's" in lower:
#
#         item.is_addon = True
#
#         item.addon_type = AddonType.SOLE
#
#         item.addon_description = text
#         item.colors = [extract_big_runner_color(text)]
#
#     # ----------------------------------------
#     # gift cards
#     # ----------------------------------------
#
#     if "gift card" in lower:
#
#         parse_gift_card(item, text)


def get_order_item(text, timeStamp, quantity=None, note=None, orderNum=None):
    return OrderItem(
        timeStamp=timeStamp,
        original_order_string=text,
        quantity=quantity,
        note=note,
        orderNum=orderNum
    )


def get_add_on_item(text, timeStamp, quantity=None, note=None, orderNum=None):
    return Addon(
        timeStamp=timeStamp,
        original_order_string=text,
        display_text=text,
        quantity=quantity,
        note=note,
        orderNum=orderNum
    )


def detect_class(text, timeStamp, quantity=None, note=None, orderNum=None):
    lower = text.lower()

    if text.startswith("ADD//"):
        item = get_add_on_item(text, timeStamp, quantity, note, orderNum)
        parse_addon(item, text)
        classify_addon(item)

        # detect_special_item(item, text)

    elif "big runner add to men's" in lower:
        item = get_add_on_item(text, timeStamp, quantity, note, orderNum)
        item.type = AddonType.SOLE
        item.description = text
        item.display_text = text
        item.icon = "👟"
        item.color = extract_big_runner_color(text)
        item.note = note

    elif "gift card" in lower:
        item = get_add_on_item(text, timeStamp, quantity, note, orderNum)
        parse_gift_card(item, text)
    else:
        item = get_order_item(text, timeStamp, quantity, note, orderNum)

    return item


def parse_addon(item, text):
    parts = text.split("//")
    if len(parts) < 3:
        return

    raw_type = parts[1].strip()

    item.type = ADDON_TYPE_MAP.get(
        raw_type,
        AddonType.UNKNOWN
    )

    description = parts[2].strip()
    item.description = description
    item.display_text = text

# ----------------------------------------
# color extraction
# ----------------------------------------


def extract_varient(text):

    found = []
    colors = get_colors()

    lower = text.lower()

    # remove junk location suffixes
    for junk in IGNORE_LOCATION:
        lower = lower.replace(junk, "")

    # longest first prevents partial collisions
    for color in colors:
        if color in lower:
            found.append(lower)

    return list(set(found))


def get_colors():

    return config.load_colors()


def get_ignore_words():

    return config.load_ignore_words()


def extract_colors(text):
    colors = get_colors()
    found = []

    lower = text.lower()

    # remove junk location suffixes
    for junk in IGNORE_LOCATION:
        lower = lower.replace(junk, "")

    # longest first prevents partial collisions
    for color in colors:

        if color in lower:
            found.append(color)

    return list(set(found))


# ----------------------------------------
# display text extraction
# ----------------------------------------

def extract_display_text(main_text, colors=None, variant_display=None):

    COLORS = get_colors()
    IGNORE_WORDS = get_ignore_words()
    # everything before size block already removed
    left = main_text

    # normalize separators
    left = left.replace("//", " ")

    # remove (...) option lists entirely
    left = re.sub(r"\(.*?\)", "", left)

    # tokenize
    words = re.findall(r"[A-Za-z]+", left)

    filtered = []

    for word in words:

        lower = word.lower()

        if lower not in IGNORE_WORDS:
            if colors:
                if lower not in COLORS:
                    filtered.append(word)
            else:
                filtered.append(word)

    filtered = list(dict.fromkeys(filtered))

    result = " ".join(filtered).strip()

    if colors:
        result = f"{', '.join(colors)} {result}"

    return result.strip()

# ----------------------------------------
# parse single order
# ----------------------------------------


def parse_order_item(
    text,
    timeStamp,
    quantity=None,
    note=None,
    orderNum=None
):

    item = detect_class(text, timeStamp, quantity, note, orderNum)
    if isinstance(item, Addon):
        return item


    # --------------------------
    # colors
    # prefer variant colors first
    # --------------------------

    item.colors = []

    # --------------------------
    # split variant
    # --------------------------

    parts = text.split(" / ")

    main = parts[0]

    if len(parts) > 1:
        item.variant_full = parts[1].strip()

    # variant usually contains the actual chosen color
    if item.variant_full:
        color_list = extract_varient(item.variant_full)
        if len(color_list):
            item.colors = color_list

        # fallback display-safe version (keeps modifiers)
        # item.variant_display = item.variant_full

    # fallback to full string
    if not item.colors:
        item.colors = extract_colors(text)

    # --------------------------
    # display text
    # --------------------------

    item.display_text = extract_display_text(
        main,
        item.colors,
        item.variant_display
    )

    # --------------------------
    # extract size block
    # --------------------------

    size_match = re.search(
        r'-\s*([0-9]+)\s*\((.*?)\)\s*([0-9.]+")',
        main
    )

    if size_match:

        item.size = size_match.group(1).strip()
        item.age = size_match.group(2).strip()
        item.measurement = size_match.group(3).strip()

        # remove sizing info
        main = main[:size_match.start()].strip()

    # --------------------------
    # category detection
    # --------------------------

    categories = [
        "LOAFERS",
        "MOCCS",
        "SCOUT BOOTIES",
        "BELLA JANES",
        "RAINEY JANES",
        "SUNRISE",
        "SEQUOIA",
        "T-Strap",
        "SANDALS",
        "Cute Critters",
        "Headband",
        "Gift card"
    ]

    for cat in categories:

        if cat.lower() in main.lower():
            item.category = cat
            break

    item.product_name = main

    return item


# ----------------------------------------
# parse many orders
# ----------------------------------------

def parse_orders(
    order_strings,
    timestamps=None,
    quantities=None,
    notes=None,
    orderNums=None
):

    orders = []
    events = []

    last_processed = config.load_last_processed_timestamp()

    newest_timestamp = None

    for i, text in enumerate(order_strings):

        ts = ""

        if timestamps:
            ts = timestamps[i]

        order_num = None

        if orderNums:
            order_num = orderNums[i]

        quantity = None
        if quantities:
            quantity = quantities[i]

        quantity = int(quantity) if quantity else 1

        note = None
        if notes:
            note = notes[i]

        # ----------------------------------------
        # skip previously processed
        # ----------------------------------------

        if ts and not DEBUG:

            current_dt = config.timestamp_to_datetime(ts)

            if last_processed and current_dt <= last_processed:
                events.append(ParseEvent(
                    level=1,
                    message=f"Skipping already processed order: {ts}",
                    orderNum=orderNums[i] if orderNums else None,
                    timestamp=ts
                ))

                continue

            if (
                newest_timestamp is None or
                current_dt > newest_timestamp
            ):
                newest_timestamp = current_dt
        item = parse_order_item(
                text=text,
                timeStamp=ts,
                quantity=quantity,
                note=note,
                orderNum=order_num
            )

        if isinstance(item, Addon):
            addonList.append(item)
        elif isinstance(item, OrderItem):
            orders.append(item)

    for addon in addonList:
        for item in orders:
            if item.orderNum == addon.orderNum:
                item.addOns.append(addon)
    # ----------------------------------------
    # save newest processed timestamp
    # ----------------------------------------

    if newest_timestamp:

        config.set_last_processed_timestamp(
            newest_timestamp.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

    return orders, events
