"""Scheduling-specific compatibility wrapper around shared similarity helpers."""

from ..shared.text_similarity import (
    clean_img_tag,
    extract_images,
    extract_srcs,
    group_note_ids_by_similarity,
    group_similar_notes_by_content,
    normalize,
)

from PyQt6.QtWidgets import QInputDialog

from aqt import mw


def prompt_threshold_with_cancel(default=0.94, parent=None):
    """Prompt user for similarity threshold and return (threshold, accepted)."""
    try:
        default_float = float(default)
    except Exception:
        default_float = 0.94
    if default_float > 1.0:
        default_float = default_float / 100.0
    default_int = max(0, min(int(default_float * 100), 100))

    dialog_parent = parent or mw
    val, ok = QInputDialog.getInt(
        dialog_parent,
        "Set Similarity Threshold",
        "Enter similarity threshold (0 = loose, 100 = strict):",
        default_int,
        0,
        100,
        1,
    )
    if not ok:
        return default_float, False
    return val / 100.0, True


def prompt_threshold(default=94, parent=None):
    """Backward-compatible wrapper returning only threshold."""
    threshold, _ = prompt_threshold_with_cancel(default=default, parent=parent)
    return threshold


def merge_images_main():
    """Legacy no-op placeholder retained for compatibility."""
    return None
