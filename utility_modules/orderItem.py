"""
utility_modules/orderItem.py

Turns raw Shopify CSV columns into domain objects and groups them into a
Batch that makeHtml.py renders into the production cut-sheet HTML.

Pipeline, top to bottom:
  1. parse_orders()      -- one CSV -> one Batch. Iterates every row,
                             isolates failures per-row, returns (Batch, events).
  2. parse_order_item()  -- one row -> one OrderItem or Addon.
  3. get_class()         -- decides OrderItem vs Addon by keyword match
                             ("wool insert", "big runner", "purse", ...).
  4. parse_order_item_data() / classify_addon()
                          -- fill in size/color/category fields for
                             whichever kind of object it is.

Two parallel object kinds come out of this:
  - OrderItem: a pair of shoes -- the thing being made.
  - Addon: an extra attached to an order -- wool insert, big runner
    (spare sole), purse, headband, or gift card. Rendered separately from
    OrderItems in the HTML report.

NOTE (review, see PR): parse_order_item() below re-runs
parse_order_item_data() on OrderItems that get_class() -> get_order_item()
has *already* fully parsed, so every OrderItem is parsed twice per row.
It's currently harmless (parse_order_item_data is idempotent -- it always
recomputes from item.original_order_string, which never changes), but it's
wasted work and a latent trap if that function is ever made to accumulate
instead of overwrite. Flagged rather than fixed here -- see chat for the
full write-up.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
import re
import config
from utility_modules import helper
from collections import defaultdict


# DEBUG mode now lives in config (config.get_debug_mode() /
# config.set_debug_mode()), persisted to a workspace file, instead of being
# hardcoded here. While DEBUG is True, the "skip already-processed orders"
# feature is off and every order in the CSV is reprocessed regardless of
# the Last Processed Order Timestamp shown in the GUI.


# ----------------------------------------
# Classes
# ----------------------------------------


@dataclass()
class Addon:
    """
    An extra attached to an order, distinct from the shoes themselves:
    natural wool insert, big runner (spare/replacement sole), purse,
    headband, or gift card. Which one is decided by get_class() matching a
    keyword in helper.AddMarkers against the Shopify line item text.

    add_type drives most of the downstream behavior (icon, category,
    color/size extraction rules) -- see classify_addon() below.
    """

    time_stamp: str
    original_order_string: str
    icon: Optional[str] = None
    color: Optional[str] = None
    order_num: Optional[str] = None
    quantity: Optional[int] = 1
    note: Optional[str] = None
    display_text: Optional[str] = None
    product_name: Optional[str] = None
    category: Optional[str] = None
    size: Optional[int] = None
    prefix: Optional[str] = None

    add_type: Optional[helper.AddonType] = None

    def get_size_and_prefix_tuple(self):
        return self.prefix, str(self.size)

    def set_size_and_prefix_tuple(self, size_tuple):
        self.prefix = size_tuple[0]
        self.size = size_tuple[1]

    def get_display(self):
        """
        Builds the label shown for this addon in its own row of the HTML
        report: note emoji, category icon, color in parens, then whichever
        of display_text / product_name / original_order_string is set
        (in that priority order -- first one wins).
        """

        ret_str = f""
        if self.note:
            ret_str += f"📝 {self.note}\n"
        if self.icon:
            ret_str += f"{self.icon}"
        if self.color:
            ret_str += f"({self.color})"
        if self.display_text:
            ret_str += f"{self.display_text}"
        elif self.product_name:
            ret_str += f"{self.product_name}"
        elif self.original_order_string:
            ret_str += f"{self.original_order_string}"

        return ret_str

    def get_order_piggyback_display(self):
        """
        Compact form of get_display() used when an addon is shown
        "piggybacked" inline on its parent OrderItem's row instead of its
        own row (no product name -- just note/icon/color/quantity).
        """

        ret_str = f""
        if self.note:
            ret_str += f"📝"
        if self.icon:
            ret_str += f"{self.icon}"
        if self.color:
            ret_str += f"({self.color})"
        if self.quantity and int(self.quantity) > 1:
            ret_str += f"X{self.quantity}"

        return ret_str


@dataclass
class OrderItem:
    """
    A pair of shoes from one Shopify line item -- the thing actually being
    produced. Everything from `age`/`measurement`/`variant`/
    `variant_display`/`size_prefix` down to `colors` is populated (or, for
    several of these fields, left at its default -- see review notes) by
    parse_order_item_data() from the raw Shopify product string.
    """

    time_stamp: str
    original_order_string: str
    order_num: Optional[str] = None
    quantity: Optional[int] = 1
    note: Optional[str] = None
    display_text: Optional[str] = None
    product_name: Optional[str] = None
    category: Optional[str] = None

    size: Optional[int] = None
    prefix: Optional[str] = None

    addOns: list["Addon"] = field(default_factory=list)
    age: Optional[str] = None
    size_prefix: Optional[str] = None
    measurement: Optional[str] = None
    variant: Optional[str] = None
    variant_full: Optional[str] = None
    variant_display: Optional[str] = None
    colors: list = field(default_factory=list)

    def get_size_and_prefix_tuple(self):
        return self.prefix, str(self.size)

    def set_size_and_prefix_tuple(self, size_tuple):
        self.prefix = size_tuple[0]
        self.size = size_tuple[1]

    def get_display(self):
        """
        Builds the label shown for this order item's own row in the HTML
        report: note emoji, then whichever of display_text / product_name /
        original_order_string is set, then an "X<quantity>" suffix if more
        than one pair was ordered.
        """

        ret_str = f""
        if self.note:
            ret_str += f"📝"
        if self.display_text:
            ret_str += f"{self.display_text}"
        elif self.product_name:
            ret_str += f"{self.product_name}"
        elif self.original_order_string:
            ret_str += f"{self.original_order_string}"
        if self.quantity and int(self.quantity) > 1:
            ret_str += f"X{self.quantity}"
        return ret_str

    def get_tool_tip(self, add_ons):
        """
        Builds the hover tooltip for this order item: order number, the
        raw Shopify product string, this item's note, then one line per
        addon attached to the same order (via their get_display()).
        Quotes are escaped since this gets embedded as an HTML attribute.
        """

        tooltip_parts = list()
        tooltip_parts.append(f"Order {self.order_num}")
        tooltip_parts.append(self.original_order_string)
        tooltip_parts.append(self.note or "")
        if len(add_ons):
            for add in add_ons:
                tooltip_parts.append(add.get_display())

        return "\n".join(tooltip_parts).strip().replace('"', '&quot;')


@dataclass
class Order:
    """
    NOTE (review): unused elsewhere in the codebase. Batch groups
    OrderItems/Addons by order_num into plain dicts instead of ever
    constructing one of these. Kept as-is; flagged as dead code in chat.
    """

    time_stamp: str
    order_num: Optional[str] = None
    note: Optional[str] = None

    addOns: List[Addon] = field(default_factory=list)
    orderItems: List[OrderItem] = field(default_factory=list)


@dataclass
class Batch:
    """
    The full result of parsing one CSV: every OrderItem and Addon, grouped
    by order_num, plus the reporting/lookup helpers makeHtml.py uses to
    build the HTML tables (by category, by addon type, etc.).

    Two flat lists (addOns_list / orders_list) are the source of truth,
    fed in one row at a time via add_add_on()/add_order() as parse_orders()
    works through the CSV. __post_init__ (and the same-named re-call at the
    end of parse_orders(), once every row has been added) rebuilds the
    order_num -> [items] groupings from those flat lists.
    """

    addOns_list: List[Addon] = field(default_factory=list)
    orders_list: List[OrderItem] = field(default_factory=list)
    orderItems: Dict[str, List[OrderItem]] = field(init=False, default_factory=dict)
    orderAddons: Dict[str, List[Addon]] = field(init=False, default_factory=dict)

    def __post_init__(self):
        """Rebuilds orderItems/orderAddons (order_num -> [items]) from the flat lists."""

        grouped_orders = defaultdict(list)
        grouped_addons = defaultdict(list)

        for item in self.orders_list:
            grouped_orders[item.order_num].append(item)

        self.orderItems = dict(grouped_orders)

        for item in self.addOns_list:
            grouped_addons[item.order_num].append(item)

        self.orderAddons = dict(grouped_addons)

    def add_add_on(self, add_on: Addon):
        self.addOns_list.append(add_on)

    def add_order(self, order: OrderItem):
        self.orders_list.append(order)

    def get_order_item(self, order_num: str) -> List[OrderItem]:
        return self.orderItems.get(order_num, [])

    def get_orders(self):
        return self.orderItems

    def get_order_addon_items(self, order_num: str) -> List[Addon]:
        return self.orderAddons.get(order_num, [])

    def get_all_order_items(self) -> List[OrderItem]:
        result = []

        for items in self.orderItems.values():
            result.extend(items)

        return result

    def get_headers(self) -> List[str]:
        """Returns each distinct OrderItem.category seen, in first-seen order (used as HTML report section headers)."""

        result = dict()

        for item in self.get_all_order_items():
            if item.category not in result:
                result[item.category] = 1

        return list(result.keys())

    def get_all_addon_items(self) -> List[Addon]:
        result = []

        for items in self.orderAddons.values():
            result.extend(items)

        return result

    def get_addon_category(self, category: str) -> List[Addon]:
        """NOTE (review): unused -- get_addon_categorized() below is what makeHtml.py actually calls."""

        return self.orderAddons.get(category, [])

    def get_order_notes(self) -> List[tuple[str, str]]:
        """NOTE (review): unused elsewhere in the codebase."""

        notes = []

        for items in self.orderItems.values():
            for item in items:
                if item.note:
                    notes.append((item.order_num, item.note))

        return notes

    def get_order_category(self, category: str) -> List[OrderItem]:
        """All OrderItems whose category matches (used by makeHtml.py to build one table per category)."""

        orders = []

        for items in self.orderItems.values():
            for item in items:
                if item.category == category:
                    orders.append(item)

        return orders

    def get_addon_notes(self) -> List[tuple[str, str]]:
        """NOTE (review): unused elsewhere in the codebase."""

        notes = []

        for items in self.orderAddons.values():
            for item in items:
                if item.note:
                    notes.append((item.order_num, item.note))

        return notes

    def get_addon_categorized(self):
        """
        Groups addons for the HTML report: by category normally, but by
        "<category> <color>" for big runners (SOLE) specifically, since tan
        and black big runners are cut/tracked separately. Gift cards are
        dropped entirely -- they're not a production item. Also triggers
        get_try_big_runner_size() as a side effect first, since that's what
        fills in add.size for big runners before they're grouped/displayed.
        """

        add_ons = self.get_all_addon_items()
        addon_rows = defaultdict(list)
        self.get_try_big_runner_size()

        for add in add_ons:
            if add.add_type == helper.AddonType.GIFT:
                continue

            if add.add_type == helper.AddonType.SOLE:
                addon_rows[f"{add.category} {add.color}"].append(add)
            else:
                addon_rows[add.category].append(add)

        return addon_rows

    def get_try_big_runner_size(self):
        """
        Big Runner (spare sole) line items don't carry their own size --
        the customer is expected to want a size matching the shoes in the
        same order. This best-effort infers that size by matching up big
        runner add-ons with the OrderItems in the same order, one-to-one,
        and copies the order note onto any addon that doesn't have its own.

        Only proceeds if the order's shoe-pair count exactly matches its
        total big runner count (tan + black) -- i.e. it can assume "one big
        runner per pair" and doesn't have to guess which runner belongs to
        which pair. If that assumption doesn't hold (total_runners > 0 but
        doesn't match order count), it prints a warning and leaves those
        addons' sizes unset rather than guessing wrong.

        NOTE (review): reassigns the local `orders` variable partway
        through from "the whole order_num -> [OrderItem] dict"
        (self.get_orders()) to "this order's OrderItem list"
        (self.get_order_item(order_num)) -- works today only because
        order_nums was already captured into its own list first, but it's
        a confusing name collision worth renaming if this gets touched
        again. Also uses print() for its diagnostics instead of the
        ParseEvent mechanism used everywhere else in the parsing pipeline.
        """

        orders = self.get_orders()
        order_nums = list(orders.keys())
        for order_num in order_nums:
            add_ons = self.get_order_addon_items(order_num)
            orders = self.get_order_item(order_num)
            note = None
            for order in orders:
                if order.note:
                    note = order.note

            total_black_big_runners = 0
            total_tan_big_runners = 0

            for add in add_ons:
                if not add.note and note is not None:
                    add.note = note
                if add.add_type == helper.AddonType.SOLE:
                    if add.color.lower() == "tan":
                        total_tan_big_runners += add.quantity
                    if add.color.lower() == "black":
                        total_black_big_runners += add.quantity

            total_runners = total_black_big_runners + total_tan_big_runners

            if len(orders) == total_runners:
                if total_black_big_runners == 0 or total_tan_big_runners == 0:
                    print("can figure out runner size")
                    size_list = list()
                    idx = 0
                    for order in orders:
                        size_list.append(order.size)
                    for add in add_ons:
                        if add.add_type == helper.AddonType.SOLE:
                            add.size = size_list[idx]
                            idx += 1

                            # set tuple thing

            elif total_runners > 0:
                print(order_num, "can not figure out runner size!!!!!!!!!!!!!!!!!")

    def get_total_pairs(self):
        """NOTE (review): unused elsewhere in the codebase. Total pairs of shoes across every OrderItem (quantity summed, defaulting missing quantity to 1)."""

        all_orders = self.get_all_order_items()
        total = 0
        for order in all_orders:
            q = 1
            if order.quantity:
                q = int(order.quantity)
            total += q

        return total


def get_class(
    text,
    time_stamp,
    quantity=None,
    note=None,
    order_num=None
):
    """
    First decision point for a CSV row: is this an Addon (wool insert, big
    runner, purse, headband, gift card -- one of helper.AddMarkers) or a
    plain OrderItem (shoes)? Decided purely by substring match against the
    lowercased line item text; first marker to match wins, so if a product
    name were ever to contain more than one marker keyword, whichever is
    listed first in helper.AddMarkers takes priority.
    """

    lower = (text or "").lower()

    for marker in helper.AddMarkers:
        if marker.value in lower:
            return get_add_on_item(
                text=text,
                time_stamp=time_stamp,
                add_type=helper.ADDON_TYPE_MAP.get(marker.value, helper.AddonType.UNKNOWN),
                quantity=quantity,
                note=note,
                order_num=order_num,
            )

    return get_order_item(text, time_stamp, quantity=quantity, note=note, order_num=order_num)


def get_order_item(text, time_stamp, quantity=None, note=None, order_num=None):
    """Builds a bare OrderItem from a CSV row and immediately runs it through parse_order_item_data() to fill in size/color/category."""

    order = OrderItem(
        time_stamp=time_stamp,
        original_order_string=text,
        quantity=quantity,
        note=note,
        order_num=order_num
    )

    return parse_order_item_data(order)


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


def get_size_and_prefix(item, size_str):
    """
    Pulls the size block off the end of a product string and sets
    item.size / item.prefix from it, e.g. "Some Product - 10" -> size="10",
    or "Some Product - Kids 10" / "Some Product - W 8" -> a "kids"/"W"/"M"
    prefix plus the numeric size. Returns size_str with the matched size
    block stripped off (or unchanged if no size pattern was found -- not
    every product line has one, e.g. addons or malformed product names).
    """

    size_match = re.search(
        r'-\s*(?:(kids)|([WM]))?\s*(\d+(?:\.\d+)?)',
        size_str,
        re.IGNORECASE
    )

    if size_match:
        kids_prefix, wm_prefix, size_number = size_match.groups()
        item.size = size_number
        item.prefix = kids_prefix or wm_prefix
        size_str = size_str[:size_match.start()].strip()

    return size_str


# ----------------------------------------
# Addon Data Extraction
# ----------------------------------------

def classify_addon(item):
    """
        refactor this
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
        print("Missed one", item)


