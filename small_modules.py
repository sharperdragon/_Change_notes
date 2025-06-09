import os
from collections import defaultdict
from datetime import datetime

from aqt import mw
from aqt.qt import QAction, QInputDialog, QMenu
from aqt.browser import Browser
from aqt.utils import showInfo
from aqt import gui_hooks
from .config_manager import ConfigManager
from .config_ui import ConfigDialog

config_manager = ConfigManager("batch_note_change_config", "global_config")

# Load merged config from config_manager
config = config_manager.load()
# Compatibility shim: Tries multiple import paths to ensure compatibility with different Anki versions' change note type dialogs
try:
    from aqt.dialogs import changeNoteType as _change_note_type_fn
    _run_change_note_type = lambda browser, nids, mid: _change_note_type_fn(browser, nids, mid)
except ImportError:
    try:
        from aqt.change import changeNoteType as _change_note_type_fn
        _run_change_note_type = lambda browser, nids, mid: _change_note_type_fn(browser, nids, mid)
    except ImportError:
        from aqt.changenotetype import ChangeNotetypeDialog
        _run_change_note_type = lambda browser, nids, mid: ChangeNotetypeDialog(browser, browser.mw, nids, mid).exec_()


# Scans all note types and deletes those with zero associated cards from the collection.
def delete_empty_note_types():
    from fnmatch import fnmatch
    col = mw.col
    # Load protected note types from config (supports wildcards)
    protected = config.get("delete_empty_notes_config", {}).get("protected_notes", [])
    models = col.models.all()
    deleted = 0
    for model in models:
        model_name = model.get("name", "")
        # Skip deletion for any model whose name matches a protected pattern (wildcard supported)
        if any(fnmatch(model_name, pattern) for pattern in protected):
            continue  # Skip protected note types
        cards = col.db.scalar("SELECT COUNT() FROM cards WHERE nid IN (SELECT id FROM notes WHERE mid=?)", model["id"])
        if cards == 0:
            col.models.rem(model)
            deleted += 1
    mw.reset()
    showInfo(f"Deleted {deleted} note types with zero cards.")
