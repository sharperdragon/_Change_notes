"""Shared helpers for _Change_notes modules."""

from .defaults import (
    ADD_CUSTOM_TAGS_DEFAULTS,
    ADD_MISSED_TAGS_DEFAULTS,
    ADD_TABLE_CLASS_DEFAULTS,
    IMG_TAGS_MERGE_DEFAULTS,
    MERGE_IMAGES_DEFAULTS,
    MERGE_SCHEDULE_DEFAULTS,
    MERGE_TAGS_DEFAULTS,
    TAG_DUPES_DEFAULTS,
    clone_defaults,
)
from .parsing import parse_bool

__all__ = [
    "ADD_CUSTOM_TAGS_DEFAULTS",
    "ADD_MISSED_TAGS_DEFAULTS",
    "ADD_TABLE_CLASS_DEFAULTS",
    "IMG_TAGS_MERGE_DEFAULTS",
    "MERGE_IMAGES_DEFAULTS",
    "MERGE_SCHEDULE_DEFAULTS",
    "MERGE_TAGS_DEFAULTS",
    "TAG_DUPES_DEFAULTS",
    "clone_defaults",
    "parse_bool",
]
