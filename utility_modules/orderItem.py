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
    time_stamp: str
    order_num: Optional[str] = None
    note: Optional[str] = None

    addOns: List[Addon] = field(default_factory=list)
    orderItems: List[OrderItem] = field(default_factory=list)


@dataclass
class Batch:
    addOns_list: List[Addon] = field(default_factory=list)
    orders_list: List[OrderItem] = field(default_factory=list)
    orderItems: Dict[str, List[OrderItem]] = field(init=False, default_factory=dict)
    orderAddons: Dict[str, List[Addon]] = field(init=False, default_factory=dict)

    def __post_init__(self):
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
        return self.orderAddons.get(category, [])

    def get_order_notes(self) -> List[tuple[str, str]]:
        notes = []

        for items in self.orderItems.values():
            for item in items:
                if item.note:
                    notes.append((item.order_num, item.note))

        return notes

    def get_order_category(self, category: str) -> List[OrderItem]:
        orders = []

        for items in self.orderItems.values():
            for item in items:
                if item.category == category:
                    orders.append(item)

        return orders

    def get_addon_notes(self) -> List[tuple[str, str]]:
        notes = []

        for items in self.orderAddons.values():
            for item in items:
                if item.note:
                    notes.append((item.order_num, item.note))

        return notes

    def get_addon_categorized(self):
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
    order = OrderItem(
        time_stamp=time_stamp,
        original_order_string=text,
        quantity=quantity,
        note=note,
        order_num=order_num
    )

    return parse_order_item_data(order)


def get_add_on_item(text, time_stamp, add_type, quantity=None, note=None, order_num=None):
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
        if " - " in item.display_text:
            item.size = (
                item.display_text
                .split(" - ")[-1]
                .strip()
                .title()
            )

    elif item.add_type == helper.AddonType.SOLE:
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
        item.icon = "➕"
        item.add_type = helper.AddonType.UNKNOWN
        print("Missed one", item)


def get_color_end_hyphen(item):
    return item.display_text.split(" - ")[-1].strip().title()


def parse_gift_card(item, text):

    if "gift card" not in text.lower():
        return

    item.display_text = text
    item.add_type = helper.AddonType.GIFT
    item.category = "Gift Card"


def extract_big_runner_color(text):

    marker = "Big Runner"

    if marker not in text:
        return "None"

    color = text.split(marker)[0].strip()

    if not color:
        return "None"

    return color.title()


def extract_purse_color(text):

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

    item = get_class(text, time_stamp, quantity, note, order_num)
    if isinstance(item, Addon):
        return item

    return parse_order_item_data(item)


def parse_order_item_data(item):
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
