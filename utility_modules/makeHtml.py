from collections import defaultdict
import webbrowser
import os
import config


TABLE_HEADERS = [
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
    "Scout",
]


def clean_timestamp(ts):

    return ts.split(" -")[0]

# ----------------------------------------
# category mapping
# ----------------------------------------


def get_table_category(order):

    if not order.product_name:
        return None

    name = order.product_name.lower()

    if "lotus" in name:
        return "Lotus"

    elif "t-strap" in name:
        return "T-strap"

    elif "rainey janes" in name:
        return "RAINEY Janes"

    elif "bella janes" in name:
        return "BELLA Jane"

    elif "sequoia" in name:
        return "SEQ"

    elif "sunrise" in name:
        return "SUN"

    elif "daisy" in name:
        return "Daisy"

    elif "moccs" in name:
        return "Moccs"

    elif "two tone" in name:
        return "Two tone"

    elif "loafer" in name or "loafers" in name:
        return "Loafers"

    elif "critters" in name:
        return "Critters"

    elif "designs" in name:
        return "Designs"

    elif "scout" in name:
        return "Scout"

    return None


# ----------------------------------------
# export html
# ----------------------------------------

def export_orders_html(orders, filename="orders.html"):
    output_file = config.get_output_file(filename)

    if not output_file:
        print("No output path configured.")
        return

    # rows[size][category] = list of order objects
    rows = defaultdict(lambda: defaultdict(list))

    # ----------------------------------------
    # collect data
    # ----------------------------------------

    for order in orders:

        if not order.size:
            continue

        category = get_table_category(order)

        if not category:
            continue

        rows[order.size][category].append(order)

    # ----------------------------------------
    # sort sizes numerically
    # ----------------------------------------

    sorted_sizes = sorted(rows.keys(), key=lambda x: int(x))

    timestamps = [
        order.timeStamp
        for order in orders
        if order.timeStamp
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
    # build html
    # ----------------------------------------

    html = f"""
    <html>
    <head>
        <title>Orders</title>

        <style>

            body {{
                font-family: Arial;
                padding: 20px;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
            }}

            th, td {{
                border: 1px solid black;
                padding: 8px;
                vertical-align: top;
            }}

            th {{
                background-color: #dddddd;
                position: sticky;
                top: 0;
            }}

            td {{
                min-width: 140px;
            }}

            ul {{
                margin: 0;
                padding-left: 18px;
            }}

            li {{
                margin-bottom: 4px;
                cursor: pointer;
            }}

            li:hover {{
                background-color: #f0f0f0;
            }}
            
    
            li.has-note {{
                font-weight: bold;
                color: #0056b3;
            }}

        </style>
    </head>

    <body>

    <h2>Order Summary {date_range_text}</h2>

    <table>
    """

    # ----------------------------------------
    # header row
    # ----------------------------------------

    html += "<tr>"
    html += "<th>Size</th>"

    for header in TABLE_HEADERS:
        html += f"<th>{header}</th>"

    html += "</tr>"

    # ----------------------------------------
    # rows
    # ----------------------------------------

    for size in sorted_sizes:

        html += "<tr>"

        html += f"<td><b>{size}</b></td>"

        for header in TABLE_HEADERS:

            orders_in_cell = rows[size][header]

            html += "<td>"

            if orders_in_cell:

                html += "<ul>"

                for order in orders_in_cell:
                    display = order.display_text

                    if not display:
                        display = order.product_name

                    # --------------------------
                    # quantity formatting
                    # --------------------------

                    qty = getattr(order, "quantity", None)

                    if qty and int(qty) > 1:
                        display = f"{display} ×{qty}"

                    # --------------------------
                    # tooltip (order verification)
                    # --------------------------

                    tooltip = f"""
                    Order {order.orderNum}
                    {order.original_order_string}
                    {order.note or ""}
                    """.strip()

                    tooltip = tooltip.replace('"', '&quot;')

                    note_class = "has-note" if order.note else ""

                    html += f'''
                    <li class="{note_class}" title="{tooltip}">
                        {display}
                    </li>
                    '''

                html += "</ul>"

            html += "</td>"

        html += "</tr>"

    html += """
    </table>

    </body>
    </html>
    """

    # ----------------------------------------
    # write file
    # ----------------------------------------

    with open(output_file, "w", encoding="utf-8") as f:

        f.write(html)

    # ----------------------------------------
    # open in browser
    # ----------------------------------------

    webbrowser.open(output_file.as_uri())
