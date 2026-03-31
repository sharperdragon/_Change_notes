# pyright: reportMissingImports=false
import re
from datetime import datetime
from typing import Any

from aqt.qt import QAction, QInputDialog, QMenu
from aqt.utils import showInfo, tooltip

from ..config_manager import ConfigManager

# ! ----------------------------- CONFIG SECTIONS -----------------------------
CONFIG_SECTION = "add_tags"
LEGACY_CONFIG_SECTION = "tag_selected_notes_config"
SCHEDULE_POLICY_UNKNOWN = "unknown"
SCHEDULE_POLICY_NEXT = "next"
# ! -------------------------------------------------------------------------

# ! ----------------------------- USER-TUNABLE CONSTANTS -----------------------------
# ? Base “missed” scaffolding
MISSED_BASE_TAG = ["##Missed-Qs"]  # former: tag_config["missed_base_tag"]
DEFAULT_COMQUEST_TAG_PREFIX = "COMQUEST"
ROTATION_PARENT_TAG_SEGMENT = "Rotation"
WINTER_BREAK_TAG_LABEL = "Winter-break"
POST_ROTATION_TAG_LABEL = "Dedicated"

# ? Month + rotation labels (now bare segments; the base "##Missed-Qs" is composed at use-time)
MULTI_MISS_TAG = "2x"
DEFAULT_TEST_TAG_PREFIX = "UW_Tests"
OTHER_SUFFIX = "Other"


# $ Compose a full Missed-Qs tag path with the base prefix
def base_tag_path(*parts: str) -> str:
    base = MISSED_BASE_TAG[0] if MISSED_BASE_TAG else "##Missed-Qs"
    return "::".join([base, *[p for p in parts if p]])


# ? UW / COMQUEST “subset” equivalents
SUBSET_1_NAME = "🛃UWorld"
SUBSET_1_TAG = ["##Missed-Qs::UW_Tests"]
SUBSET_2_NAME = "♿️COMQUEST"
SUBSET_2_TAG = ["##Missed-Qs::COMQUEST"]

# ? Other resources (flat actions + submenu)
OTHER_MENU_LABEL = "Other"
OTHER_RESOURCES = ["Kaplan", "True-Learn", "NBOME"]

# ? Amboss behavior (top-level + COMQUEST-style prompt)
AMBOSS_TOP_LEVEL_NAME = "🦠Amboss"
AMBOSS_BASE_TAG = "##Missed-Qs::Amboss"
AMBOSS_PROMPT_TITLE = "Enter Amboss Test Number"
AMBOSS_PROMPT_LABEL = "Test #:"
AMBOSS_BLANK_BEHAVIOR = "base_plus_rotation"
AMBOSS_NUMBER_STYLE = "rotation_then_number"
AMBOSS_REMOVE_FROM_OTHER_MENU = True

# ? Special actions
KEY_TAG_BASE = "#Custom::#Shelf"
KEY_INFO_SUFFIX = "*KEY"
CORRECT_GUESS_TAGS = ["#Custom::correct_marked"]
CORRECT_GUESS_INCLUDE_ROTATION = True
CORRECT_GUESS_ROTATION_LOWERCASE = True
CORRECT_GUESS_UNKNOWN_SEGMENT = "unknown"
ACTION_KEY_BASE_PLAIN = "base_plain"
ACTION_KEY_KEY_INFO = "add_key_info_action"
ACTION_KEY_CORRECT_GUESS = "correct_guess"
ACTION_KEY_COMQUEST_TEST_PROMPT = "comquest_test_prompt"
ACTION_KEY_UWORLD_TEST_PROMPT = "uw_test_prompt"
ACTION_KEY_AMBOSS_TEST_PROMPT = "amboss_test_prompt"
ACTION_KEY_TRUE_LEARN_TEST_PROMPT = "true_learn_test_prompt"
ACTION_KEY_OTHER_RESOURCE = "other_resource"

