"""
utility_modules/models.py

The domain objects that make up a parsed CSV: Addon, OrderItem, and Batch
(the container that groups both by order number and feeds makeHtml.py).

See utility_modules/orderItem.py for how these get built from raw CSV rows
(parse_orders -> parse_order_item -> get_class), utility_modules/
addonParser.py for Addon-specific field extraction, and utility_modules/
orderParser.py for OrderItem-specific field extraction.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from collections import defaultdict
from utility_modules import helper


@dataclass()
class Addon:
    """
    An extra attached to an order, distinct from the shoes themselves:
    natural wool insert, big runner (spare/replacement sole), purse,
    headband, or gift card. Which one is decided by get_class() matching a
    keyword in helper.AddMarkers against the Shopify line item text.

    add_type drives most of the downstream behavior (icon, category,
    color/size extraction rules) -- see addonParser.classify_addon().
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
        own row (no product name -- just note/icon/color). Quantity is
        deliberately not shown here (or in OrderItem.get_display()) -- the
        owner found the "X<quantity>" suffix confusing on the cut sheet.
        """

        ret_str = f""
        if self.note:
            ret_str += f"📝"
        if self.icon:
            ret_str += f"{self.icon}"
        if self.color:
            ret_str += f"({self.color})"

        return ret_str


@dataclass
class OrderItem:
    """
    A pair of shoes from one Shopify line item -- the thing actually being
    produced. size/prefix/colors/product_name/display_text/category are
    populated by orderParser.parse_order_item_data() from the raw Shopify
    product string; variant_full holds the raw Shopify "variant" (the part
    of the product string after " / ") that extraction was drawn from.
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
    variant_full: Optional[str] = None
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
        original_order_string is set. No quantity suffix -- the owner found
        the "X<quantity>" notation confusing on the cut sheet, so quantity
        is tracked internally (self.quantity) but not rendered here.
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

    def get_order_category(self, category: str) -> List[OrderItem]:
        """All OrderItems whose category matches (used by makeHtml.py to build one table per category)."""

        orders = []

        for items in self.orderItems.values():
            for item in items:
                if item.category == category:
                    orders.append(item)

        return orders

    def get_addon_categorized(self):
        """
        Groups addons for the HTML report: by category normally, but by
        "<category> <color>" for big runners (SOLE) specifically, since tan
        and black big runners are cut/tracked separately. Gift cards are
        dropped entirely -- they're not a production item. Also triggers
        get_try_big_runner_size() as a side effect first, since that's what
        fills in add.size for big runners before they're grouped/displayed.

        Returns (addon_rows, events): events flags any order where the big
        runner size couldn't be confidently inferred, for the GUI to show.
        """

        add_ons = self.get_all_addon_items()
        addon_rows = defaultdict(list)
        events = self.get_try_big_runner_size()

        for add in add_ons:
            if add.add_type == helper.AddonType.GIFT:
                continue

            if add.add_type == helper.AddonType.SOLE:
                addon_rows[f"{add.category} {add.color}"].append(add)
            else:
                addon_rows[add.category].append(add)

        return addon_rows, events

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
        doesn't match order count), it leaves those addons' sizes unset
        rather than guessing wrong, and returns a ParseEvent for that order
        so the GUI can tell the user to fill it in by hand.

        Returns the list of such events (empty if every order with big
        runners could be sized unambiguously).
        """

        events = []
        all_orders_by_num = self.get_orders()
        order_nums = list(all_orders_by_num.keys())
        for order_num in order_nums:
            add_ons = self.get_order_addon_items(order_num)
            order_items = self.get_order_item(order_num)
            note = None
            for order in order_items:
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

            if len(order_items) == total_runners:
                if total_black_big_runners == 0 or total_tan_big_runners == 0:
                    size_list = [order.size for order in order_items]
                    idx = 0
                    for add in add_ons:
                        if add.add_type == helper.AddonType.SOLE:
                            add.size = size_list[idx]
                            idx += 1

            elif total_runners > 0:
                # order has big runners but the count doesn't line up
                # 1-to-1 with its shoe pairs -- can't safely guess which
                # runner goes with which pair, so leave their sizes unset
                events.append(helper.ParseEvent(
                    level=1,
                    message="Could not determine big runner size automatically -- please set manually",
                    order_num=order_num,
                ))

        return events