def get_color_end_hyphen(item):
    """Returns whatever follows the last " - " in display_text, e.g. "Tan - Big Runner" -> "Big Runner" (title-cased)."""

    return item.display_text.split(" - ")[-1].strip().title()


def parse_gift_card(item, text):
    """NOTE (review): unused elsewhere in the codebase -- gift cards are actually classified via get_class()'s AddMarkers.GIFT match, not this function."""

    if "gift card" not in text.lower():
        return

    item.display_text = text
    item.add_type = helper.AddonType.GIFT
    item.category = "Gift Card"


def extract_big_runner_color(text):
    """Fallback big-runner color extraction: whatever text precedes the "Big Runner" marker, e.g. "Tan Big Runner" -> "Tan"."""

    marker = "Big Runner"

    if marker not in text:
        return "None"

    color = text.split(marker)[0].strip()

    if not color:
        return "None"

    return color.title()


def extract_purse_color(text):
    """Purse color extraction: whatever text precedes "purse" (case-insensitive), e.g. "Tan Purse" -> "Tan"."""

    marker = "purse"

    if marker not in text.lower():
        return "None"

    color = text.split(marker)[0].strip()

    if not color:
        return "None"

    return color.title()


# ----------------------------------------
# OrderItem Data Extraction
# ----------------------------------------


