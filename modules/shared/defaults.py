"""Shared fallback defaults for _Change_notes modules.

These values are Python-side guard defaults used when config keys are missing
or malformed. User-editable defaults still live in `configs/*.json`.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TypeVar

T = TypeVar("T")


def clone_defaults(value: T) -> T:
    """Return a deep copy so callers can mutate safely."""
    return deepcopy(value)


ADD_CUSTOM_TAGS_DEFAULTS = {
    "submenu_label": "Custom Tags",
}


ADD_MISSED_TAGS_DEFAULTS = {
    "ui": {
        "menu_label": "Missed Tags ❌",
    },
    "rotation": {
        "schedule": [
            {"label": "IM1", "start": "2025-06-30", "end": "2025-07-25"},
            {"label": "FM2", "start": "2025-07-28", "end": "2025-08-22"},
            {"label": "ACM", "start": "2025-08-25", "end": "2025-09-05"},
            {"label": "OMM", "start": "2025-09-08", "end": "2025-09-18"},
            {"label": "Surgery", "start": "2025-09-22", "end": "2025-10-17"},
            {"label": "IM2", "start": "2025-10-20", "end": "2025-11-14"},
            {"label": "FM1", "start": "2025-11-17", "end": "2025-12-12"},
            {"label": "Winter-break", "start": "2025-12-13", "end": "2026-01-04"},
            {"label": "Pediatrics", "start": "2026-01-05", "end": "2026-01-30"},
            {"label": "OBGYN", "start": "2026-02-02", "end": "2026-02-27"},
            {"label": "Psych", "start": "2026-03-02", "end": "2026-03-27"},
        ],
        "exhausted_policy": "unknown",
        "parent_tag_segment": "Rotation",
        "winter_break_label": "Winter-break",
        "post_rotation_label": "Dedicated",
    },
    "actions": {
        "base": {
            "label": "♦️Base",
            "tags": ["##Missed-Qs"],
        },
        "uworld": {
            "label": "🛃UWorld",
            "base_tags": ["##Missed-Qs::UW_Tests"],
            "default_tag_prefix": "UW_Tests",
            "test_range_block_size": 25,
        },
        "nbme": {
            "label": "🧠NBME",
            "base_tags": ["##Missed-Qs::NBME"],
            "default_tag_prefix": "NBME",
        },
        "amboss": {
            "label": "🦠Amboss",
            "base_tag": "##Missed-Qs::Amboss",
            "blank_behavior": "base_plus_rotation",
            "number_style": "rotation_then_number",
            "remove_from_other_menu": True,
        },
        "multi_missed": {
            "label": "2x Missed 📌",
            "tag_segment": "2x",
        },
        "key_info": {
            "label": "Key Info 🗝️",
            "tag_base": "#Custom::#KEY",
        },
        "correct_guess": {
            "label": "Guessed Correct 🎫",
            "tags": ["#Custom::correct_marked"],
            "include_rotation": True,
            "rotation_lowercase": True,
            "unknown_segment": "unknown",
        },
        "other": {
            "resources": ["Kaplan", "True-Learn", "NBOME"],
            "tag_suffix": "Other",
        },
    },
    "Q_Banks": ["UWORLD", "NBME"],
}


MERGE_IMAGES_DEFAULTS = {
    "default_threshold": 0.90,
    "min_threshold": 0.80,
    "ask_threshold_each_time": True,
    "allowed_models": [],
    "excluded_tags": ["First_Aid"],
    "fields_to_scan_for_images": [
        "Extra",
        "Extra2",
        "Extra3",
        "Extra4",
        "Extra5",
        "Extra6",
        "Extra7",
        "Button",
        "Front",
    ],
    "merge_behavior": {
        "wrap_images_in_div": True,
        "insert_new_line_between_images": True,
        "append_to_existing_field": True,
        "copy_sketchy_links": True,
    },
    "logging": {
        "enable_log_popup": True,
        "save_log_to_desktop": True,
        "log_filename_prefix": "merged_images_log_",
    },
    "tagging": {
        "add_to_merged": "IMG_Uni::received",
        "add_to_donor": "IMG_Uni::donor",
        "add_to_unchanged": "IMG_Uni::same",
    },
}


IMG_TAGS_MERGE_DEFAULTS = {
    "global_fuzzy_opts": {
        "default_fuzz": 0.96,
        "min_fuzz": 0.78,
        "max_fuzz": 1.00,
    },
    "merge_images_and_tags_config": {},
}


MERGE_SCHEDULE_DEFAULTS = {
    "merge_similarity_threshold": 0.94,
    "abort_on_cancel": True,
    "multi_card_policy": "skip",
    "multi_card_policies": ("skip", "first_card", "all_cards"),
}


ADD_TABLE_CLASS_DEFAULTS = {
    "apply_to_existing_classes": True,
    "log_path": "~/Desktop/anki_logs/Add_table_class_log.txt",
}


MERGE_TAGS_DEFAULTS = {
    "base_tag": "TAGS_MERGED",
    "comparison_field": "Text",
    "merge_select_only": False,
    "prompt_default_fuzzy": 0.98,
    "run_default_fuzzy": 0.97,
    "min_fuzzy": 0.80,
    "max_fuzzy": 1.0,
    "ask_fuzzy_each_time": True,
}


TAG_DUPES_DEFAULTS = {
    "base_tag": "DUPE_Tagging",
    "comparison_field": "Text",
    "tag_unmatched": False,
    "multi_tag_child": "multiple",
    "log_folder": "logs",
    "prompt_fuzzy_threshold": 98,
}


__all__ = [
    "ADD_CUSTOM_TAGS_DEFAULTS",
    "ADD_MISSED_TAGS_DEFAULTS",
    "MERGE_IMAGES_DEFAULTS",
    "IMG_TAGS_MERGE_DEFAULTS",
    "MERGE_SCHEDULE_DEFAULTS",
    "ADD_TABLE_CLASS_DEFAULTS",
    "MERGE_TAGS_DEFAULTS",
    "TAG_DUPES_DEFAULTS",
    "clone_defaults",
]
