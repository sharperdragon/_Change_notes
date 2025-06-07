from aqt import mw
from aqt.utils import showInfo

def delete_empty_note_types():
    """Delete all note types that currently have zero cards."""
    col = mw.col
    models = col.models.all()
    deleted = 0
    for model in models:
        count = col.db.scalar(
            "SELECT COUNT() FROM cards WHERE nid IN "
            "(SELECT id FROM notes WHERE mid=?)",
            model["id"]
        )
        if count == 0:
            col.models.rem(model)
            deleted += 1
    mw.reset()
    showInfo(f"Deleted {deleted} note types with zero cards.")