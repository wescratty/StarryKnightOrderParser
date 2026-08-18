"""
utility_modules/orderParser.py

Builds and fills in OrderItem objects (a pair of shoes) from a CSV row not
identified as an addon by orderItem.get_class(): size/prefix, color,
display product name, and category.
"""

import re
import config
from utility_modules import helper
from utility_modules.models import OrderItem


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


def get_size_and_prefix(item, size_str):
    """
    Pulls the size block off the end of a product string and sets
    item.size / item.prefix from it, e.g. "Some Product - 10" -> size="10",
    or "Some Product - Kids 10" / "Some Product - W 8" -> a "Kids"/"W"/"M"
    prefix plus the numeric size. The prefix is normalized to exactly
    "Kids", "W", or "M" regardless of how it was typed/cased in the
    Shopify product string (e.g. "kids"/"KIDS"/"w"/"m" all normalize) --
    makeHtml.get_leather_order() does an exact-match check against these
    values, so an unnormalized prefix would silently miscategorize that
    order's leather counts.

    Returns size_str with the matched size block stripped off (or
    unchanged if no size pattern was found -- not every product line has
    one, e.g. addons or malformed product names).
    """

    size_match = re.search(
        r'-\s*(?:(kids)|([WM]))?\s*(\d+(?:\.\d+)?)',
        size_str,
        re.IGNORECASE
    )

    if size_match:
        kids_prefix, wm_prefix, size_number = size_match.groups()
        item.size = size_number
        raw_prefix = kids_prefix or wm_prefix
        item.prefix = "Kids" if raw_prefix and raw_prefix.lower() == "kids" else (raw_prefix.upper() if raw_prefix else None)
        size_str = size_str[:size_match.start()].strip()

    return size_str


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


def extract_display_text(main_text, colors=None):
    """
    Builds the human-readable product name shown in the report: strips
    "(...)" option lists, tokenizes to words, drops anything in
    config/ignore_words.txt (marketing filler like "Baby and Toddler") and
    -- if colors were already extracted separately -- drops color words
    too so they don't appear twice, then de-dupes while preserving first-
    seen order. If colors were found, they're prepended to the result.
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
    produces the same result.
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

    item.display_text = extract_display_text(main, item.colors)

    main = get_size_and_prefix(item, main)

    for cat in helper.CATEGORY:
        if cat.lower() in main.lower():
            item.category = cat
            break
    item.product_name = main
    return item
