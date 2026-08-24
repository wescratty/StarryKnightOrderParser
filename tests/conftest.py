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
def workspace(tmp_path, monkeypatch):
    """
    Points the app's config module at a throwaway workspace directory for
    the duration of a test, so tests never touch the real
    C:\\dev\\LoverGirl\\starry_knight_order_parser config/ files.

    Regression test/fixture fix: set_workspace_path() persists the chosen
    directory to BOOTSTRAP_FILE (~/.starry_knight_workspace in the *real*
    user home directory) -- a real file shared with the actual running
    app, not something pytest's tmp_path isolates. The old version of
    this fixture called set_workspace_path() directly and never restored
    it, so running the test suite permanently repointed the live app's
    workspace at a pytest temp directory -- one that pytest itself later
    cleans up, silently breaking the app (all config/ignore-word/color
    lookups start returning empty since the directory no longer exists,
    but the app doesn't know to ask for a new one since a *path* is
    still saved).

    Fixed by monkeypatching BOOTSTRAP_FILE itself to a per-test path
    inside tmp_path -- set_workspace_path()/get_workspace_path() now read
    and write that throwaway file instead of the real one, and
    monkeypatch automatically restores the original BOOTSTRAP_FILE value
    when the test ends, regardless of pass/fail.
    """

    monkeypatch.setattr(app_config, "BOOTSTRAP_FILE", tmp_path / ".starry_knight_workspace_test")

    app_config.set_workspace_path(str(tmp_path))
    app_config.load_paths()
    app_config.initialize_app()
    yield tmp_path
