"""
utility_modules/makeHtml.py

Renders a parsed Batch (see utility_modules.models) into the production
cut-sheet HTML report: a per-category shoe table, a by-size bottoms/sole
cutting summary, a leather/color-count summary, an add-ons table, and a
per-order checklist view. Writes the result to OUTPUT_HTML/orders.html
and opens it in the browser.
"""

import re
from collections import defaultdict
import webbrowser
import config
from utility_modules import helper
from utility_modules.models import Batch
from dataclasses import dataclass, field
from typing import Any


class _Divider:
    """A full-width group-label row (e.g. "Big Kids") inside a Table, rendered as its own <tr> spanning every column instead of one cell per column. See Table.add_divider()."""

    def __init__(self, label):
        self.label = label


@dataclass
class Table:
    """One HTML <table>: a title, column headers, and rows (each row a list of cell values, or a _Divider group label spanning the full row)."""

    title: str
    columns: list[str]
    rows: list[list[Any]] = field(default_factory=list)

    def add(self, row):
        self.rows.append(row)

    def add_divider(self, label):
        """Adds a full-width group-label row, e.g. to mark where Big Kids/Men's/Women's sizes start within an otherwise-toddler-sized table."""

        self.rows.append(_Divider(label))


@dataclass
class Report:
    """
    A collection of Tables rendered as side-by-side HTML tables, splitting
    any table over max_rows into multiple same-titled tables (chop()) and
    laying tables out max_tables columns wide (get_grid_of_tables()).

    Tables flow top-to-bottom within each column via CSS multi-column
    layout (column-count) rather than a fixed row-by-row grid, so a short
    table (e.g. a collection with only one or two orders) doesn't force
    a matching band of blank space next to it -- the next table just
    stacks underneath it in the same column instead. See
    get_grid_of_tables() and the .table-columns/.table-block CSS in
    get_preamble().
    """

    title: str = ""
    max_rows: int = 18
    tables: list[Table] = field(default_factory=list)

    def add(self, table):
        self.tables.append(table)

    def chop(self, table: Table) -> list[Table]:
        """
        Splits a table over max_rows into multiple same-titled chunks.
        Chunk size is recomputed from how many chunks are actually needed
        (ceil(rows / max_rows)), then rows are divided as evenly as
        possible across that many chunks -- rather than filling every
        chunk to max_rows and dumping whatever's left into a final
        chunk, which produced oddly small leftover tables (a 23-row
        table at max_rows=18 became an 18-row table plus a near-empty
        5-row one, both titled the same, sitting side by side in the
        print layout looking like a mistake). 23 rows now splits into a
        12-row and an 11-row chunk instead.
        """

        if len(table.rows) <= self.max_rows:
            return [table]

        num_chunks = -(-len(table.rows) // self.max_rows)  # ceil division
        chunk_size = -(-len(table.rows) // num_chunks)  # ceil division

        return [
            Table(
                title=f"{table.title}",
                columns=table.columns,
                rows=table.rows[i:i + chunk_size],
            )
            for i in range(0, len(table.rows), chunk_size)
        ]

    def make(self, max_tables=5) -> str:
        """
        Split oversized tables and return the final HTML report.
        """
        parsed_tables = []

        for table in self.tables:
            if len(table.rows):
                parsed_tables.extend(self.chop(table))

        return self.get_grid_of_tables(parsed_tables, max_tables)

    def make_html_table(self, table: Table) -> str:
        html = [f'<h1 class="table-title">{table.title}</h1>', "<table>", "<tr>"]

        # Header
        html.extend(f"<th>{column}</th>" for column in table.columns)
        html.append("</tr>")

        # Rows
        for row in table.rows:
            if isinstance(row, _Divider):
                html.append(
                    f'<tr class="size-group-row"><td class="size-group" colspan="{len(table.columns)}">{row.label}</td></tr>'
                )
                continue

            html.append("<tr>")
            html.extend(f"<td>{value}</td>" for value in row)
            html.append("</tr>")

        html.append("</table>")

        return "".join(html)

    def get_grid_of_tables(self, tables: list[Table], max_tables) -> str:
        """
        Lays every table out in a single max_tables-wide CSS multi-column
        block (column-count), instead of chunking tables into fixed rows
        of a grid. A fixed grid stretches every table in a row to match
        the tallest one in that same row, leaving a lot of blank space
        under a short table sitting next to a tall one; a CSS column
        instead just flows the next table in underneath a short one,
        within the same column, filling that space -- exactly the "stack
        another table below it" behavior asked for, without needing to
        hand-calculate table heights/row groupings in Python.

        The column count is capped at however many tables there actually
        are: asking for e.g. 5 columns when there are only 2 tables made
        the browser spread those 2 tables across a 5-column-wide area
        (column-fill balances height across every column whether or not
        it has content), which read as a lot of empty page -- capping it
        means a short report just gets as many columns as it has tables,
        instead of empty columns it never needed.
        """

        if not tables:
            return ""

        column_count = max(1, min(max_tables, len(tables)))

        html = [f'<div class="table-columns" style="column-count:{column_count};">']

        for table in tables:
            html.append(f'<div class="table-block">{self.make_html_table(table)}</div>')

        html.append("</div>")
        html.append('<div class="page-break"></div>')

        return "".join(html)

    def make_flat(self) -> str:
        """
        Renders the report as a run of same-width <table class="flat-
        table"> elements -- one per category, split again at each size-
        tier divider -- laid out so they read as one continuous flow with
        no visible gap between them, while each one keeps its own <thead>
        (category name + tier label + column headers) so that context
        reprints automatically if a print page break happens to land
        inside it (thead{{display:table-header-group}} in @media print).

        Two earlier versions of this method tried exactly this (split on
        the tier boundary, then split on the category boundary) and both
        left a visible gap of blank space between consecutive tables on a
        real print preview -- the owner flagged it and asked for one
        continuous table instead, which is what shipped for a while. That
        turned out to trade away *all* per-page context: a page break
        mid-category left the next page's rows under a bare "Size /
        Description / Order Details" header with no indication of which
        category or size tier they belonged to. Investigating the gap
        again (see the html_whitespace branch discussion), it traced back
        to generic CSS -- the sitewide `table {{ margin-bottom: 40px; }}`
        rule and default `table-layout: auto` -- rather than to using
        separate <table> elements as such. `.flat-table` below zeroes the
        margin and fixes each table's column widths (matching <colgroup>s
        across every table), which removes the gap while keeping the
        native per-table <thead> repeat. Chrome's print engine was
        confirmed (via a throwaway prototype) to have no support for CSS
        Paged Media running headers (@page margin-box `string-set`/
        `content: string()`), so splitting into same-width tables is the
        only way to get repeat-on-break context without a JS polyfill
        like Paged.js.

        This intentionally doesn't chop()/grid-layout tables the way
        make() does: a flowing single column paginates on its own in
        print, so there's no leftover-column whitespace to solve for.
        """

        tables_with_rows = [table for table in self.tables if table.rows]
        if not tables_with_rows:
            return ""

        columns = tables_with_rows[0].columns
        colgroup = "<colgroup>" + "".join(
            f'<col class="col-{idx}">' for idx in range(len(columns))
        ) + "</colgroup>"

        html = []
        for table in tables_with_rows:
            for tier_table in self._split_by_tier(table):
                html.append(self._make_flat_table_html(tier_table, colgroup, columns))

        html.append('<div class="page-break"></div>')

        return "".join(html)

    @staticmethod
    def _split_by_tier(table: Table) -> list[Table]:
        """
        Splits one category Table into same-titled sub-tables at each
        _Divider (tier boundary) it contains, dropping the _Divider rows
        themselves -- the tier label they carried becomes that sub-
        table's own title/subtitle instead of an in-body row. A table
        with no dividers (the common toddler-only case) comes back as a
        single-element list unchanged.
        """

        segments: list[Table] = []
        current_label = None
        current_rows: list[Any] = []

        def flush():
            if current_rows:
                segments.append(Table(title=table.title, columns=table.columns, rows=list(current_rows)))
                segments[-1].tier_label = current_label

        for row in table.rows:
            if isinstance(row, _Divider):
                flush()
                current_rows.clear()
                current_label = row.label
                continue
            current_rows.append(row)
        flush()

        if not segments:
            segments = [table]
            segments[0].tier_label = None

        return segments

    @staticmethod
    def _make_flat_table_html(table: Table, colgroup: str, columns: list[str]) -> str:
        subtitle = getattr(table, "tier_label", None)

        html = [f'<table class="flat-table">', colgroup, "<thead>"]
        html.append(
            f'<tr class="category-group-row"><td class="category-group" colspan="{len(columns)}">{table.title}</td></tr>'
        )
        if subtitle:
            html.append(
                f'<tr class="size-group-row"><td class="size-group" colspan="{len(columns)}">{subtitle}</td></tr>'
            )
        html.append("<tr>")
        html.extend(f"<th>{column}</th>" for column in columns)
        html.append("</tr>")
        html.append("</thead>")

        html.append("<tbody>")
        for row in table.rows:
            html.append("<tr>")
            html.extend(f"<td>{value}</td>" for value in row)
            html.append("</tr>")
        html.append("</tbody>")
        html.append("</table>")

        return "".join(html)


# ----------------------------
# Generic Table builder
# ----------------------------

def build_main_table_html(batch):
    """
    Builds the main "Shoes" report: one Table per category (see
    helper.CATEGORY), one row per order item, sorted by size, rendered
    flat via Report.make_flat() -- Size | Description | Order Details,
    with the order number, full raw Shopify product string, and any note
    always visible in their own column instead of tucked behind a
    collapsible <details>/hover. That collapsible version worked fine on
    screen, but printed to paper it silently vanished: Chrome prints a
    <details> in its default closed state, so every gift note and full
    order string was invisible on the printed cut sheet without anyone
    realizing it. Order Details reuses OrderItem.get_tool_tip(), the same
    "Order {{num}}\\n{{product string}}\\n{{note}}\\n{{addon lines}}" text
    the old hover tooltip already showed -- nothing new to compute, just
    no longer hidden. This also makes the separate per-order checklist
    view (the old build_order_list_html()) redundant, since every order's
    full text is now sitting right here -- see export_orders_html().

    When a category's table mixes toddler sizes with Big Kids/Men's/
    Women's ones, a full-width group-divider row (e.g. "Big Kids") is
    inserted right before that group starts, so the size jump is obvious
    at a glance instead of just a size number that looks out of place --
    per the owner's request. A toddler-only table (the common case) gets
    no dividers at all, since there's nothing to distinguish. A table
    that's entirely Big Kids/Men's/Women's (no toddler sizes at all)
    still gets its one divider up front, though -- without it the sizes
    alone look just like toddler sizes and get mistaken for them. See
    _should_show_divider(). Report.make_flat() turns each tier divider
    into its own same-titled sub-table (rather than an in-body row), so
    both the category name and the tier label sit in that sub-table's own
    <thead> and repeat on a print page break -- see its docstring for why.
    """

    report = Report("Shoes", max_rows=13)
    headers = batch.get_headers()
    for header in headers:
        cat_orders = batch.get_order_category(header)

        if len(cat_orders):
            table = Table(header, ["Size", "Description", "Order Details"])

            sorted_orders = sorted(cat_orders, key=sort_size)
            tiers_present = {get_size_tier(o)[0] for o in sorted_orders}
            last_tier = None

            for order in sorted_orders:
                tier, label, _number = get_size_tier(order)

                if _should_show_divider(tier, last_tier, tiers_present):
                    table.add_divider(label or "Other")
                    last_tier = tier

                size = order.size
                display = order.get_display()

                add_ons = batch.get_order_addon_items(order_num=order.order_num)

                # Only WOOL/SOLE addons piggyback onto a shoe row -- those
                # literally attach to a specific pair, so showing them
                # inline on that pair's row makes sense. PURSE/HEADBAND/
                # GIFT are standalone accessory items with their own
                # report table; they just happen to share an order number
                # with an unrelated shoe purchase, so piggybacking them
                # here would incorrectly stamp e.g. a purse's info onto a
                # completely different shoe in the same order.
                piggyback_types = (helper.AddonType.WOOL, helper.AddonType.SOLE)

                if len(add_ons):
                    for add in add_ons:
                        if add.add_type in piggyback_types:
                            display = f"{add.get_order_piggyback_display()}{display}"

                # get_tool_tip() keeps its blank-line paragraph breaks
                # for the note text as typed (handy in a hover tooltip),
                # but stacked in an always-visible column that eats a lot
                # of vertical room -- collapsed to one flowing, wrapped
                # line here instead, per the owner's request.
                tooltip = " ".join(order.get_tool_tip(add_ons).split())

                size_html = f"""
                     <button class="order " ">
                        {size}
                    </button>
                """
                display_html = f'<span class="display-text">{display}</span>'
                details_html = f'<span class="order-details">{tooltip}</span>'

                table.add([size_html, display_html, details_html])

            report.add(table=table)
    return report


_SIZE_TIERS = {
    None: (0, "Toddler"),   # numeric toddler/baby sizes: 1, 2, 3...
    "Kids": (1, "Big Kids"),
    "M": (2, "Men's"),
    "W": (3, "Women's"),
}

# Tiers that always get their own divider row, even when a table happens
# to contain only that one tier -- otherwise a Big Kids/Men's/Women's-only
# table shows no header at all, and since the size number alone looks
# just like a toddler size, the owner has mistaken an all-adult table for
# a toddler one. Toddler (0) and "no size at all" (99) are deliberately
# left out -- a toddler-only table is the common case and needs no
# header, and a lone unparseable size isn't a tier worth always labeling.
_ALWAYS_LABEL_TIERS = {1, 2, 3}


def _should_show_divider(tier, last_tier, tiers_present):
    """
    Shared divider-insertion rule for build_main_table_html() and
    get_add_on_report(): show a divider when the tier just changed, and
    either the table mixes more than one tier, or this tier is always
    labeled regardless (see _ALWAYS_LABEL_TIERS).
    """

    if tier == last_tier:
        return False

    return len(tiers_present) > 1 or tier in _ALWAYS_LABEL_TIERS


def get_size_tier(item):
    """
    Classifies an OrderItem/Addon's size into (tier, label, number):
    tier/label are one of _SIZE_TIERS' (index, name) pairs -- (99, None)
    if there's no size or it doesn't match the expected pattern -- and
    number is the parsed numeric size (None if there wasn't one to parse).

    OrderItem.prefix is already normalized to exactly None/"Kids"/"W"/"M"
    by orderParser.get_size_and_prefix(), so it's used directly here when
    present. Addon objects don't populate .prefix -- their WOOL size text
    (e.g. "Kids 2.5", "Womens 9") still carries the prefix word embedded
    in the size string itself, so those fall back to parsing it out the
    same way get_size_and_prefix() does.

    Used both for sort_size() (the tier index) and for the "Big Kids"/
    "Men's"/"Women's" group-divider rows build_main_table_html() and
    get_add_on_report() insert into each table, so a size only ever needs
    classifying in one place.
    """

    if not item.size:
        return 99, None, None

    size = str(item.size).strip()
    explicit_prefix = getattr(item, "prefix", None)

    if explicit_prefix:
        number_match = re.match(r'(\d+(?:\.\d+)?)$', size)
        number = float(number_match.group(1)) if number_match else None
        tier, label = _SIZE_TIERS.get(explicit_prefix, (99, None))
        return tier, label, number

    match = re.match(
        r'(?:(kids)|(wom[ae]ns?|m[ae]ns?|[WM]))?\s*(\d+(?:\.\d+)?)$',
        size,
        re.IGNORECASE
    )

    if not match:
        return 99, None, None

    kids_prefix, adult_prefix, number = match.groups()

    if kids_prefix:
        prefix = "Kids"
    elif adult_prefix:
        prefix = "W" if adult_prefix[0].lower() == "w" else "M"
    else:
        prefix = None

    tier, label = _SIZE_TIERS.get(prefix, (99, None))
    return tier, label, float(number)


def sort_size(item):
    """
    Sort key for shoe/addon sizes. Regular numeric baby/toddler sizes sort
    first (tier 0, by number); Big Kids, then men's, then women's sizes
    all sort into their own tiers *after* every toddler size, rather than
    being interleaved with them by raw number -- per the owner's request,
    since adult/Big Kids sizes aren't small and are hard to spot when
    scattered through the toddler range. Anything with no size, or a size
    that doesn't match the expected pattern, sorts last of all. See
    get_size_tier() for the actual tier/number classification.
    """

    tier, _label, number = get_size_tier(item)

    if number is None:
        return 99, 999

    return tier, number


def export_orders_html(batch: Batch, filename="orders.html"):
    """
    Renders the full HTML report for a Batch and writes it to
    OUTPUT_HTML/<filename>, then opens it in the browser. Returns a list
    of ParseEvent warnings collected while building the report (currently
    just "couldn't infer big runner size" cases from get_add_on_report) --
    empty list if there's nothing to flag, so callers can always safely
    iterate the result.
    """

    orders = batch.get_all_order_items()
    output_file = config.get_output_file(filename)

    user_notify_list = list()

    if not output_file:
        user_notify_list.append(helper.ParseEvent(
            level=2,
            message="No output path configured -- set a workspace directory first.",
        ))
        return user_notify_list

    date_range_text = get_date_range(orders)

    # ----------------------------------------
    # html start
    # ----------------------------------------

    html = get_preamble(date_range_text)

    html += build_main_table_html(batch).make_flat()

    html += '''<h2>Bottoms</h2>'''
    bottoms_report = get_bottoms_report(orders)
    html += bottoms_report.make(max_tables=2)

    html += '''<h2>Leather Order</h2>'''
    size_report = get_leather_order(orders)
    html += size_report.make(max_tables=3)

    add_report, addon_events = get_add_on_report(batch)
    user_notify_list.extend(addon_events)
    html += add_report.make(max_tables=2)

    html += """</body></html>"""

    # ----------------------------------------
    # write file
    # ----------------------------------------

    with open(output_file, "w", encoding="utf-8") as f:

        f.write(html)

    # ----------------------------------------
    # open browser
    # ----------------------------------------

    webbrowser.open(output_file.as_uri())
    return user_notify_list


def get_date_range(orders):
    """Returns "<earliest> - <latest>" across every order's timestamp, or "" if none have one."""

    timestamps = [
        order.time_stamp
        for order in orders
        if order.time_stamp
    ]

    date_range_text = ""
    if timestamps:
        cleaned = [
            config.clean_timestamp(ts)
            for ts in timestamps
        ]

        start_ts = min(cleaned)
        end_ts = max(cleaned)

        date_range_text = f"{start_ts} - {end_ts}"
    return date_range_text


def get_add_on_report(batch):
    """Builds the add-ons Report (one Table per category/color grouping) and returns (report, events) -- events flags any order whose big runner size couldn't be inferred. Group-divider rows are inserted the same way as build_main_table_html() -- see _should_show_divider()."""

    add_ons_dict, events = batch.get_addon_categorized()
    add_report = Report(max_rows=15)
    for add_key in list(add_ons_dict.keys()):
        add_list = add_ons_dict[add_key]
        title = add_key
        columns = ["Order Number", "Size", "Description"]

        sorted_adds = sorted(add_list, key=sort_size)
        tiers_present = {get_size_tier(a)[0] for a in sorted_adds}
        last_tier = None

        table = Table(title=title, columns=columns)
        for add in sorted_adds:
            tier, label, _number = get_size_tier(add)

            if _should_show_divider(tier, last_tier, tiers_present):
                table.add_divider(label or "Other")
                last_tier = tier

            size = 999
            if add.size:
                size = add.size
            table.add([add.order_num, size, add.get_display()])

        add_report.add(table)
    return add_report, events


def _bottom_size_label(order):
    """
    Label for one row of the "Bottoms" table (see get_bottoms_report()):
    the bare size for a plain toddler size ("3", matching what's shown on
    that order's own size button), or "<tier> <size>" for a Big Kids/
    Men's/Women's size ("Big Kids 2.5", "Men's 10.5", "Women's 9") so
    those don't collide with a same-numbered toddler size in the same
    table. "Unknown" for an item with no usable size at all.
    """

    if not order.size:
        return "Unknown"

    tier, tier_label, _number = get_size_tier(order)

    if tier_label and tier != 0:
        return f"{tier_label} {order.size}"

    return str(order.size)


def get_bottoms_report(orders):
    """
    Builds the "Bottoms" table: total pairs needed per size across every
    category and color combined. The bottom/sole leather is cut the same
    color regardless of the shoe's own color, so this lets the owner cut
    the whole order's bottoms in one batch by size instead of hunting
    across every category's table. Sorted the same way as sort_size()
    (toddler sizes ascending, then Big Kids, then Men's, then Women's),
    with a bolded Total row at the end.
    """

    counts = defaultdict(int)
    sample_order_for_label = {}

    for order in orders:
        label = _bottom_size_label(order)
        counts[label] += order.quantity or 0

        # keep one representative item per label so sort_size() has
        # something real to sort by
        if label not in sample_order_for_label:
            sample_order_for_label[label] = order

    table = Table("Bottoms", ["Size", "Qty"])

    sorted_labels = sorted(
        counts.keys(),
        key=lambda label: sort_size(sample_order_for_label[label])
    )

    total = 0
    for label in sorted_labels:
        qty = counts[label]
        total += qty
        table.add([label, qty])

    table.add(["<b>Total</b>", f"<b>{total}</b>"])

    bottoms_report = Report()
    bottoms_report.add(table)
    return bottoms_report


def get_leather_order(orders):
    """
    Builds the "Leather Order" report: total quantity needed per color,
    split into Toddler / Kids / Adult tables by order.prefix (normalized
    by orderParser.get_size_and_prefix() to exactly "Kids"/"M"/"W" so this
    exact-match check is reliable regardless of how the size was typed in
    Shopify). Orders with no prefix (plain numeric toddler sizes) fall
    into the Toddler bucket.
    """

    small_sizes = defaultdict(int)
    kid_sizes = defaultdict(int)
    adult_sizes = defaultdict(int)
    prefixes = ['M', 'W', 'Kids']
    for order in orders:
        if order.prefix in prefixes:
            if order.prefix == 'M' or order.prefix == 'W':
                for color in order.colors:
                    adult_sizes[color] += order.quantity

            if order.prefix == 'Kids':
                for color in order.colors:
                    kid_sizes[color] += order.quantity
        else:
            for color in order.colors:
                small_sizes[color] += order.quantity
    size_report = Report()
    toddler_table = Table(title="Toddler", columns=["Color", "Qty"])
    kids_table = Table(title="Kids", columns=["Color", "Qty"])
    adult_table = Table(title="Adult", columns=["Color", "Qty"])
    for color in list(small_sizes.keys()):
        qty = small_sizes[color]
        clr = color
        toddler_table.add([clr, qty])
    for color in list(kid_sizes.keys()):
        qty = kid_sizes[color]
        clr = color
        kids_table.add([clr, qty])
    for color in list(adult_sizes.keys()):
        qty = adult_sizes[color]
        clr = color
        adult_table.add([clr, qty])
    size_report.add(toddler_table)
    size_report.add(kids_table)
    size_report.add(adult_table)
    return size_report


def get_preamble(date_range_text):
    """
    The report's <html><head> block: inline CSS (print + screen styles)
    and a small click-to-cycle-color script for the order buttons
    (none -> yellow -> green -> red -> gray, used to mark progress by
    hand while cutting). Everything up through the opening <body><h1>.
    """

    return f"""
    <html>
    <head>
    <meta charset="UTF-8">

        <title>Orders</title>

        <style>

            /* =========================
               BASE LAYOUT
            ========================== */

            body {{
                transform: scale(0.95);
                transform-origin: top left;
                font-family: Arial;
                padding: 20px;
            }}

            h2 {{
                margin-top: 40px;
            }}

            /* =========================
               TABLE STYLES
            ========================== */

            table {{
                font-size: 12px;
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 40px;
            }}

            th, td {{
                border: 1px solid black;
                padding: 6px;
                vertical-align: top;
            }}

            th {{
                background-color: #D3D3D3;
            }}

            td {{
                min-width: 30px;
            }}

            /* Big Kids/Men's/Women's group-divider row -- see
               makeHtml.Table.add_divider() / _Divider */
            td.size-group {{
                background-color: #D3D3D3;
                color: #000000;
                font-weight: bold;
                text-align: center;
                padding: 4px 6px;
            }}

            tr.size-group-row {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            /* =========================
               FLAT SHOES TABLE
               (see Report.make_flat() / build_main_table_html())
            ========================== */

            /* One <table class="flat-table"> per category (split again
               per size tier) instead of one continuous table, so each
               one's own <thead> -- category name, tier label, column
               headers -- reprints via thead{{display:table-header-group}}
               (below, in @media print) if a page break lands inside it.
               table-layout:fixed + the shared <colgroup> below keeps
               every table's column widths identical, and margin:0
               overrides the sitewide `table {{ margin-bottom: 40px; }}`
               rule -- between them, consecutive tables read as one
               continuous flow with no visible gap, which is what
               actually caused the gap the owner flagged in the two
               earlier attempts at this (not the use of separate <table>
               elements itself). */
            table.flat-table {{
                table-layout: fixed;
                margin: 0;
            }}

            table.flat-table col.col-0 {{
                width: 8%;
            }}

            table.flat-table col.col-1 {{
                width: 22%;
            }}

            table.flat-table col.col-2 {{
                width: 70%;
            }}

            /* category name -- its own row inside each flat-table's
               <thead>, so it repeats on a print page break */
            tr.category-group-row {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            td.category-group {{
                background-color: #ffffff;
                border: none;
                text-align: left;
                font-size: 16px;
                font-weight: bold;
                padding: 14px 0 0 0;
            }}

            /* order number/raw product string/note -- always visible now
               instead of behind a <details> click/hover, which printed
               to paper as permanently closed and invisible */
            span.order-details {{
                display: block;
                word-break: break-word;
                font-family: Arial, sans-serif;
                font-size: 9px;
                margin: 0;
            }}

            /* =========================
               TABLE COLUMN LAYOUT
               (see Report.get_grid_of_tables())
            ========================== */

            /* column-fill:auto instead of the default "balance" -- with
               balance, the browser stretches content to fill every
               column evenly by height even when only 1-2 columns
               actually have tables in them, which is what made a short
               report (e.g. Bottoms with just 2 table-blocks) look like a
               lot of empty page. auto just fills column 1 top-to-bottom
               before starting column 2, and get_grid_of_tables() now
               also caps column-count at however many tables there are,
               so a short report doesn't reserve columns it'll never use. */
            .table-columns {{
                column-gap: 20px;
                column-fill: auto;
                margin-bottom: 20px;
            }}

            .table-block {{
                break-inside: avoid;
                page-break-inside: avoid;
                -webkit-column-break-inside: avoid;
                margin-bottom: 20px;
            }}

            /* per-table title inside get_grid_of_tables() (Bottoms/
               Leather Order/Add-ons) -- explicitly sized to match the
               Shoes report's category-group text (16px) instead of
               relying on the browser's default <h1> size (~2em), which
               read as oversized next to the compact tables around it */
            h1.table-title {{
                font-size: 16px;
                margin: 20px 0 6px 0;
            }}

            /* =========================
               LIST STYLES (TABLE CELLS)
            ========================== */

            ul {{
                margin: 0;
                padding-left: 12px;
            }}

            li {{
                margin-bottom: 4px;
            }}

            /* only apply hover in interactive (non-print) mode */
            li:hover {{
                background-color: #f0f0f0;
            }}

            /* =========================
               CUT-PROGRESS MARKER BUTTON
               (the clickable size button on each Shoes row -- see the
               click-to-cycle-color <script> in get_preamble())
            ========================== */

            .order {{
                border: 1px solid #ddd;
                padding: 3px 6px;
                margin-bottom: 0;
                border-radius: 6px;
                break-inside: avoid;
                page-break-inside: avoid;
                cursor: pointer;
                width: 100%;
                height: 16px;
                box-sizing: border-box;
                display: flex;
                align-items: center;
                justify-content: center;
            }}

            .order.red {{
                background-color: #ff9999;
            }}
            .order.yellow {{
                background-color: #FFBF00;
            }}

            .order.gray {{
                background-color: #d3d3d3;
            }}

            .order.green {{
                background-color: #90ee90;
            }}

            /* =========================
               PRINT RULES
            ========================== */

            @media print {{

                @page {{
                    size: portrait;
                    margin: 0.5in;
                }}

                thead {{
                    display: table-header-group;
                }}

                .page-break {{
                    break-before: page;
                    page-break-before: always;
                }}
                
                    
                /* safer than page-breaking full tables */
                tr {{
                    page-break-inside: avoid;
                }}

                /* disable hover effects in print */
                li:hover {{
                    background-color: transparent;
                }}
            }}

        </style>
    </head>
        <script>
            const colors = ["", "yellow", "green", "red", "gray"];

            document.addEventListener("click", function(e) {{
                const order = e.target.closest(".order");
            
                if (!order) return;
            
                let index = parseInt(order.dataset.color || "0");
            
                order.classList.remove("red", "gray", "green", "yellow");
            
                index = (index + 1) % colors.length;
            
                if (colors[index]) {{
                    order.classList.add(colors[index]);
                }}
            
                order.dataset.color = index;
            }});
        </script>

    <body>
    <h1>Order Summary {date_range_text}</h1>
    """
