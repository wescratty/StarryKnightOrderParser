from dataclasses import dataclass, field
from typing import Optional
import re
import config

# ----------------------------------------
# master color list
# easy to extend later
# ----------------------------------------

# Get Notes and highlight if note
DEBUG = False
# COLORS = [
#
#     "barley",
#     "beige",
#     "big sky",
#     "black",
#     "camel",
#     "caramel",
#     "carob",
#     "chai",
#     "chestnut",
#     "cream",
#     "daffodil",
#     "dusty rose",
#     "flax",
#     "gray",
#     "grey",
#     "honey",
#     "iron",
#     "latte",
#     "lichen",
#     "milk",
#     "navy",
#     "oat",
#     "oyster",
#     "papaya",
#     "pink",
#     "platinum",
#     "rose blush",
#     "russet",
#     "rust",
#     "sable",
#     "saddle",
#     "sahara",
#     "sepia",
#     "sienna",
#     "tan",
#     "tumbleweed",
#     "white",
#     "wood",
# ]

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

IGNORE_WORDS = {

    "baby",
    "toddler",
    "and",
    "shoes",
    "shoe",
    "leather",
    "cute",
    "moccs",
    "mocc",
    "loafer",
    "loafers",
    "jane",
    "janes",
    "sunrise",
    "bella",
    "rainey",
    "strap",
    "t",
    "lotus",
    "daisy",
    "critters",
    "scout",
    "sequoia",
    "mary",
    "booties",
    "sandals",
    "headband",
    "two",
    "tone",
    "pick",
    "your",
    "color",
    "//",
    "&",
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


@dataclass
class OrderItem:

    # mandatory
    timeStamp: str

    # untouched original order string
    original_order_string: str

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

    is_addon: bool = False
    is_gift_card: bool = False


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

    item = OrderItem(
        timeStamp=timeStamp,
        original_order_string=text,
        quantity=quantity,
        note=note,
        orderNum=orderNum
    )

    # --------------------------
    # flags
    # --------------------------

    if text.startswith("ADD//"):
        item.is_addon = True

    if "Gift card" in text:
        item.is_gift_card = True

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

        orders.append(
            parse_order_item(
                text=text,
                timeStamp=ts,
                quantity=quantity,
                note=note,
                orderNum=order_num
            )
        )

    # ----------------------------------------
    # save newest processed timestamp
    # ----------------------------------------

    if newest_timestamp:

        config.save_last_processed_timestamp(
            newest_timestamp.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

    return orders, events
