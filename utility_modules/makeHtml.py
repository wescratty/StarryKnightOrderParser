"""
utility_modules/makeHtml.py

Renders a parsed Batch (see utility_modules.models) into the production
cut-sheet HTML report: a per-category shoe table, a leather/color-count
summary, an add-ons table, and a per-order checklist view. Writes the
result to OUTPUT_HTML/orders.html and opens it in the browser.
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
    A collection of Tables rendered as a grid of side-by-side HTML tables,
    splitting any table over max_rows into multiple same-titled tables
    (chop()) and laying tables out max_tables-per-row (get_grid_of_tables()).
    """

    title: str = ""
    max_rows: int = 18
    tables: list[Table] = field(default_factory=list)

    def add(self, table):
        self.tables.append(table)

    def chop(self, table: Table) -> list[Table]:
        if len(table.rows) <= self.max_rows:
            return [table]

        return [
            Table(
                title=f"{table.title}",
                columns=table.columns,
                rows=table.rows[i:i + self.max_rows],
            )
            for idx, i in enumerate(
                range(0, len(table.rows), self.max_rows)
            )
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
        html = [f"<h1>{table.title}</h1>", "<table>", "<tr>"]

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

    def chunk_tables(self, tables: list[Table], size: int = 5) -> list[list[Table]]:
        return [
            tables[i:i + size]
            for i in range(0, len(tables), size)
        ]

    def get_grid_of_tables(self, tables: list[Table], max_tables) -> str:
        if not tables:
            return ""

        html = []

        for group in self.chunk_tables(tables, max_tables):
            html.append(f"""
            <div style="
                display:grid;
                grid-template-columns: repeat({max_tables}, 1fr);
                gap:20px;
                margin-bottom:20px;
            ">
            """)

            for table in group:
                html.append(f"<div>{self.make_html_table(table)}</div>")

            html.append("</div>")

        html.append('<div class="page-break"></div>')

        return "".join(html)


# ----------------------------
# Generic Table builder
# ----------------------------

def build_order_list_html(batch: Batch) -> str:
    """Renders the per-order checklist view: one <li> per order, its shoes, and its add-ons."""

    html = "<div class='report-section'>"
    html += "<ul class='order-list'>"

    order_dict = batch.get_orders()

    for order_num, items in order_dict.items():
        html += f"<li>"
        html += f"<div class='order-header'>Order #{order_num}</div>"

        html += "<ul class='order-items'>"

        # Shoes / items
        for item in items:
            html += "<li class='order-item'>"
            html += f"<span class='item-text'>{item.original_order_string}</span>"

            if item.note:
                html += f"<div class='note'>📝 {item.note}</div>"

            html += "</li>"

        # Add-ons
        addons = batch.get_order_addon_items(order_num)
        if addons:
            html += "<li class='addons-section'>"
            html += "<div class='addon-header'>Add-ons</div>"
            html += "<ul class='addons'>"

            for addon in addons:
                html += "<li class='addon'>"
                html += f"<span>{addon.display_text} × {addon.quantity}</span>"

                if addon.note:
                    html += f"<div class='note'>📝 {addon.note}</div>"

                html += "</li>"

            html += "</ul>"
            html += "</li>"

        html += "</ul>"
        html += "</li>"

    html += "</ul>"
    html += "</div>"

    return html


def build_main_table_html(batch):
    """
    Builds the main "Shoes" report: one Table per category (see
    helper.CATEGORY), one row per order item, sorted by size. Each row's
    description is a collapsible <details> (see make_details_html())
    showing the piggybacked add-on summary and the full tooltip on
    expand/hover.

    When a category's table mixes toddler sizes with Big Kids/Men's/
    Women's ones, a full-width group-divider row (e.g. "Big Kids") is
    inserted right before that group starts, so the size jump is obvious
    at a glance instead of just a size number that looks out of place --
    per the owner's request. A single-tier table (the common case) gets no
    dividers at all, since there's nothing to distinguish.
    """

    report = Report("Shoes", max_rows=13)
    headers = batch.get_headers()
    for header in headers:
        cat_orders = batch.get_order_category(header)

        if len(cat_orders):
            table = Table(header, ["Size", "Description"])

            sorted_orders = sorted(cat_orders, key=sort_size)
            tiers_present = {get_size_tier(o)[0] for o in sorted_orders}
            last_tier = None

            for order in sorted_orders:
                tier, label, _number = get_size_tier(order)

                if len(tiers_present) > 1 and tier != last_tier:
                    table.add_divider(label or "Other")
                    last_tier = tier

                html = f"<div class='report-section'>"

                size = order.size
                display = order.get_display()

                add_ons = batch.get_order_addon_items(order_num=order.order_num)

                if len(add_ons):
                    for add in add_ons:
                        display = f"{add.get_order_piggyback_display()}{display}"

                tooltip = order.get_tool_tip(add_ons)

                size_html = f"""
                     <button class="order " ">
                        {size}
                    </button>
                """
                html += make_details_html(display, tooltip)
                html += "</div>"

                table.add([size_html, html])

            report.add(table=table)
    return report


def make_details_html(main_display, tooltip):
    """Wraps a row's display text and tooltip in a collapsible <details>/<summary> element."""

    size_html = f'''
                <details>
                    <summary>{main_display}</summary>
                    <pre>{tooltip}</pre>
                </details>
                '''
    return size_html


_SIZE_TIERS = {
    None: (0, "Toddler"),   # numeric toddler/baby sizes: 1, 2, 3...
    "Kids": (1, "Big Kids"),
    "M": (2, "Men's"),
    "W": (3, "Women's"),
}


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

    html += build_main_table_html(batch).make(4)

    html += '''<h2>Leather Order</h2>'''
    size_report = get_leather_order(orders)
    html += size_report.make(max_tables=5)

    add_report, addon_events = get_add_on_report(batch)
    user_notify_list.extend(addon_events)
    html += add_report.make(max_tables=2)

    html += build_order_list_html(batch)

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
    """Builds the add-ons Report (one Table per category/color grouping) and returns (report, events) -- events flags any order whose big runner size couldn't be inferred. Group-divider rows are inserted the same way as build_main_table_html() when a group (e.g. wool inserts) mixes toddler with Big Kids/Men's/Women's sizes."""

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

            if len(tiers_present) > 1 and tier != last_tier:
                table.add_divider(label or "Other")
                last_tier = tier

            size = 999
            if add.size:
                size = add.size
            table.add([add.order_num, size, add.get_display()])

        add_report.add(table)
    return add_report, events


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
                background-color: #dddddd;
            }}

            td {{
                min-width: 30px;
            }}

            /* Big Kids/Men's/Women's group-divider row -- see
               makeHtml.Table.add_divider() / _Divider */
            td.size-group {{
                background-color: #333333;
                color: #ffffff;
                font-weight: bold;
                text-align: center;
                padding: 4px 6px;
            }}

            tr.size-group-row {{
                break-inside: avoid;
                page-break-inside: avoid;
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

            li.has-note {{
                font-weight: bold;
                color: #0056b3;
                font-size: 14px;
            }}
            div.has-note {{
                font-weight: bold;
                color: #0056b3;
                font-size: 14px;
            }}

            /* =========================
               REPORT BLOCKS
            ========================== */

            .report-section {{
                break-inside: avoid;
                page-break-inside: avoid;
            }}

            /* =========================
               ORDER LIST VIEW
            ========================== */

            .order-list {{
                list-style: none;
                padding-left: 0;
                font-size: 11px;
            }}

            .order {{
                border: 1px solid #ddd;
                padding: 10px;
                margin-bottom: 0;
                border-radius: 6px;
                break-inside: avoid;
                page-break-inside: avoid;
                cursor: pointer;
                width: 100%;
                height: 25px;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            
            .order.active {{
                background: #ffff99;
            }}
            
            .order.active::after {{
                content: attr(data-tooltip);
                white-space: pre-wrap;
            
                position: absolute;
                top: 100%;
                left: 0;
            
                z-index: 1000;
            
                background: white;
                border: 1px solid black;
                padding: 8px;
                min-width: 250px;
            }}

            .order-header {{
                font-weight: bold;
                font-size: 14px;
                margin-bottom: 6px;
            }}

            .order-items {{
                list-style: none;
                padding-left: 10px;
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

            .order-item {{
                margin-bottom: 4px;
            }}

            .addons-section {{
                margin-top: 8px;
            }}

            .addon-header {{
                font-weight: bold;
                font-size: 13px;
                margin-top: 6px;
            }}

            .addons {{
                list-style: none;
                padding-left: 12px;
            }}

            .note {{
                font-weight: bold;
                color: #0056b3;
                font-size: 14px;
                margin-left: 10px;
            }}

            /* =========================
               PRINT RULES
            ========================== */

            @media print {{

                @page {{
                    size: landscape;
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