def get_colors():

    return config.load_colors()


def get_ignore_words():

    return config.load_ignore_words()


def extract_varient(text):
    """
    Matches known colors (config/colors.txt) against the variant block
    (the part of the product string after " / ", which is Shopify's
    "customer selected this option" field). Note this returns the matched
    *lowercased full text* for each hit, not the color name itself --
    see extract_colors() below for the version that returns color names.
    Deduplicated via set(), so ordering isn't guaranteed.
    """

    found = []
    colors = get_colors()

    lower = text.lower()

    # remove junk location suffixes
    for junk in helper.IGNORE_LOCATION:
        lower = lower.replace(junk, "")

    # longest first prevents partial collisions
    for color in colors:
        if color in lower:
            found.append(lower)

    return list(set(found))


def extract_colors(text):
    """
    Fallback color extraction used when the variant block (see
    extract_varient()) didn't yield anything: scans the full original
    product string for any known color name. Returns the matched color
    names themselves (unlike extract_varient()). Deduplicated via set(),
    so ordering isn't guaranteed.
    """

    colors = get_colors()
    found = []

    lower = text.lower()

    # remove junk location suffixes
    for junk in helper.IGNORE_LOCATION:
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
    """
    Builds the human-readable product name shown in the report: strips
    "(...)" option lists, tokenizes to words, drops anything in
    config/ignore_words.txt (marketing filler like "Baby and Toddler") and
    -- if colors were already extracted separately -- drops color words
    too so they don't appear twice, then de-dupes while preserving first-
    seen order. If colors were found, they're prepended to the result.

    NOTE (review): the variant_display parameter is accepted but never
    read in the body below -- dead parameter. OrderItem.variant_display is
    also never assigned anywhere in this module, so it's always None
    wherever it's passed in from parse_order_item_data().
    """

    got_colors = get_colors()
    got_ignore = get_ignore_words()
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

        if lower not in got_ignore:
            if colors:
                if lower not in got_colors:
                    filtered.append(word)
            else:
                filtered.append(word)

    filtered = list(dict.fromkeys(filtered))
    result = " ".join(filtered).strip()

    if colors:
        result = f"{', '.join(colors)} {result}"

    return result.strip()


