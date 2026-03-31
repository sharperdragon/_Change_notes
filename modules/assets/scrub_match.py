"""Backward-compatible wrapper around shared text similarity helpers."""

from ..shared.text_similarity import (
    clean_img_tag,
    extract_images,
    extract_srcs,
    group_note_ids_by_similarity,
    group_similar_notes_by_content,
    normalize,
)


def merge_images_main():
    """Legacy no-op placeholder retained for compatibility."""
    return None