# ? Prompt constants
PROMPT_LABEL_TEST_NUMBER = "Test #:"
PROMPT_TITLE_COMQUEST = "Enter COMQUEST Test Number"
PROMPT_TITLE_UWORLD = "Enter UWorld Test Number"
PROMPT_TITLE_TRUE_LEARN = "Enter True-Learn Test Number"
PROMPT_BEHAVIOR_BASE_PLUS_ROTATION = "base_plus_rotation"
PROMPT_BEHAVIOR_BASE_ONLY = "base_only"
PROMPT_STYLE_ROTATION_THEN_NUMBER = "rotation_then_number"
PROMPT_STYLE_RANGE_THEN_NUMBER = "range_then_number"

# ? Exclude list for “auto-missed” context
EXCLUDE_AUTO_MISS = [
    ACTION_KEY_KEY_INFO,
    ACTION_KEY_BASE_PLAIN,
    ACTION_KEY_CORRECT_GUESS,
]


# ! --------------------------- END USER-TUNABLE CONSTANTS ---------------------------


# $ Helpers to resolve base tags without changing the top config
def _get_list(name: str):
    v = globals().get(name)
    return v if isinstance(v, list) and v else []


def _uw_base_tag() -> str:
    # Prefer a value that looks like UW
    for name in ("SUBSET_1_TAGS", "SUBSET_1_TAG", "SUBSET_2_TAGS", "SUBSET_2_TAG"):
        for cand in _get_list(name):
            if "UW_Base" in cand or "::UW" in cand:
                return cand
    # Fallback to composed default
    return base_tag_path(DEFAULT_TEST_TAG_PREFIX)


def _comquest_base_tag() -> str:
    # Prefer a value that looks like COMQUEST
    for name in ("SUBSET_2_TAGS", "SUBSET_2_TAG", "SUBSET_1_TAGS", "SUBSET_1_TAG"):
        for cand in _get_list(name):
            if "COMQUEST_Base" in cand or "COMQUEST" in cand:
                return cand
    # Fallback to explicit default
    return base_tag_path(DEFAULT_COMQUEST_TAG_PREFIX)


TEST_RANGE_BLOCK_SIZE = 25


DEFAULT_ROTATION_SCHEDULE = [
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
]
ROTATION_SCHEDULE: list[tuple[str, str, str]] = []
SCHEDULE_EXHAUSTED_POLICY = SCHEDULE_POLICY_UNKNOWN
_ROTATION_WARNING = ""


def scrub_resource_label_to_tag(label: str) -> str:
    missed_base = str(label).strip()
    missed_base = re.sub(r"[^A-Za-z0-9\- ]+", "", missed_base)
    missed_base = re.sub(r"\s+", " ", missed_base).strip()
    return missed_base


