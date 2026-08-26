"""
Tests for utility_modules.tkinterface's macOS button/checkbox/radio-button
stand-ins.

Real-world bug this guards against: on Windows, bg='black'/fg='lime' (or
its hex equivalent) works fine on native tk.Button/Checkbutton/
Radiobutton. On macOS, Aqua ignores bg/background on those widgets
entirely, no matter the color format -- and the previously-tried
highlightbackground/highlightthickness "compromise" workaround was
confirmed NOT to actually fix the visible background color either. The
real fix: on Mac, these widgets are built from tk.Label instead (Label
always respects bg/fg on Mac -- Aqua's restriction is specific to
interactive controls, not passive display widgets), styled and wired up
to behave like the real thing.
"""

import platform

import pytest

from utility_modules import tkinterface
from utility_modules.tkinterface import _MacButton, _MacCheckbox, _MacRadioButton


class _Event:
    def __init__(self, x=5, y=5):
        self.x = x
        self.y = y


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


# ----------------------------------------
# get_button
# ----------------------------------------

def test_button_is_mac_button_on_mac(mac):
    tk = tkinterface.SuperTk()
    tk.get_window()
    button = tk.get_button(tk.scroll_area, "Go", lambda: None)

    assert isinstance(button, _MacButton)
    assert button.cget("bg") == tk.bg
    assert button.cget("fg") == tk.fg


def test_button_is_native_tk_button_off_mac(not_mac):
    tk = tkinterface.SuperTk()
    tk.get_window()
    button = tk.get_button(tk.scroll_area, "Go", lambda: None)

    assert not isinstance(button, _MacButton)
    assert button.cget("background") == tk.bg


def test_mac_button_fires_command_on_click_release_inside(mac):
    calls = []
    tk = tkinterface.SuperTk()
    tk.get_window()
    button = tk.get_button(tk.scroll_area, "Go", lambda: calls.append(1))

    button._on_press(_Event())
    button._on_release(_Event())

    assert calls == [1]


def test_mac_button_does_not_fire_if_released_outside(mac):
    # mirrors real Button behavior: pressing, dragging off, and releasing
    # elsewhere should not trigger the command
    calls = []
    tk = tkinterface.SuperTk()
    tk.get_window()
    button = tk.get_button(tk.scroll_area, "Go", lambda: calls.append(1))

    button._on_press(_Event())
    button._on_release(_Event(x=-10, y=-10))

    assert calls == []


def test_mac_button_bg_config_still_works_after_creation(mac):
    # regression guard for the "Set" button's green unsaved-change
    # highlight (StarryKnightOrderParser.on_change/set_date_range),
    # which calls .config(bg=...) directly on the button after creation
    tk = tkinterface.SuperTk()
    tk.get_window()
    button = tk.get_button(tk.scroll_area, "Set", lambda: None)

    button.config(bg="green")
    assert button.cget("bg") == "green"


# ----------------------------------------
# get_check_box
# ----------------------------------------

def test_check_box_is_mac_checkbox_on_mac(mac):
    tk = tkinterface.SuperTk()
    tk.get_window()
    var = tk.tk.BooleanVar(value=True)
    checkbox = tk.get_check_box(tk.scroll_area, "Archive", var, lambda: None)

    assert isinstance(checkbox, _MacCheckbox)
    assert checkbox.cget("bg") == tk.bg


def test_check_box_is_native_off_mac(not_mac):
    tk = tkinterface.SuperTk()
    tk.get_window()
    var = tk.tk.BooleanVar(value=True)
    checkbox = tk.get_check_box(tk.scroll_area, "Archive", var, lambda: None)

    assert not isinstance(checkbox, _MacCheckbox)


def test_mac_checkbox_toggles_var_and_calls_command_on_click(mac):
    calls = []
    tk = tkinterface.SuperTk()
    tk.get_window()
    var = tk.tk.BooleanVar(value=True)
    checkbox = tk.get_check_box(tk.scroll_area, "Archive", var, lambda: calls.append(var.get()))

    checkbox._on_click(_Event())
    assert var.get() is False
    assert calls == [False]

    checkbox._on_click(_Event())
    assert var.get() is True
    assert calls == [False, True]


def test_mac_checkbox_label_reflects_checked_state(mac):
    tk = tkinterface.SuperTk()
    tk.get_window()
    var = tk.tk.BooleanVar(value=True)
    checkbox = tk.get_check_box(tk.scroll_area, "Archive", var, lambda: None)

    assert checkbox.cget("text") == _MacCheckbox._MARK_ON + "Archive"

    checkbox._on_click(_Event())
    assert checkbox.cget("text") == _MacCheckbox._MARK_OFF + "Archive"


# ----------------------------------------
# get_radio_button
# ----------------------------------------

def test_radio_button_is_mac_radio_on_mac(mac):
    tk = tkinterface.SuperTk()
    tk.get_window()
    var = tk.get_str_var()
    radio = tk.get_radio_button(tk.scroll_area, "Option", var, "opt1", lambda: None)

    assert isinstance(radio, _MacRadioButton)


def test_mac_radio_button_sets_var_and_calls_command_on_click(mac):
    calls = []
    tk = tkinterface.SuperTk()
    tk.get_window()
    var = tk.get_str_var()
    radio = tk.get_radio_button(tk.scroll_area, "Option", var, "opt1", lambda: calls.append(var.get()))

    radio._on_click(_Event())

    assert var.get() == "opt1"
    assert calls == ["opt1"]


# ----------------------------------------
# theme color follow-through
# ----------------------------------------

def test_mac_widgets_follow_current_theme_color(mac):
    # the Mac stand-ins must track whatever bg/fg the theme is currently
    # set to, not a hardcoded 'black'/'#00FF00' -- otherwise they'd look
    # wrong after set_theme(0) switches to the light theme
    tk = tkinterface.SuperTk()
    tk.get_window()
    tk.set_theme(0)  # light theme: bg -> 'white', fg -> 'black'

    button = tk.get_button(tk.scroll_area, "Go", lambda: None)
    assert button.cget("bg") == "white"
    assert button.cget("fg") == "black"
