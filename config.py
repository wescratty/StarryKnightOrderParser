import sys
from pathlib import Path
import shutil
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
DEBUG_FILE = None
processed_time_stamp = None

# Default DEBUG mode when no workspace/config file exists yet. True keeps
# the historical hardcoded behavior (skip-already-processed feature off,
# every order reprocessed) until the user opts in via the config file.
DEFAULT_DEBUG_MODE = True

# ----------------------------------------
# bootstrap file
# ----------------------------------------
BOOTSTRAP_FILE = Path.home() / ".starry_knight_workspace"

# ----------------------------------------
# timestamp helpers
# ----------------------------------------


# ----------------------------------------
# runtime state
# ----------------------------------------


# ----------------------------------------
# timestamp helpers
# ----------------------------------------

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


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


def validate_timestamp(ts):

    cleaned = clean_timestamp(ts)

    if not cleaned:

        return {
            "success": False,
            "message": "Timestamp is empty."
        }

    try:

        datetime.strptime(
            cleaned,
            TIMESTAMP_FORMAT
        )

    except ValueError:

        return {
            "success": False,
            "message": (
                "Invalid timestamp format.\n"
                "Expected: YYYY-MM-DD HH:MM:SS"
            )
        }

    return {
        "success": True,
        "message": "Timestamp valid."
    }


def timestamp_to_datetime(ts):

    cleaned = clean_timestamp(ts)

    validation = validate_timestamp(cleaned)

    if not validation["success"]:
        return None

    return datetime.strptime(
        cleaned,
        TIMESTAMP_FORMAT
    )


# ----------------------------------------
# processed timestamp
# ----------------------------------------

def load_last_processed_timestamp():

    global processed_time_stamp

    if not PROCESSED_FILE:
        return None

    if not PROCESSED_FILE.exists():

        processed_time_stamp = None

        return None

    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:

        text = f.read().strip()

    if not text:

        processed_time_stamp = None

        return None

    processed_time_stamp = timestamp_to_datetime(text)

    return processed_time_stamp


def get_last_processed_timestamp():

    global processed_time_stamp

    return processed_time_stamp


def set_last_processed_timestamp(ts):

    global processed_time_stamp

    validation = validate_timestamp(ts)

    if not validation["success"]:

        return validation

    cleaned = clean_timestamp(ts)

    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:

        f.write(cleaned)

    processed_time_stamp = timestamp_to_datetime(cleaned)

    print(f"Saved processed timestamp: {cleaned}")

    return {
        "success": True,
        "message": "Timestamp saved."
    }


def archive_csv_file(path):
    """
    Moves a processed CSV from ACTIVE → ARCHIVE
    """

    path = Path(path)

    if not path.exists():
        return {
            "success": False,
            "message": f"File not found: {path}"
        }

    if not ACTIVE_DIR or not ARCHIVE_DIR:
        return {
            "success": False,
            "message": "Directories not initialized"
        }

    ensure_directory(ARCHIVE_DIR)

    # ----------------------------------------
    # create unique archive filename
    # ----------------------------------------

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    target = ARCHIVE_DIR / f"{path.stem}_{timestamp}{path.suffix}"

    try:
        shutil.move(str(path), str(target))

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }

    return {
        "success": True,
        "message": f"Archived to {target}",
        "path": target
    }


def get_last_processed_timestamp_string():

    global processed_time_stamp
    load_last_processed_timestamp()

    if not processed_time_stamp:
        return ""

    return processed_time_stamp.strftime(
        TIMESTAMP_FORMAT
    )


def clear_last_processed_timestamp():

    global processed_time_stamp

    with open(PROCESSED_FILE, "w", encoding="utf-8") as f:

        f.write("")

    processed_time_stamp = None

    print("Processed timestamp cleared.")

    return {
        "success": True,
        "message": "Timestamp cleared."
    }

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
    "on",
    "with",
    "designs",
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


def load_ignore_words():

    if not IGNORE_WORDS_FILE:
        return []

    if not IGNORE_WORDS_FILE.exists():
        return []

    ignore = []

    with open(IGNORE_WORDS_FILE, "r", encoding="utf-8") as f:

        for line in f:

            line = line.strip().lower()

            # --------------------------
            # ignore empty/comment lines
            # --------------------------

            if not line:
                continue

            if line.startswith("#"):
                continue

            ignore.append(line)

    # --------------------------
    # longest first
    #
    # prevents:
    # "tan" matching before
    # "tumbleweed tan"
    # --------------------------

    return sorted(
        ignore,
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
    global DEBUG_FILE

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

    DEBUG_FILE = CONFIG_DIR / "debug_mode.txt"

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

    ensure_text_file(
        DEBUG_FILE,
        [str(DEFAULT_DEBUG_MODE)]
    )

    print("App initialization complete.")

    return True


# ----------------------------------------
# debug mode
# ----------------------------------------


def get_debug_mode():
    """
    Reads DEBUG mode from the workspace config file (config/debug_mode.txt).
    True: reprocess every order in the CSV every run (skip-already-processed
    feature is off).
    False: skip orders at/before the Last Processed Order Timestamp, and
    update that timestamp after a successful run.
    Falls back to DEFAULT_DEBUG_MODE if no workspace/config file exists yet
    or the file can't be parsed as a bool.
    """

    if not DEBUG_FILE or not DEBUG_FILE.exists():
        return DEFAULT_DEBUG_MODE

    with open(DEBUG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip().lower()

            # ignore empty/comment lines (ensure_text_file writes a
            # "# Auto-generated..." header on first creation)
            if not line or line.startswith("#"):
                continue

            if line in ("true", "1", "yes", "on"):
                return True

            if line in ("false", "0", "no", "off"):
                return False

    return DEFAULT_DEBUG_MODE


def set_debug_mode(value):
    """
    Persists DEBUG mode to the workspace config file.
    """

    if not DEBUG_FILE:
        return {
            "success": False,
            "message": "Workspace not initialized."
        }

    with open(DEBUG_FILE, "w", encoding="utf-8") as f:
        f.write(str(bool(value)))

    print(f"Saved DEBUG mode: {bool(value)}")

    return {
        "success": True,
        "message": f"DEBUG mode set to {bool(value)}."
    }