def _to_string_list(value: Any, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        out = [str(v).strip() for v in value if str(v).strip()]
        return out or list(fallback)
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return list(fallback)


def _normalize_rotation_schedule(raw: Any) -> list[tuple[str, str, str]]:
    normalized: list[tuple[str, str, str]] = []
    if not isinstance(raw, list):
        return normalized

    for item in raw:
        label = start = end = ""
        if isinstance(item, dict):
            label = str(item.get("label", "")).strip()
            start = str(item.get("start", "")).strip()
            end = str(item.get("end", "")).strip()
        elif isinstance(item, (list, tuple)) and len(item) >= 3:
            label = str(item[0]).strip()
            start = str(item[1]).strip()
            end = str(item[2]).strip()

        if not label or not start or not end:
            continue
        try:
            datetime.strptime(start, "%Y-%m-%d")
            datetime.strptime(end, "%Y-%m-%d")
        except Exception:
            continue

        normalized.append((label, start, end))
    return normalized


def _reload_runtime_config():
    global MISSED_BASE_TAG
    global SUBSET_1_NAME
    global SUBSET_1_TAG
    global SUBSET_2_NAME
    global SUBSET_2_TAG
    global OTHER_MENU_LABEL
    global OTHER_RESOURCES
    global ROTATION_SCHEDULE
    global SCHEDULE_EXHAUSTED_POLICY

    legacy_cfg = ConfigManager(LEGACY_CONFIG_SECTION).load()
    section_cfg = ConfigManager(CONFIG_SECTION).load()
    merged_cfg = ConfigManager.deep_merge_dicts(
        legacy_cfg if isinstance(legacy_cfg, dict) else {},
        section_cfg if isinstance(section_cfg, dict) else {},
    )

    MISSED_BASE_TAG = _to_string_list(
        merged_cfg.get("base_missed_tag", merged_cfg.get("missed_base_tag", MISSED_BASE_TAG)),
        fallback=MISSED_BASE_TAG,
    )
    SUBSET_1_NAME = str(merged_cfg.get("subset_1_name", SUBSET_1_NAME)).strip() or SUBSET_1_NAME
    SUBSET_2_NAME = str(merged_cfg.get("subset_2_name", SUBSET_2_NAME)).strip() or SUBSET_2_NAME
    SUBSET_1_TAG = _to_string_list(
        merged_cfg.get("subset_tag_1", merged_cfg.get("subset_1_tag", SUBSET_1_TAG)),
        fallback=SUBSET_1_TAG,
    )
    SUBSET_2_TAG = _to_string_list(
        merged_cfg.get("subset_tag_2", merged_cfg.get("subset_2_tag", SUBSET_2_TAG)),
        fallback=SUBSET_2_TAG,
    )

    other_menu = merged_cfg.get("other_menu", {})
    if isinstance(other_menu, dict):
        OTHER_MENU_LABEL = str(other_menu.get("label", OTHER_MENU_LABEL)).strip() or OTHER_MENU_LABEL
        OTHER_RESOURCES = _to_string_list(
            other_menu.get("resources", OTHER_RESOURCES),
            fallback=OTHER_RESOURCES,
        )

    schedule_raw = merged_cfg.get("rotation_schedule", DEFAULT_ROTATION_SCHEDULE)
    parsed_schedule = _normalize_rotation_schedule(schedule_raw)
    if not parsed_schedule:
        parsed_schedule = _normalize_rotation_schedule(DEFAULT_ROTATION_SCHEDULE)
    ROTATION_SCHEDULE = parsed_schedule

    policy = str(merged_cfg.get("schedule_exhausted_policy", SCHEDULE_POLICY_UNKNOWN)).strip().lower()
    if policy not in {SCHEDULE_POLICY_UNKNOWN, SCHEDULE_POLICY_NEXT}:
        policy = SCHEDULE_POLICY_UNKNOWN
    SCHEDULE_EXHAUSTED_POLICY = policy


_reload_runtime_config()


def get_missed_month_tag() -> str:
    now = datetime.now()
    return f"{MISSED_BASE_TAG[0]}::{now.year}::{now.strftime('%m')}_{now.strftime('%B')}"


def _set_rotation_warning(message: str):
    global _ROTATION_WARNING
    _ROTATION_WARNING = message.strip()


def get_rotation_key_info_tag() -> str:
    """Return the KEY info tag for the current/next rotation, using numbered segment.

    Example: '#Custom::#Shelf::07_FM1::*KEY'
    """
    segment = get_rotation_segment()
    return f"{KEY_TAG_BASE}::{segment}::{KEY_INFO_SUFFIX}"


def get_current_or_next_rotation_meta():
    global _ROTATION_WARNING
    _ROTATION_WARNING = ""

    today = datetime.today().date()
    if not ROTATION_SCHEDULE:
        _set_rotation_warning("Rotation schedule is empty; using Unknown.")
        return "00", "Unknown"

    parsed = []
    for idx, (rotation, start_str, end_str) in enumerate(ROTATION_SCHEDULE, start=1):
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        parsed.append((idx, rotation, start, end))
        if start <= today <= end:
            return f"{idx:02d}", rotation

    if SCHEDULE_EXHAUSTED_POLICY == SCHEDULE_POLICY_NEXT:
        for idx, rotation, start, _ in parsed:
            if today < start:
                _set_rotation_warning(
                    f"No active rotation for {today.isoformat()}; using next window "
                    f"{rotation} ({start.isoformat()})."
                )
                return f"{idx:02d}", rotation

    last_end = parsed[-1][3]
    if today > last_end:
        post_label = str(POST_ROTATION_TAG_LABEL).strip()
        if post_label:
            # Post-rotation is an expected steady state when a suffix is configured.
            _set_rotation_warning("")
            return "00", post_label
        _set_rotation_warning(f"No rotation configured after {last_end.isoformat()}; using Unknown.")
    else:
        _set_rotation_warning(f"No rotation configured for {today.isoformat()}; using Unknown.")
    return "00", "Unknown"


def _rotation_label_matches(actual: str, expected: str) -> bool:
    return str(actual or "").strip().lower() == str(expected or "").strip().lower()


def get_formatted_rotation_segment(rot_num_2d: str, rot_label: str) -> str:
    """Return canonical rotation segment for tags.

    - Winter break -> "Winter-break"
    - Post-rotation -> POST_ROTATION_TAG_LABEL
    - Active rotation -> "NN_Label"
    - Unknown -> "00_Unknown"
    """
    label = str(rot_label or "").strip()
    if not label:
        return "00_Unknown"

    if _rotation_label_matches(label, WINTER_BREAK_TAG_LABEL):
        return WINTER_BREAK_TAG_LABEL

    if _rotation_label_matches(label, POST_ROTATION_TAG_LABEL):
        return POST_ROTATION_TAG_LABEL

    if label == "Unknown":
        return "00_Unknown"

    rot_num = str(rot_num_2d or "00").strip() or "00"
    return f"{rot_num}_{label}"


def get_rotation_segment() -> str:
    """Return canonical rotation segment for current/next rotation."""
    rot_num_2d, rot_label = get_current_or_next_rotation_meta()
    return get_formatted_rotation_segment(rot_num_2d, rot_label)


def get_correct_guess_rotation_segment() -> str:
    _, rot_label = get_current_or_next_rotation_meta()
    raw = str(rot_label or CORRECT_GUESS_UNKNOWN_SEGMENT).strip()
    raw = raw if raw else CORRECT_GUESS_UNKNOWN_SEGMENT
    slug = re.sub(r"\s+", "-", raw)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "", slug)
    if not slug:
        slug = CORRECT_GUESS_UNKNOWN_SEGMENT
    return slug.lower() if CORRECT_GUESS_ROTATION_LOWERCASE else slug


