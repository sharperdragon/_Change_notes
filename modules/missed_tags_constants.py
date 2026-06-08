# pyright: reportMissingImports=false
from __future__ import annotations

# ! ----------------------------- CONFIG SECTIONS -----------------------------
CANONICAL_CONFIG_SECTION = "tag_missed_notes"
# ! -------------------------------------------------------------------------
# Show or hide the "Base" action in the Missed Tags menu.
# Canonical config key: actions.base.menu_display
SHOW_BASE_ACTION_IN_MISSED_TAGS_MENU = True

# ! --------------------------- CHANGE-PRONE VALUES ---------------------------
SCHEDULE_POLICY = {
    "unknown": "unknown",
    "next": "next",
}
DEFAULT_OPEN_ENDED_ROTATION_END = "2099-12-31"
MISSED_CONTEXT_PARENT_TAG_SEGMENT = "Block"
LEGACY_MISSED_CONTEXT_PARENT_TAG_SEGMENT = "Rotation"

# UWorld grouping for numeric test tags:
#   parent range (for example, 001-050) -> child range (for example, 01-05).
DEFAULT_UWORLD_PARENT_RANGE_BLOCK_SIZE = 50
DEFAULT_UWORLD_CHILD_RANGE_BLOCK_SIZE = 5
DEFAULT_PARENT_RANGE_PAD_WIDTH = 3
# Keep True to include child range like:
#   ##Missed-Qs::*UW_Tests::051-100::96-100::96
# Set False only if you intentionally want:
#   ##Missed-Qs::*UW_Tests::051-100::96
INCLUDE_UWORLD_CHILD_RANGE_SEGMENT = True
CANONICAL_UWORLD_TAG_SEGMENT = "*UW_Tests"
ACTION_KEY_CORRECT_TAG_MISSED_PROMPT = "correct_tag_missed_prompt"
CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY = "correct_tag_missed"
LEGACY_CORRECT_TAG_MISSED_ACTION_KEY = "uw_correct_missed"
DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL = "UW Correct + Missed Tag"
CORRECT_MARKED_TAG_SEGMENT = "correct_marked"
UWORLD_CORRECT_MISSED_SOURCE_KEY = "uw_correct_missed_source"
UWORLD_CORRECT_MISSED_SOURCE_OPTIONS = ("UWorld", "NBME", "Amboss", "Other")

PROMPT_BEHAVIOR_BASE_PLUS_ROTATION = "base_plus_rotation"
PROMPT_BEHAVIOR_BASE_ONLY = "base_only"

PROMPT_STYLE_ROTATION_THEN_NUMBER = "rotation_then_number"
PROMPT_STYLE_RANGE_THEN_NUMBER = "range_then_number"
PROMPT_STYLE_NUMBER_ONLY = "number_only"
PROMPT_KIND_NONE = "none"
PROMPT_KIND_NUMBER = "number"
PROMPT_KIND_FORM = "form"
VALID_PROMPT_KINDS = {
    PROMPT_KIND_NONE,
    PROMPT_KIND_NUMBER,
    PROMPT_KIND_FORM,
}
VALID_PROMPT_NUMBER_STYLES = {
    PROMPT_STYLE_ROTATION_THEN_NUMBER,
    PROMPT_STYLE_RANGE_THEN_NUMBER,
    PROMPT_STYLE_NUMBER_ONLY,
}
VALID_PROMPT_BLANK_BEHAVIORS = {
    PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
    PROMPT_BEHAVIOR_BASE_ONLY,
}

# Amboss prompt behavior: when enabled, any non-empty prompt text is converted
# into child tag segments under Amboss::<rotation>.
AMBOSS_ALLOW_FREEFORM_CHILD_SEGMENTS = True
AMBOSS_FREEFORM_INCLUDE_ROTATION_SEGMENT = False

