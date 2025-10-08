from aqt import mw
from aqt.qt import QAction
from aqt.browser import Browser
from aqt.gui_hooks import browser_will_show_context_menu

from .combo_runner import run_combined_merge

def on_browser_context_menu(browser: Browser, menu):
    selected = browser.selectedNotes()
    if not selected:
        return

    action = QAction("🧬 Merge Images + Tags", browser)
    action.triggered.connect(lambda: run_combined_merge(browser))
    menu.addSeparator()
    menu.addAction(action)

if not getattr(mw, "_merge_images_and_tags_menu_hooked", False):
    browser_will_show_context_menu.append(on_browser_context_menu)
    mw._merge_images_and_tags_menu_hooked = True