def get_correct_guess_tags() -> list[str]:
    if not CORRECT_GUESS_INCLUDE_ROTATION:
        return list(CORRECT_GUESS_TAGS)

    rotation_segment = get_correct_guess_rotation_segment()
    return [f"{base_tag}::{rotation_segment}" for base_tag in CORRECT_GUESS_TAGS]


def get_missed_tag_for_rotation() -> str:
    """Rotation context tag for missed questions.

    Default example: '##Missed-Qs::Rotation::07_FM1'
    Winter break example: '##Missed-Qs::Rotation::Winter-break'
    Post-rotation example: '##Missed-Qs::Rotation::Dedicated'
    """
    rot_num_2d, rot_label = get_current_or_next_rotation_meta()
    segment = get_formatted_rotation_segment(rot_num_2d, rot_label)
    return base_tag_path(ROTATION_PARENT_TAG_SEGMENT, segment)


def _add_tag_safe(note, tag: str):
    if hasattr(note, "add_tag"):
        note.add_tag(tag)
    else:
        note.addTag(tag)


# ! Centralized tag applier: adds rotation (always) and month (unless excluded)
def apply_tags_to_selected_notes(browser, tag_list: list[str], action_key: str):
    _reload_runtime_config()
    global _ROTATION_WARNING
    _ROTATION_WARNING = ""

    col = browser.mw.col
    nids = browser.selectedNotes()
    if not nids:
        return
    # $ Build dynamic context tags
    final = list(tag_list or [])
    local_exclude = set(EXCLUDE_AUTO_MISS)
    # Append rotation + month only when NOT excluded
    if action_key not in local_exclude:
        final.append(get_missed_tag_for_rotation())
        final.append(get_missed_month_tag())

    # $ Deduplicate while preserving order
    seen = set()
    final_tags = []
    for t in final:
        if t and t not in seen:
            seen.add(t)
            final_tags.append(t)

    for nid in nids:
        note = col.get_note(nid)
        current = set(note.tags)
        for tag in final_tags:
            if tag not in current:
                _add_tag_safe(note, tag)
        note.flush()

    browser.model.reset()
    msg = f"✅ Applied {len(final_tags)} tags to {len(nids)} notes."
    if _ROTATION_WARNING:
        msg += f"\n⚠️ {_ROTATION_WARNING}"
    tooltip(msg)


