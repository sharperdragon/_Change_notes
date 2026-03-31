from aqt import mw
from ..config_manager import ConfigManager

config_manager = ConfigManager("delete_empty_notes_config")


def delete_empty_note_types():
    from fnmatch import fnmatch
    from aqt.utils import showInfo, showText, askUser

    col = mw.col

    # Use effective section config (defaults from configs/ + profile override).
    protected = list(config_manager.reload().get("protected_notes", []))

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
