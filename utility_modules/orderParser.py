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
    prefix plus the numeric size. Adult sizes are sometimes spelled out in
    full in the Shopify product string instead of abbreviated -- "Men 10.5"
    or "Women 9"/"Womens 9" work the same as "M 10.5"/"W 9". The prefix is
    always normalized down to exactly "Kids", "W", or "M" regardless of how
    it was typed/cased in the source string (e.g. "kids"/"KIDS", "w"/"W",
    "Men"/"mens"/"M" all normalize) -- makeHtml.get_leather_order() does an
    exact-match check against these values, so an unnormalized prefix
    would silently miscategorize that order's leather counts (this is what
    caused adult "Men"/"Women" sizes to fall into the wrong bucket, or not
    parse at all, before this was added).

    Returns size_str with the matched size block stripped off (or
    unchanged if no size pattern was found -- not every product line has
    one, e.g. addons or malformed product names).
    """

    size_match = re.search(
        r'-\s*(?:(kids)|(wom[ae]ns?|m[ae]ns?|[WM]))?\s*(\d+(?:\.\d+)?)',
        size_str,
        re.IGNORECASE
    )

    if size_match:
        kids_prefix, adult_prefix, size_number = size_match.groups()
        item.size = size_number

        if kids_prefix:
            item.prefix = "Kids"
        elif adult_prefix:
            item.prefix = "W" if adult_prefix[0].lower() == "w" else "M"
        else:
            item.prefix = None

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


def extract_display_text(main_text, colors=None, category=None):
    """
    Builds the human-readable product name shown in the report: strips
    "(...)" option lists and possessive "'s" markers (so "Men's"/"Women's"
    reduce to "Men"/"Women" before the next step drops them as filler
    rather than leaving a stray "s"), tokenizes to words, drops anything
    in config/ignore_words.txt (marketing filler like "Baby and Toddler")
    and -- if colors were already extracted separately -- drops color
    words too so they don't appear twice, then de-dupes while preserving
    first-seen order. If colors were found, they're prepended to the
    result.

    A COLLECTION_NAME_WORDS word (see helper.py) is only dropped when it
    matches the item's own `category` (helper.CATEGORY_DISPLAY_STRIP) --
    already redundant with that category's own table/section header.
    When it doesn't match, it's kept instead of blanket-filtered, since
    it's most likely a print/pattern name that happens to collide with a
    different collection's keyword (e.g. a "Daisy" print on a Mary Janes
    shoe -- category ends up "Mary", but "Daisy" is the one piece of real
    information in the name, not boilerplate).

    IMPORTANT: call this with `main_text` already stripped of its size
    block (i.e. after get_size_and_prefix()) -- an un-stripped size block
    can itself contain a prefix word ("Big Kids ... - kids 3") that would
    otherwise leak into the display text.
    """

    got_colors = get_colors()
    got_ignore = get_ignore_words()
    category_words = helper.CATEGORY_DISPLAY_STRIP.get(category, set())

    left = main_text

    # normalize separators
    left = left.replace("//", " ")

    # "Men's"/"Women's" -> "Men"/"Women" (otherwise the bare "s" left over
    # from the apostrophe survives filtering as its own stray word)
    left = re.sub(r"'s\b", "", left)

    # remove (...) option lists entirely
    left = re.sub(r"\(.*?\)", "", left)

    # tokenize
    words = re.findall(r"[A-Za-z]+", left)

    filtered = []

    for word in words:
        lower = word.lower()

        if lower in helper.COLLECTION_NAME_WORDS:
            if lower in category_words:
                continue  # redundant with this item's own category
            # else: a distinguishing print/collection name from a
            # different collection -- fall through and keep it, same as
            # any other non-ignored word below.
        elif lower in got_ignore:
            continue

        if colors and lower in got_colors:
            continue

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

    main = get_size_and_prefix(item, main)

    for cat in helper.CATEGORY:
        if cat.lower() in main.lower():
            item.category = cat
            break

    item.display_text = extract_display_text(main, item.colors, item.category)
    item.product_name = main
    return item
