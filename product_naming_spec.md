# Product Naming Guide

*A note for the shop owner, from the order-parser cleanup project.*

This isn't a rule the software enforces for you -- it's a description of what the
order parser actually looks for in a Shopify product name, so you can name (or
rename) products in a way that keeps them showing up correctly on the cut sheet
without any manual fixing after the fact. It doubles as a checklist for naming
brand-new products going forward.

## Why this matters

Every time you load an orders CSV, the tool reads each line item's product name
as plain text and tries to figure out, from the words in it: which collection it
belongs to (so it lands in the right section of the report), what size to cut,
and what color the customer picked. It has no way to "just know" -- it's
matching against a fixed list of keywords. When a product name doesn't contain
one of those keywords, or breaks the size/variant layout, the item either lands
in the wrong section, comes out with a blank color, or (worst case) doesn't show
up in the report at all and has to be caught and fixed by hand. A consistent
naming pattern means the report is right the first time, every time.

## The three-part pattern

Every product name Shopify sends through breaks into three parts, in this order:

```
[Descriptive words + Collection name] - [Size info] / [Variant]
```

For example:

```
Caramel Rainey Janes - 5 (15m)5.25" / Caramel
```

- **Everything before the ` - `** is the product header. This is where the
  collection name has to appear (see the list below) -- that's how the tool
  decides which section of the cut sheet the pair belongs in.
- **The size block, right after ` - `**, should stay in the `SIZE (AGE)MEASUREMENT"`
  shape you're already using, e.g. `5 (15m)5.25"`. The tool also understands a
  `Kids`, `W`, or `M` prefix in front of the number (`Kids 10`, `W 8`, `M 9`) if
  you ever need to distinguish a kids/women's/men's size run.
- **The variant, after ` / `**, is where Shopify puts the option the customer
  actually picked. This is the *first* place the tool looks for a color -- if a
  color name shows up here, that's what gets used. If there's no variant block
  at all, it falls back to scanning the whole product name for a color instead.

If a product genuinely has no variant (nothing for the customer to choose), it's
fine to leave off the `/ ...` part entirely.

## Collection names the tool recognizes

The product header has to contain one of these words (matching isn't
case-sensitive) for the pair to be filed under the right collection. This list
is checked top to bottom and the *first* one that matches wins, so it's worth
knowing what's on it:

| Keyword in product name | Collection section |
|---|---|
| Lotus | Lotus |
| T-strap | T-Strap |
| RAINEY | Rainey Janes |
| BELLA | Bella Janes |
| Mary | Mary Janes |
| SEQ | Sequoia |
| SUN | Sunrise |
| Daisy | Daisy Sandals |
| Moccs | Moccs |
| Two tone | Two Tone |
| Loafer | Loafers |
| Designs | Designs |
| Critters | Critters |
| Scout | Scout Booties |

If a product name doesn't contain any of these words, it currently gets dropped
from the main report silently -- there's no error, it just won't show up. If
you're planning a new collection, the simplest fix is to make sure its name
includes one of the words above where it fits naturally, or let me know and I
can add the new collection's keyword to this list in the code.

One thing to watch for: because it's a first-match search, a name that
accidentally contains two of these keywords will be filed under whichever one
appears first in the table above, not necessarily the one you meant. Keeping
one collection keyword per product name avoids that entirely.

## Words that get automatically cleaned up

You don't need to strip marketing language out of the product name yourself --
words like "Shoes," "Baby and Toddler," "Leather," "and," "for," "the," and the
collection words themselves (Rainey, Bella, Mary, Scout, Sequoia, Sunrise,
Daisy, Loafer, Moccs, Critters, Two Tone, Strap, T, Lotus) are automatically
filtered out of the display name shown on the cut sheet, along with the color
words listed below once a color's been found. So a name like `Caramel RAINEY
JANES Shoes Baby and Toddler - 5 (15m)5.25"` already displays cleanly as
`Caramel` on the sheet -- you don't have to manually shorten it in Shopify
first. This list of filler words lives in `config/ignore_words.txt` if you ever
want to add to it.

## Colors the tool recognizes

Color matching only works for names on this list (also checked case-insensitively):

barley, beige, big sky, black, camel, caramel, carob, chai, chestnut, cream,
daffodil, dusty rose, flax, gray, grey, honey, iron, latte, lichen, milk,
navy, oat, oyster, papaya, pink, platinum, rose blush, russet, rust, sable,
saddle, sahara, sepia, sienna, tan, tumbleweed, white, wood

If a new color isn't on this list, it won't be picked up automatically and the
color field will come out blank on the report -- easy to fix by adding the new
name to `config/colors.txt`, but worth doing *before* the first batch of orders
for that color comes in rather than after. Just let me know the new color name
and I can add it.

## Addons (wool inserts, big runners, purses, headbands, gift cards)

These aren't shoes, so they're handled separately from the collection list
above. A line item is recognized as an addon if its name contains one of these
phrases, matched the same first-wins way:

1. `natural wool insert`
2. `big runner`
3. `purse`
4. `headband`
5. `gift card`

For wool inserts, whatever follows ` - ` becomes the size (`Natural Wool Insert
- Small` -> size "Small"). For big runners and headbands, whatever follows
` - ` (or precedes "Big Runner" if there's no dash) becomes the color, e.g.
`Tan - Big Runner` or `Tan Big Runner` both work. Purses work the same way with
whatever precedes the word "purse." Keeping that dash in place (`Color - Big
Runner`) is the more reliable of the two forms.

## Quick checklist for naming a new product

1. Pick the collection keyword from the table above that this product belongs
   to, and make sure it appears somewhere in the header (before the ` - `).
   Only use one keyword per product.
2. Keep the size block in the `- SIZE (AGE)MEASUREMENT"` format, right after
   the header, exactly as you've been doing.
3. If there's a customer-chosen option (usually color), put it after ` / ` at
   the very end, using a color name from the recognized list above.
4. Don't worry about trimming marketing words like "Shoes," "Leather," or
   "Baby and Toddler" out of the name -- the report cleans those up
   automatically.
5. If you're introducing a brand-new collection name or color that isn't in
   either list above, flag it to me before the first order comes in so I can
   add it to the config -- it takes minutes, but doing it ahead of time means
   nothing falls through the cracks on the report.

## Examples

| Current-style Shopify name | What shows up on the cut sheet |
|---|---|
| `Latte, Saddle, Sable Leather LOAFERS Shoes Baby and Toddler - 6 (18m)5.5" / Sable dark brown` | Loafers, size 6 (18m)5.5", color Sable |
| `Caramel RAINEY JANES Shoes Baby and Toddler - 5 (15m)5.25"` | Rainey Janes, size 5 (15m)5.25", color Caramel |
| `Dusty Rose & Oyster BELLA JANES Shoes Baby and Toddler - 7 (24m)5.75" / Dusty Rose` | Bella Janes, size 7 (24m)5.75", color Dusty Rose |
| `Sable & Sepia SEQUOIA Shoes Baby and Toddler - 8 (2yr)6" / Sepia` | Sequoia, size 8 (2yr)6", color Sepia |
| `Tan - Big Runner` | Big Runner addon, color Tan |