# $ Add a plain "Base" action (no test/rotation/month)
def add_base_plain_action(browser, menu):
    action = QAction("♦️Base", browser)
    action.triggered.connect(
        lambda _: apply_tags_to_selected_notes(browser, MISSED_BASE_TAG, action_key=ACTION_KEY_BASE_PLAIN)
    )
    menu.addAction(action)


def add_tag_menu_items(browser, menu):
    _reload_runtime_config()

    tag_menu = QMenu(" 📝 Apply Tags ", browser)
    tag_menu.setStyleSheet("""
        QMenu::item {
            padding-top: 4.5px;
            padding-bottom: 4.5px;
            padding-left: 6px;
            padding-right: 6px;
        }
        QMenu::item:selected {
            background-color: rgba(120, 160, 255, 60);  /* subtle hover highlight */
        }
    """)

    add_uworld_tags(browser, tag_menu)
    add_COMQUEST_tag(browser, tag_menu)
    add_amboss_tag(browser, tag_menu)
    add_base_plain_action(browser, tag_menu)
    tag_menu.addSeparator()

    add_multi_tag(browser, tag_menu)
    tag_menu.addSeparator()

    add_key_info_action(browser, tag_menu)
    add_correct_guess_action(browser, tag_menu)
    tag_menu.addSeparator()

    add_other_resources_actions(browser, tag_menu)

    if tag_menu.actions():
        menu.addSeparator()
        menu.addMenu(tag_menu)


def add_COMQUEST_tag(browser, menu):
    base_tag = _comquest_base_tag()
    action = QAction(f"{SUBSET_2_NAME:<24}", browser)
    action.triggered.connect(
        make_test_prompt_handler(
            browser,
            base_tag,
            action_key=ACTION_KEY_COMQUEST_TEST_PROMPT,
            title=PROMPT_TITLE_COMQUEST,
            label=PROMPT_LABEL_TEST_NUMBER,
            blank_behavior=PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
            number_style=PROMPT_STYLE_ROTATION_THEN_NUMBER,
        )
    )
    menu.addAction(action)


def add_amboss_tag(browser, menu):
    action = QAction(f"{AMBOSS_TOP_LEVEL_NAME:<24}", browser)
    action.triggered.connect(
        make_test_prompt_handler(
            browser,
            AMBOSS_BASE_TAG,
            action_key=ACTION_KEY_AMBOSS_TEST_PROMPT,
            title=AMBOSS_PROMPT_TITLE,
            label=AMBOSS_PROMPT_LABEL,
            blank_behavior=AMBOSS_BLANK_BEHAVIOR,
            number_style=AMBOSS_NUMBER_STYLE,
        )
    )
    menu.addAction(action)


