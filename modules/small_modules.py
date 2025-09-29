import os
from collections import defaultdict
from datetime import datetime

from aqt import mw
from aqt.qt import QAction, QInputDialog, QMenu
from aqt.browser import Browser
from aqt.utils import showInfo
from aqt import gui_hooks
from ..config_manager import ConfigManager

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


def delete_empty_note_types():
    from fnmatch import fnmatch
    from pathlib import Path
    import json
    from aqt.utils import showInfo, showText, askUser

    col = mw.col

    # --- Load protected patterns from file or merged config ---
    protected = []
    try:
        cfg_path = Path("/Users/claytongoddard/Library/Application Support/Anki2/addons21/_Change_notes/config.json")
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            protected = list(data.get("delete_empty_notes_config", {}).get("protected_notes", []))
    except Exception:
        # fall through to config dict if file missing/malformed
        pass

    if not protected:
        protected = list(config.get("delete_empty_notes_config", {}).get("protected_notes", []))

    models = col.models.all()
    to_delete_names = []

    for model in models:
        model_name = model.get("name", "")
        # Skip protected patterns (supports wildcards via fnmatch)
        if any(fnmatch(model_name, pattern) for pattern in protected):
            continue
        cards = col.db.scalar(
            "SELECT COUNT() FROM cards WHERE nid IN (SELECT id FROM notes WHERE mid=?)",
            model["id"],
        )
        if cards == 0:
            to_delete_names.append(model_name)

    if not to_delete_names:
        showInfo("No note types have zero cards.")
        return

    # --- Show full list in a scrollable window (prevents too-tall popups) ---
    # showText is scrollable and includes a Copy button; safe on small screens.
    header = f"Note types with zero cards ({len(to_delete_names)}):\n"
    body = "\n".join(f"- {name}" for name in sorted(to_delete_names, key=str.lower))
    showText(header + body, title="Empty Note Types", copyBtn=True)

    # --- Keep the confirmation short ---
    if not askUser(f"Delete these {len(to_delete_names)} note types now?\n"
                   f"(Full list shown in the previous window)"):
        showInfo("Deletion cancelled.")
        return

    # --- Perform deletion ---
    by_name = {m.get("name", ""): m for m in col.models.all()}
    deleted = 0
    for name in to_delete_names:
        m = by_name.get(name)
        if m:
            col.models.rem(m)
            deleted += 1

    mw.reset()
    showInfo(f"Deleted {deleted} note types with zero cards.")