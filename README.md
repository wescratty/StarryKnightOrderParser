# StarryKnightOrderParser

A small desktop tool that turns a Shopify `orders_export.csv` into a printable/touch-friendly
HTML production cut sheet for a handmade shoe business. It groups line items by order,
separates add-ons (wool inserts, big runners, purses, headbands, gift cards) from the shoes
themselves, extracts size/color/variant info from the product name, and writes out a
categorized HTML report.

## What it does

1. You export orders from Shopify as CSV and drop the file in `INPUT_CSV/ACTIVE`.
2. The app (a small Tkinter GUI) parses the CSV, turning each row into either an `OrderItem`
   (a shoe) or an `Addon` (wool insert / big runner / purse / headband / gift card), grouped
   by order number.
3. It extracts size, color/variant, and product category from the Shopify product name using
   the conventions in [`product_naming_spec.md`](product_naming_spec.md).
4. It writes a categorized HTML report to `OUTPUT_HTML/orders.html` and opens it in your
   browser.
5. The processed CSV is moved from `INPUT_CSV/ACTIVE` to `INPUT_CSV/ARCHIVE` so you don't
   reprocess it by accident.

## Getting started

**Requirements:** Python 3.9+ with Tkinter (bundled with the standard python.org installer
on Windows/macOS).

```
python StarryKnightOrderParser.py
```

On first run, the app will ask you to pick a workspace folder. It creates the following
structure there automatically:

```
<workspace>/
  config/              # colors.txt, ignore_words.txt, processed_orders.txt, debug_mode.txt
  INPUT_CSV/
    ACTIVE/             # drop new orders_export.csv files here
    ARCHIVE/            # processed CSVs are moved here automatically
  OUTPUT_HTML/           # generated cut sheet(s)
  logs/
```

From the GUI: **Load CSV Order**, then select your `orders_export.csv` from
`INPUT_CSV/ACTIVE`. The generated report opens automatically once parsing finishes.

## Configuration

- **`config/colors.txt`** / **`config/ignore_words.txt`** — one entry per line. Used to pull
  color/variant names out of product strings and to filter marketing filler ("Baby and
  Toddler", "Leather", etc.) out of the displayed product name.
- **`config/processed_orders.txt`** — the timestamp of the last successfully processed order.
  Editable from the GUI (there's format validation on the input).
- **`config/debug_mode.txt`** — `True` (default) reprocesses every order in the CSV on every
  run. Set to `False` to skip orders at or before the last-processed timestamp and have that
  timestamp advance automatically after a successful run.

## Product naming conventions

The parser expects Shopify product names to roughly follow
`[COLLECTION] [PRODUCT TYPE] [details] - SIZE (AGE)MEASUREMENT" / VARIANT`. See
[`product_naming_spec.md`](product_naming_spec.md) for the full spec and category-by-category
examples — getting product names into this shape is what makes category/size/variant
detection reliable instead of a pile of special cases.

## Project layout

```
StarryKnightOrderParser.py     # Tkinter GUI entry point
config.py                      # workspace setup, timestamp handling, debug mode, defaults
utility_modules/
  orderItem.py                  # CSV rows -> OrderItem/Addon domain objects, parse_orders()
  fileHelper.py                 # CSV reading (FileHelper.parse_csv_to_dict)
  makeHtml.py                   # domain objects -> HTML report
  helper.py                     # shared enums/maps (categories, addon types, icons)
  tkinterface.py                # small Tkinter convenience wrappers
tests/                          # pytest suite + synthetic fixture CSVs
```

## Running the tests

```
pip install -r requirements-dev.txt
pytest
```

The suite covers the CSV-parsing edge cases that used to crash or silently corrupt output:
missing/empty/BOM'd files, ragged rows, non-numeric quantities, blank product names, missing
required columns, and products with no size pattern — each backed by a small fixture CSV in
`tests/fixtures/`, plus a happy-path fixture and end-to-end checks.