def add_multi_tag(browser, menu):
    multi_tag = base_tag_path(MULTI_MISS_TAG)
    multi_tag_label = f"{'2x Missed 📌':<24}"
    add_static_action(browser, menu, multi_tag_label, [multi_tag], action_key="multi_missed")


def add_uworld_tags(browser, menu):
    set_name = SUBSET_1_NAME
    base = _uw_base_tag()
    if set_name and base:
        padded_name = f"{set_name:<24}"
        action = QAction(padded_name, browser)
        action.triggered.connect(
            make_test_prompt_handler(
                browser,
                base,
                action_key=ACTION_KEY_UWORLD_TEST_PROMPT,
                title=PROMPT_TITLE_UWORLD,
                label=PROMPT_LABEL_TEST_NUMBER,
                blank_behavior=PROMPT_BEHAVIOR_BASE_ONLY,
                number_style=PROMPT_STYLE_RANGE_THEN_NUMBER,
            )
        )
        menu.addAction(action)


def add_other_resources_actions(browser, menu):
    """
    Builds the 'Other' submenu.

    - Kaplan / NBOME: simple 'Other::<Source>' tags.
    - True-Learn: behaves like COMQUEST, with rotation segment + optional test number:
        ##Missed-Qs::Other::True-Learn::<rotation-segment>::04
        (if blank test #: ##Missed-Qs::Other::True-Learn::<rotation-segment>)
    """
    for resource_name in OTHER_RESOURCES:
        label = str(resource_name).strip()
        canonical = scrub_resource_label_to_tag(resource_name)

        # Defensive guard if Amboss is ever re-added to OTHER_RESOURCES
        if AMBOSS_REMOVE_FROM_OTHER_MENU and canonical.lower() == "amboss":
            continue

        # * SPECIAL CASE: True-Learn uses rotation + optional test number
        if canonical == "True-Learn":
            # Base tag: "##Missed-Qs::Other::True-Learn"
            base_tag = base_tag_path(
                OTHER_SUFFIX,
                canonical,
            )

            action = QAction(label, browser)

            # Use the same factory used for COMQUEST, but with "Other::True-Learn"
            handler = make_test_prompt_handler(
                browser,
                base_tag,
                action_key=ACTION_KEY_TRUE_LEARN_TEST_PROMPT,
                title=PROMPT_TITLE_TRUE_LEARN,
                label=PROMPT_LABEL_TEST_NUMBER,
                blank_behavior=PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,  # blank → base_tag::<rotation-segment>
                number_style=PROMPT_STYLE_ROTATION_THEN_NUMBER,  # number → base_tag::<rotation-segment>::NN
            )

            action.triggered.connect(handler)
            menu.addAction(action)
            continue  # Skip the generic behavior for this resource

        # * DEFAULT: flat source tag under Other
        resource_tag = base_tag_path(
            OTHER_SUFFIX,
            canonical,
        )

        action = QAction(label, browser)

        def on_click(_, rtag=resource_tag):
            if not browser.selectedNotes():
                showInfo("❌ No notes selected.")
                return
            # -> e.g. "##Missed-Qs::Other::Kaplan"
            tags_to_apply = MISSED_BASE_TAG + [rtag]
            apply_tags_to_selected_notes(browser, tags_to_apply, action_key=ACTION_KEY_OTHER_RESOURCE)

        action.triggered.connect(on_click)
        menu.addAction(action)


