import re
from collections import defaultdict
import webbrowser
import config
from utility_modules import helper
from utility_modules.orderItem import Batch
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Table:
    title: str
    columns: list[str]
    rows: list[list[Any]] = field(default_factory=list)

    def add(self, table):
        self.rows.append(table)


@dataclass
class Report:
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

def is_prefixed_size(size):
    if not size:
        return False

    return bool(
        re.fullmatch(
            r'(?:kids\s+|[WM])\d+(?:\.\d+)?',
            str(size).strip(),
            re.IGNORECASE
        )
    )


def get_adult_prefix(size):

    return str(size)[0].upper()


def get_adult_numeric_size(size):

    return float(str(size)[1:])


def clean_timestamp(ts):

    return ts.split(" -")[0]


def build_order_list_html(batch: Batch) -> str:
    html = "<div class='report-section'>"
    html += "<ul class='order-list'>"

    order_dict = batch.get_orders()

    for order_num, items in order_dict.items():
        html += f"<li class='order'>"
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


def row_has_data(size, headers, rows):
    return any(rows[size][header] for header in headers)


def build_table_html(rows, sorted_sizes, headers, batch):
    html = f"<div class=\"report-section\">"
    html += "<table>"
    html += "<tr>"
    html += "<th>Size</th>"

    for header in headers:
        html += f"<th>{header}</th>"

    html += "</tr>"

    for size in sorted_sizes:
        if not row_has_data(size, headers, rows):
            continue
        html += "<tr>"
        html += f"<td><b>{size}</b></td>"

        for header in headers:
            orders_in_cell = rows[size][header]
            html += "<td>"

            if orders_in_cell:
                html += "<ul>"

                for order in orders_in_cell:
                    display = order.get_display()
                    # if not display:
                    #     display = order.product_name

                    add_ons = batch.get_order_addon_items(order_num=order.order_num)
                    if len(add_ons):
                        for add in add_ons:
                            display = f"{add.get_order_piggyback_display()}{display}"

                    tooltip = order.get_tool_tip(add_ons)

                    note_class = (
                        "has-note"
                        if order.note
                        else ""
                    )

                    html += f'''
                    <li class="{note_class}" title="{tooltip}">
                        {display}
                    </li>
                    '''

                html += "</ul>"
            html += "</td>"
        html += "</tr>"
    html += "</table>"
    html += "</div>"
    html += """
    <div class="page-break"></div>
    """

    return html


def build_main_table_html(batch):
    report = Report("Shoes", max_rows=13)
    headers = batch.get_headers()
    for header in headers:
        cat_orders = batch.get_order_category(header)
        if len(cat_orders):
            table = Table(header, ["Size", "Description"])

            for order in sorted(cat_orders, key=sort_size):
                html = f"<div class='report-section'>"

                size = order.size

                display = order.get_display()

                add_ons = batch.get_order_addon_items(order_num=order.order_num)
                if len(add_ons):
                    for add in add_ons:
                        display = f"{add.get_order_piggyback_display()}{display}"

                tooltip = order.get_tool_tip(add_ons)

                note_class = (
                    "has-note"
                    if order.note
                    else ""
                )

                html += f'''
                <div class="{note_class}" title="{tooltip}">
                    {display}
                </div>
                '''
                html += "</div>"
                table.add([size, html])

            report.add(table=table)
    return report


def is_int(value):

    try:
        int(value)
        return True

    except (TypeError, ValueError):
        return False


def sort_size(add):
    if not add.size:
        return (99, 999)

    size = str(add.size).strip()

    match = re.match(
        r'(?:(kids)|([WM]))?\s*(\d+(?:\.\d+)?)$',
        size,
        re.IGNORECASE
    )

    if not match:
        return (99, 999)

    kids_prefix, wm_prefix, number = match.groups()

    if kids_prefix:
        prefix = "K"
    elif wm_prefix:
        prefix = wm_prefix.upper()
    else:
        prefix = ""

    prefix_order = {
        "": 0,   # numeric kids sizes: 1, 2, 3...
        "K": 0,  # explicit "kids 2.5"
        "M": 1,
        "W": 2,
    }

    return (
        prefix_order.get(prefix, 99),
        float(number)
    )