MSG_NO_NOTES_SELECTED = "❌ No notes selected."
MSG_INVALID_INTEGER_TEST_NUMBER = "❌ Please enter a valid integer test number."
MSG_INVALID_NBME_INPUT = "❌ Please enter a positive form number or a tag path."
MSG_INVALID_CORRECT_GUESS_SUBTAG = "❌ Subtag cannot include spaces."
MSG_INVALID_CORRECT_MARKED_SOURCE_INPUT = "❌ Please enter a value."
PROMPT_DEFAULT_TITLE = "Enter Test Number"
PROMPT_DEFAULT_LABEL = "Test #:"
PROMPT_NBME_TITLE = "Enter NBME Form or Path"
PROMPT_NBME_LABEL = "Form # or path:"
PROMPT_AMBOSS_TITLE = "Enter Amboss Subtag"
PROMPT_AMBOSS_LABEL = "Subtags:"
# Checkbox label used on every prompt that can append the correct_marked tag.
PROMPT_CORRECT_MARKED_CHECKBOX_LABEL = "Correct+Marked"
AMBOSS_CORRECT_MARKED_TAG_SEGMENT = "correct_marked"
AMBOSS_APPEND_CORRECT_MARKED_STATE_KEY = "amboss_append_correct_marked"
AMBOSS_APPEND_CORRECT_MARKED_DEFAULT = False
PROMPT_SHOW_CORRECT_MARKED_CHECKBOX_DEFAULT = False
PROMPT_UWORLD_TITLE = "Enter UWorld Test Number"
PROMPT_TRUE_LEARN_TITLE = "Enter True-Learn Test Number"
PROMPT_CORRECT_GUESS_SUBTAG_TITLE = "Guessed Correct Subtag"
PROMPT_CORRECT_GUESS_SUBTAG_LABEL = "Optional subtag (no spaces):"

# ! -------------------------------------------------------------------------

# ? Exclude list for auto-added rotation/month context tags.
EXCLUDE_AUTO_MISS = {
    "add_key_info_action",
    "base_plain",
    "correct_guess",
}

DEFAULT_ACTION_ADD_MISSED_DATE_CONTEXT = {
    "add_key_info_action": False,
    "base_plain": False,
    "correct_guess": False,
    "uw_test_prompt": True,
    ACTION_KEY_CORRECT_TAG_MISSED_PROMPT: True,
    "nbme_form_prompt": True,
    "amboss_test_prompt": True,
    "multi_missed": True,
    "other_resource": True,
    "true_learn_test_prompt": True,
}

STANDARD_ACTION_SCHEMA_KEYS = (
    "menu_label",
    "child_of_primary_missed",
    "absolute_tags",
    "tag_segment",
)
STANDARD_ACTION_SCHEMA_KEYS_WITH_PROMPT = (*STANDARD_ACTION_SCHEMA_KEYS, "prompt")
STANDARDIZED_ACTION_SCHEMA_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("base", STANDARD_ACTION_SCHEMA_KEYS),
    ("uworld", STANDARD_ACTION_SCHEMA_KEYS_WITH_PROMPT),
    ("nbme", STANDARD_ACTION_SCHEMA_KEYS_WITH_PROMPT),
    ("amboss", STANDARD_ACTION_SCHEMA_KEYS_WITH_PROMPT),
    ("multi_missed", STANDARD_ACTION_SCHEMA_KEYS),
    ("key_info", STANDARD_ACTION_SCHEMA_KEYS),
    ("correct_guess", STANDARD_ACTION_SCHEMA_KEYS),
    (CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY, STANDARD_ACTION_SCHEMA_KEYS),
)
ACTION_DATE_CONTEXT_RESOLUTION_SPECS: tuple[tuple[str, str, str], ...] = (
    ("base_plain", "base", "base_plain"),
    ("uw_test_prompt", "uworld", "uw_test_prompt"),
    ("nbme_form_prompt", "nbme", "nbme_form_prompt"),
    ("amboss_test_prompt", "amboss", "amboss_test_prompt"),
    ("multi_missed", "multi_missed", "multi_missed"),
    ("add_key_info_action", "key_info", "add_key_info_action"),
    ("correct_guess", "correct_guess", "correct_guess"),
    (
        ACTION_KEY_CORRECT_TAG_MISSED_PROMPT,
        CANONICAL_CORRECT_TAG_MISSED_ACTION_KEY,
        ACTION_KEY_CORRECT_TAG_MISSED_PROMPT,
    ),
)
