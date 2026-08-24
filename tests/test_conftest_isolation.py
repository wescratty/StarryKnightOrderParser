"""
Regression test for the `workspace` fixture itself (see conftest.py):
it must never touch the real, permanent BOOTSTRAP_FILE
(~/.starry_knight_workspace in the actual user's home directory).

The original fixture called config.set_workspace_path(tmp_path) directly,
which persists straight to that real file with no restore -- so running
the test suite permanently redirected the live app's workspace at a
pytest temp directory. Once pytest later cleaned that temp directory up,
the real app was left pointed at a folder that no longer existed, with
no obvious way to tell (a *path* was still saved, so the first-run wizard
never re-triggered) -- this is exactly what happened in production.
"""

import config as app_config


def test_workspace_fixture_does_not_touch_the_real_bootstrap_file(workspace, tmp_path):
    # BOOTSTRAP_FILE must be monkeypatched to something inside this
    # test's own tmp_path for the duration of the test -- never the real
    # ~/.starry_knight_workspace.
    assert str(app_config.BOOTSTRAP_FILE).startswith(str(tmp_path))


def test_workspace_fixture_restores_bootstrap_file_after_test():
    """
    Runs *without* the `workspace` fixture -- confirms BOOTSTRAP_FILE is
    back to its real, original value once a prior test using `workspace`
    has finished (monkeypatch's auto-restore).
    """

    from pathlib import Path

    assert app_config.BOOTSTRAP_FILE == Path.home() / ".starry_knight_workspace"
