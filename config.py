from pathlib import Path
import sys


# ----------------------------------------
# app root
# ----------------------------------------

if getattr(sys, 'frozen', False):
    APP_ROOT = Path(sys.executable).parent
else:
    APP_ROOT = Path(__file__).resolve().parent


# ----------------------------------------
# directories
# ----------------------------------------

CONFIG_DIR = APP_ROOT / "config"
INPUT_DIR = APP_ROOT / "INPUT_CSV"
ACTIVE_DIR = INPUT_DIR / "ACTIVE"
ARCHIVE_DIR = INPUT_DIR / "ARCHIVE"
OUTPUT_DIR = APP_ROOT / "OUTPUT_HTML"


# ----------------------------------------
# files
# ----------------------------------------

COLORS_FILE = CONFIG_DIR / "colors.txt"
IGNORE_WORDS_FILE = CONFIG_DIR / "ignore_words.txt"
PROCESSED_FILE = APP_ROOT / "processed_orders.txt"


# ----------------------------------------
# default data
# ----------------------------------------

DEFAULT_COLORS = [

    "barley",
    "beige",
    "big sky",
    "black",
    "camel",
    "caramel",
    "carob",
    "chai",
    "chestnut",
    "cream",
    "daffodil",
    "dusty rose",
    "flax",
    "gray",
    "grey",
    "honey",
    "iron",
    "latte",
    "lichen",
    "milk",
    "navy",
    "oat",
    "oyster",
    "papaya",
    "pink",
    "platinum",
    "rose blush",
    "russet",
    "rust",
    "sable",
    "saddle",
    "sahara",
    "sepia",
    "sienna",
    "tan",
    "tumbleweed",
    "white",
    "wood",
]


DEFAULT_IGNORE_WORDS = [
    "&",
    "//",
    "and",
    "baby",
    "bella",
    "booties",
    "color",
    "critters",
    "cute",
    "daisy",
    "for",
    "headband",
    "jane",
    "janes",
    "leather",
    "loafer",
    "loafers",
    "lotus",
    "mary",
    "mocc",
    "moccs",
    "pick",
    "rainey",
    "removable",
    "rubber",
    "runner",
    "sandals",
    "scout",
    "sequoia",
    "shoe",
    "shoes",
    "sole",
    "soles",
    "strap",
    "sunrise",
    "t",
    "the",
    "tone",
    "toddler",
    "two",
    "your",
]

# ----------------------------------------
# helpers
# ----------------------------------------


def ensure_directory(path):

    path.mkdir(exist_ok=True)


def ensure_text_file(path, lines):

    if path.exists():
        return

    with open(path, "w", encoding="utf-8") as f:

        f.write("# Auto-generated config file\n")
        f.write("# One entry per line\n\n")

        for line in lines:
            f.write(line + "\n")


def ensure_empty_file(path):

    if path.exists():
        return

    with open(path, "w", encoding="utf-8") as f:
        f.write("")


# ----------------------------------------
# main setup
# ----------------------------------------

def initialize_app():

    # --------------------------
    # directories
    # --------------------------

    ensure_directory(CONFIG_DIR)

    ensure_directory(INPUT_DIR)
    ensure_directory(ACTIVE_DIR)
    ensure_directory(ARCHIVE_DIR)

    ensure_directory(OUTPUT_DIR)

    # --------------------------
    # files
    # --------------------------

    ensure_text_file(
        COLORS_FILE,
        DEFAULT_COLORS
    )

    ensure_text_file(
        IGNORE_WORDS_FILE,
        DEFAULT_IGNORE_WORDS
    )

    ensure_empty_file(PROCESSED_FILE)

    print("App initialization complete.")