def parse_order_item(
    text,
    time_stamp,
    quantity=None,
    note=None,
    order_num=None
):
    """
    Entry point used by parse_orders() for a single CSV row: classifies it
    via get_class() (Addon or OrderItem) and, if it came back as an
    OrderItem, runs parse_order_item_data() on it.

    NOTE (review): get_class() -> get_order_item() already calls
    parse_order_item_data() once before returning here, so this second
    call re-parses the same OrderItem from scratch. Currently harmless
    (parse_order_item_data always recomputes from
    item.original_order_string rather than appending), but it's double
    the work per order and worth collapsing to one call if this file gets
    revisited.
    """

    item = get_class(text, time_stamp, quantity, note, order_num)
    if isinstance(item, Addon):
        return item

    return parse_order_item_data(item)


def parse_order_item_data(item):
    """
    Fills in an OrderItem's derived fields from item.original_order_string:
      1. Split on " / " -- text before is the product name + size block,
         text after (if present) is the Shopify variant (the customer's
         actual selected option).
      2. Try to pull known colors out of the variant block first
         (extract_varient); if that finds nothing, fall back to scanning
         the whole original string (extract_colors).
      3. Build the display product name (extract_display_text), then strip
         the size block off the front part and set item.size/item.prefix
         (get_size_and_prefix).
      4. Match the remaining text against helper.CATEGORY to set
         item.category (first match wins; None if nothing matches).

    Idempotent: always recomputes from item.original_order_string, which
    is never itself mutated here, so calling this twice on the same item
    produces the same result (see parse_order_item() note above).
    """

    item.colors = []
    parts = item.original_order_string.split(" / ")
    main = parts[0]
    if len(parts) > 1:
        item.variant_full = parts[1].strip()
    # variant usually contains the actual chosen color
    if item.variant_full:
        color_list = extract_varient(item.variant_full)
        if len(color_list):
            item.colors = color_list

    # fallback to full string
    if not item.colors:
        item.colors = extract_colors(item.original_order_string)

    item.display_text = extract_display_text(
        main,
        item.colors,
        item.variant_display
    )

    main = get_size_and_prefix(item, main)

    for cat in helper.CATEGORY:
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
    order_nums=None
):
    """
    Parses one CSV's worth of parallel column lists (each list index i is
    one row) into a Batch, isolating each row so one bad/malformed row
    can't take down the whole import.

    Per row:
      - blank Lineitem name -> skipped with a ParseEvent (no phantom item)
      - non-numeric/blank quantity -> defaults to 1, with a ParseEvent
      - missing/malformed order number or timestamp -> handled gracefully
        rather than raising
      - while debug_mode is False: rows at/before the last-processed
        timestamp are skipped, and the newest timestamp seen is saved as
        the new "last processed" marker once the whole batch finishes
      - any other unexpected error in a row -> caught, logged as a
        ParseEvent, and that row is skipped rather than aborting the batch

    Returns (batch, events) -- events is the list of ParseEvent warnings/
    errors collected along the way, for the GUI to display to the user.
    """

    batch = Batch()
    events = list()

    last_processed = config.load_last_processed_timestamp()
    debug_mode = config.get_debug_mode()

    newest_timestamp = None

    for i, text in enumerate(order_strings):

        row_order_num_raw = order_nums[i] if order_nums else None

        try:
            ts = ""
            if timestamps:
                ts = timestamps[i]

            # skip rows with no product name instead of creating a
            # phantom line item with an empty product name
            if not text or not text.strip():
                events.append(helper.ParseEvent(
                    level=1,
                    message="Skipping row with blank Lineitem name",
                    order_num=row_order_num_raw,
                    timestamp=ts
                ))
                continue

            order_num = None
            if order_nums:
                if row_order_num_raw and row_order_num_raw.startswith("#"):
                    order_num = row_order_num_raw[1:]

            quantity_raw = None
            if quantities:
                quantity_raw = quantities[i]

            try:
                quantity = int(quantity_raw) if quantity_raw else 1
            except (TypeError, ValueError):
                events.append(helper.ParseEvent(
                    level=1,
                    message=f"Non-numeric quantity {quantity_raw!r}, defaulting to 1",
                    order_num=row_order_num_raw,
                    timestamp=ts
                ))
                quantity = 1

            note = None
            if notes:
                note = notes[i]

            if ts and not debug_mode:

                current_dt = config.timestamp_to_datetime(ts)

                if current_dt is None:
                    events.append(helper.ParseEvent(
                        level=2,
                        message=f"Could not parse timestamp: {ts!r}",
                        order_num=row_order_num_raw,
                        timestamp=ts
                    ))
                else:
                    if last_processed and current_dt <= last_processed:
                        events.append(helper.ParseEvent(
                            level=1,
                            message=f"Skipping already processed order: {ts}",
                            order_num=row_order_num_raw,
                            timestamp=ts
                        ))

                        continue

                    if newest_timestamp is None or current_dt > newest_timestamp:
                        newest_timestamp = current_dt

            item = parse_order_item(
                    text=text,
                    time_stamp=ts,
                    quantity=quantity,
                    note=note,
                    order_num=order_num
                )

            if isinstance(item, Addon):
                batch.add_add_on(item)
            elif isinstance(item, OrderItem):
                batch.add_order(item)

        except Exception as exc:
            events.append(helper.ParseEvent(
                level=2,
                message=f"Skipping row due to unexpected error: {exc}",
                order_num=row_order_num_raw,
                timestamp=timestamps[i] if timestamps else None
            ))
            continue

    batch.__post_init__()
    # ----------------------------------------
    # save newest processed timestamp
    # ----------------------------------------

    if not debug_mode and newest_timestamp:
        config.set_last_processed_timestamp(
            newest_timestamp.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

    return batch, events