def prompt_and_apply_test_tag(browser, base_tag: str, action_key: str):
    test_num, ok = QInputDialog.getText(browser, "Enter Test Number", "Test #:")
    if ok and test_num.strip():
        try:
            test_input = int(test_num.strip())
            lower = ((test_input - 1) // TEST_RANGE_BLOCK_SIZE) * TEST_RANGE_BLOCK_SIZE + 1
            upper = lower + TEST_RANGE_BLOCK_SIZE - 1
            range_tag = f"{lower}-{upper}"
            full_number_tag = f"{base_tag}::{range_tag}::{test_input:02d}"
            apply_tags_to_selected_notes(browser, [full_number_tag], action_key=action_key)
        except ValueError:
            showInfo("❌ Please enter a valid integer test number.")


# $ Factory: build a test-number prompt handler bound to a base_tag + action_key
def make_test_prompt_handler(
    browser,
    base_tag: str,
    action_key: str,
    title: str = "Enter Test Number",
    label: str = "Test #:",
    blank_behavior: str = "base_plus_rotation",
    number_style: str = "range_then_number",
):
    """
    blank_behavior:
      - "base_only"          -> blank/non-numeric -> base_tag
      - "base_plus_rotation" -> blank/non-numeric -> base_tag::<rotation-segment>

    number_style:
      - "range_then_number"    -> base_tag::<lower-upper>::NN
      - "rotation_then_number" -> base_tag::<rotation-segment>::NN
    """

    def on_trigger():
        # Prompt with no placeholder/default text
        test_num, ok = QInputDialog.getText(browser, title, label)
        if not ok:
            return
        test_num = (test_num or "").strip()
        rot_num_2d, rot_label = get_current_or_next_rotation_meta()
        rotation_segment = get_formatted_rotation_segment(rot_num_2d, rot_label)

        if test_num == "":
            if blank_behavior == "base_only":
                formatted_tag = f"{base_tag}"
            else:
                formatted_tag = f"{base_tag}::{rotation_segment}"
        else:
            try:
                tn = int(test_num)
            except ValueError:
                # Treat non-numeric like blank
                if blank_behavior == "base_only":
                    formatted_tag = f"{base_tag}"
                else:
                    formatted_tag = f"{base_tag}::{rotation_segment}"
            else:
                if number_style == "rotation_then_number":
                    formatted_tag = f"{base_tag}::{rotation_segment}::{tn:02d}"
                else:
                    lower = ((tn - 1) // TEST_RANGE_BLOCK_SIZE) * TEST_RANGE_BLOCK_SIZE + 1
                    upper = lower + TEST_RANGE_BLOCK_SIZE - 1
                    range_tag = f"{lower}-{upper}"
                    formatted_tag = f"{base_tag}::{range_tag}::{tn:02d}"

        if not browser.selectedNotes():
            showInfo("❌ No notes selected.")
            return
        apply_tags_to_selected_notes(browser, [formatted_tag], action_key=action_key)

    return on_trigger


def add_static_action(browser, menu, set_name: str, tags: list[str], action_key: str):
    action = QAction(set_name, browser)
    action.triggered.connect(
        lambda _, tags=tags, k=action_key: apply_tags_to_selected_notes(browser, tags, action_key=k)
    )
    menu.addAction(action)


def add_dynamic_test_prompt(browser, menu, base_tag: str, action_key: str):
    action = QAction("♦️Missed Test #", browser)
    action.triggered.connect(
        lambda _, base_tag=base_tag, k=action_key: prompt_and_apply_test_tag(browser, base_tag, action_key=k)
    )
    menu.addAction(action)


def add_key_info_action(browser, menu):
    action = QAction("Key Info 🗝️", browser)

    def on_click():
        if not browser.selectedNotes():
            showInfo("❌ No notes selected.")
            return
        key_tag = get_rotation_key_info_tag()
        apply_tags_to_selected_notes(
            browser, [key_tag], action_key=ACTION_KEY_KEY_INFO
        )  # EXCLUDED from month/rotation

    action.triggered.connect(on_click)
    menu.addAction(action)


def add_correct_guess_action(browser, menu):
    action = QAction("Guessed Correct 🎫", browser)
    action.triggered.connect(
        lambda _: apply_tags_to_selected_notes(
            browser, get_correct_guess_tags(), action_key=ACTION_KEY_CORRECT_GUESS
        )
    )
    menu.addAction(action)
