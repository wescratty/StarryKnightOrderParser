from pathlib import Path
import sys
from datetime import datetime


# ----------------------------------------
# workspace root
# ----------------------------------------

APP_ROOT = None

CONFIG_DIR = None
INPUT_DIR = None
ACTIVE_DIR = None
ARCHIVE_DIR = None
OUTPUT_DIR = None
LOG_DIR = None

COLORS_FILE = None
IGNORE_WORDS_FILE = None
PROCESSED_FILE = None

# ----------------------------------------
# timestamp helpers
# ----------------------------------------


def clean_timestamp(ts):

    if not ts:
        return ""

    # --------------------------
    # remove timezone suffix
    #
    # "2026-05-08 10:58:11 -0600"
    # ->
    # "2026-05-08 10:58:11"
    # --------------------------

    return ts.split(" -")[0].strip()


def timestamp_to_datetime(ts):

    cleaned = clean_timestamp(ts)

    if not cleaned:
        return None

    return datetime.strptime(
        cleaned,
        "%Y-%m-%d %H:%M:%S"
    )


# ----------------------------------------
# processed timestamp
# ----------------------------------------

def load_last_processed_timestamp():

    if not PROCESSED_FILE:
        return None

    if not PROCESSED_FILE.exists():
        return None

    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:

        text = f.read().strip()

    if not text:
        return None

    return timestamp_to_datetime(text)


def save_last_processed_timestamp(ts):

    if not PROCESSED_FILE:
        return

    cleaned = clean_timestamp(ts)

    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:

        f.write(cleaned)

    print(f"Saved processed timestamp: {cleaned}")
# ----------------------------------------
# bootstrap file
# ----------------------------------------


BOOTSTRAP_FILE = Path.home() / ".starry_knight_workspace"


# ----------------------------------------
# runtime root
# ----------------------------------------

if getattr(sys, 'frozen', False):
    BUNDLE_ROOT = Path(sys.executable).parent
else:
    BUNDLE_ROOT = Path(__file__).resolve().parent


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

def set_workspace_path(path):

    path = Path(path)

    with open(BOOTSTRAP_FILE, "w", encoding="utf-8") as f:
        f.write(str(path))

    print(f"Workspace path saved: {path}")


def get_workspace_path():

    if not BOOTSTRAP_FILE.exists():
        return None

    with open(BOOTSTRAP_FILE, "r", encoding="utf-8") as f:

        path = f.read().strip()

    if not path:
        return None

    return Path(path)


def workspace_exists():

    path = get_workspace_path()

    if not path:
        return False

    return path.exists()


def ensure_directory(path):

    path.mkdir(parents=True, exist_ok=True)


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
# output helpers
# ----------------------------------------


def get_output_file(filename="orders.html"):

    if not OUTPUT_DIR:
        return None

    return OUTPUT_DIR / filename

# ----------------------------------------
# config loaders
# ----------------------------------------


def load_colors():

    if not COLORS_FILE:
        return []

    if not COLORS_FILE.exists():
        return []

    colors = []

    with open(COLORS_FILE, "r", encoding="utf-8") as f:

        for line in f:

            line = line.strip().lower()

            # --------------------------
            # ignore empty/comment lines
            # --------------------------

            if not line:
                continue

            if line.startswith("#"):
                continue

            colors.append(line)

    # --------------------------
    # longest first
    #
    # prevents:
    # "tan" matching before
    # "tumbleweed tan"
    # --------------------------

    return sorted(
        colors,
        key=len,
        reverse=True
    )

# ----------------------------------------
# path initialization
# ----------------------------------------


def load_paths():

    global APP_ROOT

    global CONFIG_DIR
    global INPUT_DIR
    global ACTIVE_DIR
    global ARCHIVE_DIR
    global OUTPUT_DIR
    global LOG_DIR

    global COLORS_FILE
    global IGNORE_WORDS_FILE
    global PROCESSED_FILE

    APP_ROOT = get_workspace_path()

    if not APP_ROOT:
        return False

    CONFIG_DIR = APP_ROOT / "config"

    INPUT_DIR = APP_ROOT / "INPUT_CSV"

    ACTIVE_DIR = INPUT_DIR / "ACTIVE"

    ARCHIVE_DIR = INPUT_DIR / "ARCHIVE"

    OUTPUT_DIR = APP_ROOT / "OUTPUT_HTML"

    LOG_DIR = APP_ROOT / "logs"

    COLORS_FILE = CONFIG_DIR / "colors.txt"

    IGNORE_WORDS_FILE = CONFIG_DIR / "ignore_words.txt"

    PROCESSED_FILE = CONFIG_DIR / "processed_orders.txt"

    return True


# ----------------------------------------
# main setup
# ----------------------------------------

def initialize_app():

    if not load_paths():

        print("No workspace path configured.")

        return False

    # --------------------------
    # directories
    # --------------------------

    ensure_directory(APP_ROOT)

    ensure_directory(CONFIG_DIR)

    ensure_directory(INPUT_DIR)

    ensure_directory(ACTIVE_DIR)

    ensure_directory(ARCHIVE_DIR)

    ensure_directory(OUTPUT_DIR)

    ensure_directory(LOG_DIR)

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

    return True