def export_orders_html(batch: Batch, filename="orders.html"):
    orders = batch.get_all_order_items()
    output_file = config.get_output_file(filename)

    user_notify_list = list()

    if not output_file:
        print("No output path configured.")
        return

    rows = defaultdict(lambda: defaultdict(list))
    adult_rows = defaultdict(lambda: defaultdict(list))

    for order in orders:

        category = order.category
        # category = helper.get_table_category(order)

        if not category:
            user_notify_list.append(helper.ParseEvent(
                    level=1,
                    message=f"Couldn't get category",
                    order_str=order.original_order_string,
                    order_num=order.original_order_string,
                    timestamp=order.time_stamp
                ))
            continue

        if is_prefixed_size(order.size):
            prefix = get_adult_prefix(order.size)
            size = get_adult_numeric_size(order.size)
            order.size_prefix = prefix
            rows[prefix + str(size)][category].append(order)

            adult_rows[prefix + str(size)][category].append(order)

        elif not is_int(order.size):
            user_notify_list.append(helper.ParseEvent(
                level=1,
                message=f"Couldn't get size",
                order_str=order.original_order_string,
                order_num=order.original_order_string,
                timestamp=order.time_stamp
            ))
            continue
        else:
            rows[str(order.size)][category].append(order)
    # ----------------------------------------
    # timestamp range
    # ----------------------------------------

    timestamps = [
        order.time_stamp
        for order in orders
        if order.time_stamp
    ]

    date_range_text = ""

    if timestamps:

        cleaned = [
            clean_timestamp(ts)
            for ts in timestamps
        ]

        start_ts = min(cleaned)
        end_ts = max(cleaned)

        date_range_text = f"{start_ts} - {end_ts}"

    # ----------------------------------------
    # html start
    # ----------------------------------------

    html = f"""
    <html>
    <head>

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
                padding: 8px;
                vertical-align: top;
            }}

            th {{
                background-color: #dddddd;
            }}

            td {{
                min-width: 60px;
            }}

            /* =========================
               LIST STYLES (TABLE CELLS)
            ========================== */

            ul {{
                margin: 0;
                padding-left: 18px;
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
                margin-bottom: 12px;
                border-radius: 6px;
                break-inside: avoid;
                page-break-inside: avoid;
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

    <body>

    <h1>Order Summary </h1>
    <h2> {date_range_text}</h2>

    """
    # sorted_sizes = sorted(rows.keys(), key=sort_key)

    # headers = batch.get_headers()
    # n = len(headers) // 3
    #
    # first = headers[:n]
    # second = headers[n:2 * n]
    # third = headers[2 * n:]
    # html += build_table_html(
    #     rows,
    #     sorted_sizes,
    #     first,
    #     batch
    # )
    #
    # html += build_table_html(
    #     rows,
    #     sorted_sizes,
    #     second,
    #     batch
    # )
    #
    # html += build_table_html(
    #     rows,
    #     sorted_sizes,
    #     third,
    #     batch
    # )

    html += build_main_table_html(batch).make(4)

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

    html += size_report.make(max_tables=5)

    add_ons_dict = batch.get_addon_categorized()
    add_report = Report(max_rows=15)

    for add_key in list(add_ons_dict.keys()):
        add_list = add_ons_dict[add_key]
        title = add_key
        columns = ["Size", "Description"]
        rows = []
        for add in sorted(add_list, key=sort_size):
            if add.size:
                rows.append([add.size, add.get_display()])
            else:
                rows.append([add.order_num, add.get_display()])

        add_report.add(Table(
            title=title,
            columns=columns,
            rows=rows
        ))

    html += add_report.make(max_tables=2)
    html += build_order_list_html(batch)
    html += """

    </body>
    </html>
    """
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
