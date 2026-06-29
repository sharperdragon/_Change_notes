"""Shared fallback defaults for _Change_notes modules.

These values are Python-side guard defaults used when config keys are missing
or malformed. User-editable defaults live in the root `config.json`.
"""

from __future__ import annotations

from copy import deepcopy
from typing import TypeVar

T = TypeVar("T")


def clone_defaults(value: T) -> T:
    """Return a deep copy so callers can mutate safely."""
    return deepcopy(value)


ADD_CUSTOM_TAGS_DEFAULTS = {
    "menu_label": "Custom Tags",
}


ADD_MISSED_TAGS_DEFAULTS = {
    "ui": {
        "menu_label": "Missed Tags ❌",
    },
    "date": {
        "include_day_segment": True,
        "split_weeks": False,
    },
    "block": {
        "schedule": [
            {"segment_label": "*Dedicated", "start": "2026-03-28", "end": "2099-12-31"},
        ],
        "exhausted_policy": "unknown",
        "parent_tag_segment": "Block",
    },
    "actions": {
        "base": {
            "label": "♦️Base",
            "tags": ["##Missed-Qs"],
            "menu_display": True,
            "show_in_menu": True,
        },
        "uworld": {
            "label": "🛃UWorld",
            "base_tags": ["##Missed-Qs::*UW_Tests"],
            "default_tag_prefix": "*UW_Tests",
            "test_parent_range_block_size": 50,
            "test_range_block_size": 5,
            "prompt": {
                "show_correct_marked_checkbox": False,
            },
        },
        "nbme": {
            "label": "🧠NBME",
            "base_tags": ["##Missed-Qs::NBME"],
            "default_tag_prefix": "NBME",
            "prompt": {
                "show_correct_marked_checkbox": False,
            },
        },
        "amboss": {
            "label": "🦠Amboss",
            "base_tag": "##Missed-Qs::Amboss",
            "blank_behavior": "base_plus_rotation",
            "number_style": "rotation_then_number",
            "remove_from_other_menu": True,
            "prompt": {
                "show_correct_marked_checkbox": False,
            },
        },
        "multi_missed": {
            "label": "2x Missed 📌",
            "tag_segment": "*2x",
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
        "correct_tag_missed": {
            "label": "UW Correct + Missed Tag",
            "tag_segment": "correct_marked",
            "add_missed_date_context": True,
        },
        "other": {
            "submenu_bool": True,
            "submenu_label": "Other",
            "resources": ["Kaplan", "True-Learn"],
            "tag_suffix": "Other",
        },
    },
}


MERGE_IMAGES_DEFAULTS = {
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
        "add_to_merged": "DONE::IMG_Uni::{MM-DD}::received",
        "add_to_donor": "DONE::IMG_Uni::{MM-DD}::donor",
        "add_to_unchanged": "IMG_Uni::same",
    },
}


IMG_TAGS_MERGE_DEFAULTS = {
    "fuzzy_opts": {
        "default_fuzz": 0.96,
        "min_fuzz": 0.78,
    },
    "merge_images_and_tags_config": {},
}


MERGE_SCHEDULE_DEFAULTS = {
    "merge_similarity_threshold": 0.94,
    "multi_card_policy": "skip",
    "multi_card_policies": ("skip", "first_card", "all_cards"),
}


ADD_TABLE_CLASS_DEFAULTS = {
    "apply_to_existing_classes": True,
    "log_path": "~/Desktop/anki_logs/Add_table_class_log.txt",
}


MERGE_TAGS_DEFAULTS = {
    "base_tag": "DONE::TAGS_MERGED",
    "comparison_field": "Text",
    "merge_select_only": False,
    "excluded_tags": [],
    "prompt_default_fuzzy": 0.98,
    "run_default_fuzzy": 0.97,
    "min_fuzzy": 0.80,
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
