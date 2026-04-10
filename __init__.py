"""
_Change_notes Add-on for Anki

Features:
- Batch change note types from the browser context menu
- Optionally apply field-mapping profiles for note type migration
- Delete unused note types from the collection
- Unify tags between notes with identical first fields
- GUI dialog for editing field-mapping profiles

Compatibility:
- Supports multiple Anki versions through dynamic import fallbacks
- GUI and context menu integrations ensure minimal user disruption

"""

from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import QAction, QMenu
from aqt.utils import showInfo

from .menu_compiler import compile_browser_context_menu
from .modules.add_table_class.main import add_class_main

# ! --------------------------- USER-TUNABLE CONSTANTS ---------------------------
CUSTOM_TAGS_MENU_LABEL = " 🎛️ Custom Tags"
ADDON_MODULE_NAME = __name__
# ! -----------------------------------------------------------------------------


# Injects right-click browser menu options
def on_browser_will_show_context_menu(browser: Browser, menu):
    compile_browser_context_menu(
        browser,
        menu,
        custom_tags_menu_label=CUSTOM_TAGS_MENU_LABEL,
    )


# Ensures the browser context menu is only hooked once
if not getattr(mw, "_change_note_type_menu_injected", False):
    gui_hooks.browser_will_show_context_menu.append(on_browser_will_show_context_menu)
    mw._change_note_type_menu_injected = True


# Adds a submenu under Tools > Add-ons for quick access to browser-based operations.
# Currently includes placeholders to focus the browser window.
def inject_tools_menu(menu):
    # Create "Change Note Types" submenu in Tools > Add-ons
    change_menu = QMenu("Change Note Types", menu)

    def focus_browser_or_prompt():
        browser = getattr(mw, "browser", None)
        if browser:
            browser.activateWindow()
            browser.raise_()
        else:
            showInfo("Open the Browser and select notes first.")

    batch = QAction("Batch Change Note Type…", mw)
    batch.triggered.connect(focus_browser_or_prompt)
    change_menu.addAction(batch)

    resolve = QAction("Resolve Duplicates in Browser", mw)
    resolve.triggered.connect(focus_browser_or_prompt)
    change_menu.addAction(resolve)

    classify_tables = QAction("Classify Tables on Selected Notes…", mw)
    classify_tables.triggered.connect(
        lambda: (
            add_class_main(mw.browser)
            if getattr(mw, "browser", None)
            else showInfo("Open the Browser and select notes first.")
        )
    )
    change_menu.addAction(classify_tables)

    menu.addMenu(change_menu)


try:
    from aqt.gui_hooks import addon_menu_will_show

    if not getattr(mw, "_change_note_type_tools_menu_injected", False):
        addon_menu_will_show.append(inject_tools_menu)
        mw._change_note_type_tools_menu_injected = True
except ImportError:
    pass  # Older Anki versions don't support addon menu hook


def _clear_stale_config_action():
    """Ensure Anki uses the built-in config editor for this add-on."""
    addon_manager = getattr(mw, "addonManager", None)
    if addon_manager is None:
        return

    for attr_name in ("_configActions", "_config_actions"):
        config_actions = getattr(addon_manager, attr_name, None)
        if isinstance(config_actions, dict):
            config_actions.pop(ADDON_MODULE_NAME, None)


_clear_stale_config_action()
