"""
Tests for utility_modules.tkinterface.SuperTk's macOS button-background
workaround.

Real-world bug this guards against: on Windows, bg='black'/fg='lime' (or
its hex equivalent) works fine on native tk.Button/Checkbutton/Radiobutton.
On macOS, Aqua ignores bg/background on those widgets entirely -- the
button stays the system gray/white no matter the color or format -- and
the previously-working fix (coloring the widget's highlight border via
highlightbackground/highlightthickness, which Aqua *does* honor) was lost
when a Mac build pulled `main` without an OS check gating it. These tests
confirm the workaround is applied on a simulated Mac and left alone
everywhere else, without needing an actual Mac to run on.
"""

import platform

import pytest

from utility_modules import tkinterface


@pytest.fixture
def mac(monkeypatch):
    monkeypatch.setattr(tkinterface, "IS_MAC", True)


@pytest.fixture
def not_mac(monkeypatch):
    monkeypatch.setattr(tkinterface, "IS_MAC", False)


def test_is_mac_reflects_platform_system():
    # sanity check that the module-level flag is wired to platform.system()
    # the way the rest of the tests assume, without hardcoding "Darwin" vs.
    # whatever this machine actually reports
    assert tkinterface.IS_MAC == (platform.system() == "Darwin")


def test_button_gets_highlight_workaround_on_mac(mac):
    tk = tkinterface.SuperTk()
    tk.get_window()
    button = tk.get_button(tk.scroll_area, "Go", lambda: None)

    assert button.cget("highlightbackground") == tk.bg
    assert button.cget("highlightthickness") == 2


def test_button_is_left_alone_off_mac(not_mac):
    tk = tkinterface.SuperTk()
    tk.get_window()
    button = tk.get_button(tk.scroll_area, "Go", lambda: None)

    # no highlight-border workaround applied -- Windows/Linux already
    # render bg=/background= correctly, so nothing extra should be set
    assert button.cget("highlightbackground") is None
    assert button.cget("highlightthickness") is None


def test_check_box_gets_highlight_workaround_on_mac(mac):
    tk = tkinterface.SuperTk()
    tk.get_window()
    var = tk.get_str_var()
    checkbox = tk.get_check_box(tk.scroll_area, "Archive", var, lambda: None)

    assert checkbox.cget("highlightbackground") == tk.bg
    assert checkbox.cget("highlightthickness") == 2


def test_radio_button_gets_highlight_workaround_on_mac(mac):
    tk = tkinterface.SuperTk()
    tk.get_window()
    var = tk.get_str_var()
    radio = tk.get_radio_button(tk.scroll_area, "Option", var, 0, lambda: None)

    assert radio.cget("highlightbackground") == tk.bg
    assert radio.cget("highlightthickness") == 2


def test_mac_workaround_follows_theme_color(mac):
    # the workaround must track whatever bg the theme is currently set to,
    # not a hardcoded 'black' -- otherwise it'd look wrong after
    # set_theme(0) switches to the light theme
    tk = tkinterface.SuperTk()
    tk.get_window()
    tk.set_theme(0)  # light theme: bg -> 'white'

    button = tk.get_button(tk.scroll_area, "Go", lambda: None)
    assert button.cget("highlightbackground") == "white"
