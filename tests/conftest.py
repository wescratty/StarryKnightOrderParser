import sys
from pathlib import Path

# Make the repo root importable (config, utility_modules) when pytest is
# run from anywhere.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

import pytest
import config as app_config


@pytest.fixture
def workspace(tmp_path):
    """
    Points the app's config module at a throwaway workspace directory for
    the duration of a test, so tests never touch the real
    C:\\dev\\LoverGirl\\starry_knight_order_parser config/ files.
    """

    app_config.set_workspace_path(str(tmp_path))
    app_config.load_paths()
    app_config.initialize_app()
    yield tmp_path
