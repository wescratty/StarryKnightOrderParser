"""
utility_modules/orderItem.py

Top-level CSV-import pipeline. Ties together utility_modules.models (the
Addon/OrderItem/Batch data model), utility_modules.addonParser (addon
classification), and utility_modules.orderParser (order item field
extraction) into the one entry point external callers use:

    from utility_modules import orderItem
    batch, events = orderItem.parse_orders(order_strings, timestamps, ...)

Pipeline, top to bottom:
  1. parse_orders()      -- one CSV's worth of parallel column lists -> one
                             Batch. Iterates every row, isolates failures
                             per-row, returns (Batch, events).
  2. parse_order_item()  -- one row -> one OrderItem or Addon.
  3. get_class()         -- decides OrderItem vs Addon by keyword match
                             ("wool insert", "big runner", "purse", ...),
                             then delegates to addonParser/orderParser to
                             build and fill in the object.

Two parallel object kinds come out of this:
  - OrderItem: a pair of shoes -- the thing being made.
  - Addon: an extra attached to an order -- wool insert, big runner
    (spare sole), purse, headband, or gift card. Rendered separately from
    OrderItems in the HTML report.
"""

import config
from utility_modules import helper
from utility_modules.models import Addon, OrderItem, Batch
from utility_modules.addonParser import get_add_on_item
from utility_modules.orderParser import get_order_item


# parse_orders()'s `archive` parameter (see its docstring) controls the
# "skip already-processed orders" behavior -- it's passed in by the caller
# (the GUI's Archive checkbox) rather than read from a persisted config
# file, so nothing here needs to know about the GUI at all.


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

    The wool insert marker is a special case: adult (Women's/Men's) and
    Big Kids shoe listings describe the bundled wool insert right in their
    own product name ("...Wool Insert included - W7 (foot measures...)"),
    which would otherwise false-positive against a plain "wool insert"
    substring check and get misclassified as an addon instead of a pair of
    shoes. What sets those apart is specifically the word "included" right
    after "wool insert" -- no real wool-insert *addon* line phrases it that
    way, whether it's the plain "Natural Wool Insert - Small" form or the
    "ADD//...Wool Insert//..." form (with or without "Natural"), so
    "wool insert included" is excluded rather than requiring any one
    prefix format.

    Returns a fully-populated Addon or OrderItem -- get_add_on_item()/
    get_order_item() run the corresponding field extraction before
    returning, so the result of this function never needs re-parsing.
    """

    lower = (text or "").lower()

    for marker in helper.AddMarkers:
        if marker == helper.AddMarkers.WOOL:
            matched = "wool insert" in lower and "wool insert included" not in lower
        else:
            matched = marker.value in lower

        if matched:
            return get_add_on_item(
                text=text,
                time_stamp=time_stamp,
                add_type=helper.ADDON_TYPE_MAP.get(marker.value, helper.AddonType.UNKNOWN),
                quantity=quantity,
                note=note,
                order_num=order_num,
            )

    return get_order_item(text, time_stamp, quantity=quantity, note=note, order_num=order_num)


def parse_order_item(
    text,
    time_stamp,
    quantity=None,
    note=None,
    order_num=None
):
    """
    Entry point used by parse_orders() for a single CSV row: classifies it
    via get_class() into a fully-populated Addon or OrderItem and returns
    it as-is.
    """

    return get_class(text, time_stamp, quantity, note, order_num)


# ----------------------------------------
# parse many orders
# ----------------------------------------

def parse_orders(
    order_strings,
    timestamps=None,
    quantities=None,
    notes=None,
    order_nums=None,
    archive=False
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
      - while `archive` is True: rows at/before the last-processed
        timestamp are skipped, and the newest timestamp seen is saved as
        the new "last processed" marker once the whole batch finishes --
        this mirrors the GUI's "Archive" checkbox (checked by default),
        which also moves the source CSV into INPUT_CSV/ARCHIVE (see
        StarryKnightOrderParser.load_csv()). Leave it False (the default
        here) to reprocess every order regardless of what's already been
        handled, e.g. for a one-off test/preview run.
      - any other unexpected error in a row -> caught, logged as a
        ParseEvent, and that row is skipped rather than aborting the batch

    Returns (batch, events) -- events is the list of ParseEvent warnings/
    errors collected along the way, for the GUI to display to the user.
    """

    batch = Batch()
    events = list()

    last_processed = config.load_last_processed_timestamp()

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

            if ts and archive:

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

    if archive and newest_timestamp:
        config.set_last_processed_timestamp(
            newest_timestamp.strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

    return batch, events
