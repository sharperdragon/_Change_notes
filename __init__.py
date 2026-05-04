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

from typing import Callable, Optional

from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import QAction, QMenu
from aqt.utils import showInfo, tooltip

from .menu_compiler import compile_browser_context_menu
from .modules.add_custom_tags import apply_tags_to_note, iter_reviewer_shortcut_actions
from .modules.add_table_class.main import add_class_main

# ! --------------------------- USER-TUNABLE CONSTANTS ---------------------------
# Set to None to use each section's `submenu_label` from config.
CUSTOM_TAGS_MENU_LABEL: Optional[str] = None
CUSTOM_TAGS_MENU_CONFIG_SECTION = "add_custom_tags_1"
CUSTOM_TAGS_MENU_HIDE_WHEN_NO_PRESETS = False
CUSTOM_TAGS_MENU_2_LABEL: Optional[str] = None
CUSTOM_TAGS_MENU_2_CONFIG_SECTION = "add_custom_tags_2"
CUSTOM_TAGS_MENU_2_HIDE_WHEN_NO_PRESETS = True
REVIEW_TAG_SHORTCUTS_ENABLED = True
REVIEW_TAG_SHORTCUT_CONFIG_SECTIONS = (
    CUSTOM_TAGS_MENU_CONFIG_SECTION,
    CUSTOM_TAGS_MENU_2_CONFIG_SECTION,
)
REVIEW_TAG_SHORTCUT_SKIP_EXISTING_BINDINGS = False
REVIEW_TAG_SHORTCUT_SUCCESS_TEMPLATE = "✅ Tagged note: {preset_label}"
REVIEW_TAG_SHORTCUT_ALREADY_PRESENT_TEMPLATE = "ℹ️ Tag already present: {preset_label}"
ADDON_MODULE_NAME = __name__
# ! -----------------------------------------------------------------------------


# Injects right-click browser menu options
def on_browser_will_show_context_menu(browser: Browser, menu):
    compile_browser_context_menu(
        browser,
        menu,
        custom_tags_menu_label=CUSTOM_TAGS_MENU_LABEL,
        custom_tags_menu_config_section=CUSTOM_TAGS_MENU_CONFIG_SECTION,
        custom_tags_menu_hide_when_no_presets=CUSTOM_TAGS_MENU_HIDE_WHEN_NO_PRESETS,
        custom_tags_menu_2_label=CUSTOM_TAGS_MENU_2_LABEL,
        custom_tags_menu_2_config_section=CUSTOM_TAGS_MENU_2_CONFIG_SECTION,
        custom_tags_menu_2_hide_when_no_presets=CUSTOM_TAGS_MENU_2_HIDE_WHEN_NO_PRESETS,
    )


def _apply_reviewer_shortcut_tags(reviewer, preset_label: str, tags: list[str]) -> None:
    card = getattr(reviewer, "card", None)
    if card is None:
        return

    col = getattr(reviewer.mw, "col", None)
    if col is None:
        return

    try:
        note = card.note()
    except Exception:
        return

    added_count = apply_tags_to_note(col, note, tags)
    if added_count > 0:
        tooltip(REVIEW_TAG_SHORTCUT_SUCCESS_TEMPLATE.format(preset_label=preset_label))
    else:
        tooltip(REVIEW_TAG_SHORTCUT_ALREADY_PRESENT_TEMPLATE.format(preset_label=preset_label))


def _inject_review_tag_shortcuts(state: str, shortcuts: list[tuple[str, Callable]]) -> None:
    if not REVIEW_TAG_SHORTCUTS_ENABLED or state != "review":
        return

    reviewer = getattr(mw, "reviewer", None)
    if reviewer is None:
        return

    shortcut_index_by_key: dict[str, int] = {}
    for idx, (key, _handler) in enumerate(shortcuts):
        normalized = str(key).strip().lower()
        if normalized:
            shortcut_index_by_key[normalized] = idx

    newly_added = set()
    for section in REVIEW_TAG_SHORTCUT_CONFIG_SECTIONS:
        if not isinstance(section, str) or not section.strip():
            continue

        for shortcut, preset_label, tags in iter_reviewer_shortcut_actions(config_section=section):
            shortcut_key = str(shortcut).strip()
            if not shortcut_key:
                continue

            shortcut_lc = shortcut_key.lower()
            if shortcut_lc in newly_added:
                continue
            handler = (
                lambda label=preset_label, preset_tags=list(tags), r=reviewer: _apply_reviewer_shortcut_tags(
                    r,
                    label,
                    preset_tags,
                )
            )

            if shortcut_lc in shortcut_index_by_key:
                if REVIEW_TAG_SHORTCUT_SKIP_EXISTING_BINDINGS:
                    continue
                shortcuts[shortcut_index_by_key[shortcut_lc]] = (shortcut_key, handler)
                newly_added.add(shortcut_lc)
                continue

            shortcuts.append(
                (
                    shortcut_key,
                    handler,
                )
            )
            newly_added.add(shortcut_lc)
            shortcut_index_by_key[shortcut_lc] = len(shortcuts) - 1


# Ensures the browser context menu is only hooked once
if not getattr(mw, "_change_note_type_menu_injected", False):
    gui_hooks.browser_will_show_context_menu.append(on_browser_will_show_context_menu)
    mw._change_note_type_menu_injected = True


if not getattr(mw, "_change_notes_review_shortcuts_hooked", False):
    if hasattr(gui_hooks, "state_shortcuts_will_change"):
        gui_hooks.state_shortcuts_will_change.append(_inject_review_tag_shortcuts)
    else:
        try:
            from anki.hooks import addHook

            addHook(
                "reviewStateShortcuts",
                lambda shortcuts: _inject_review_tag_shortcuts("review", shortcuts),
            )
        except Exception:
            pass
    mw._change_notes_review_shortcuts_hooked = True


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
