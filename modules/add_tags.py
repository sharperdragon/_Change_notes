# pyright: reportMissingImports=false
import re
from datetime import datetime

from aqt.qt import QAction, QInputDialog, QMenu
from aqt.utils import showInfo, tooltip

# ! ----------------------------- USER-TUNABLE CONSTANTS -----------------------------
# ? Base “missed” scaffolding
MISSED_BASE_TAG = ["##Missed-Qs"]  # former: tag_config["missed_base_tag"]

# ? Month + rotation labels (now bare segments; the base "##Missed-Qs" is composed at use-time)
MULTI_MISS_TAG = "2x"
DEFAULT_TEST_TAG_PREFIX = "UW_Tests"
OTHER_SUFFIX = "Other"


# $ Compose a full Missed-Qs tag path with the base prefix
def base_tag_path(*parts: str) -> str:
    return "::".join([MISSED_BASE_TAG[0], *[p for p in parts if p]])


# ? UW / COMQUEST “subset” equivalents
SUBSET_1_NAME = "🛃UWorld"
SUBSET_1_TAG = ["##Missed-Qs::UW_Tests"]
SUBSET_2_NAME = "♿️COMQUEST"
SUBSET_2_TAG = ["##Missed-Qs::COMQUEST"]

# ? Other resources (flat actions + submenu)
OTHER_MENU_LABEL = "Other"
OTHER_RESOURCES = ["Kaplan", "True-Learn", "Amboss", "NBOME"]

# ? Special actions
KEY_TAG_BASE = "#Custom::#Shelf"
KEY_INFO_SUFFIX = "*KEY"
CORRECT_GUESS_TAGS = ["#Custom::correct_marked"]

# ? Exclude list for “auto-missed” context
EXCLUDE_AUTO_MISS = ["add_key_info_action"]
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
    return "##Missed-Qs::COMQUEST_Base"


MONTH = datetime.now().strftime("%B")
M_NUM = datetime.now().strftime("%m")
missed_month_tag = f"##Missed-Qs::{datetime.now().year}::{M_NUM}_{MONTH}"
TEST_RANGE_BLOCK_SIZE = 25


ROTATION_SCHEDULE = [
    ("IM1", "2025-06-30", "2025-07-25"),
    ("FM2", "2025-07-28", "2025-08-22"),
    ("ACM", "2025-08-25", "2025-09-05"),
    ("OMM", "2025-09-08", "2025-09-18"),
    ("Surgery", "2025-09-22", "2025-10-17"),
    ("IM2", "2025-10-20", "2025-11-14"),
    ("FM1", "2025-11-17", "2025-12-12"),
    ("Winter-break", "2025-12-13", "2026-01-04"),
    ("Pediatrics", "2026-01-05", "2026-01-30"),
    ("OBGYN", "2026-02-02", "2026-02-27"),
    ("Psych", "2026-03-02", "2026-03-27"),
]


def scrub_resource_label_to_tag(label: str) -> str:
    missed_base = str(label).strip()
    missed_base = re.sub(r"[^A-Za-z0-9\- ]+", "", missed_base)
    missed_base = re.sub(r"\s+", " ", missed_base).strip()
    return missed_base


def get_rotation_key_info_tag() -> str:
    """Return the KEY info tag for the current/next rotation, using numbered segment.

    Example: '#Custom::#Shelf::07_FM1::*KEY'
    """
    segment = get_rotation_segment()
    return f"{KEY_TAG_BASE}::{segment}::{KEY_INFO_SUFFIX}"


def get_current_or_next_rotation_meta():
    today = datetime.today().date()
    for idx, (rotation, start_str, end_str) in enumerate(ROTATION_SCHEDULE, start=1):
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        if start <= today <= end:
            return f"{idx:02d}", rotation
    for idx, (rotation, start_str, _end_str) in enumerate(ROTATION_SCHEDULE, start=1):
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        if today < start:
            return f"{idx:02d}", rotation
    return "00", "Unknown"


def get_rotation_segment() -> str:
    """Return canonical rotation segment like '07_FM1' or '00_Unknown'."""
    rot_num_2d, rot_label = get_current_or_next_rotation_meta()
    if rot_label == "Unknown":
        return f"{rot_num_2d}_Unknown"
    return f"{rot_num_2d}_{rot_label}"


def get_missed_tag_for_rotation() -> str:
    """Rotation context tag for missed questions.

    Default example: '##Missed-Qs::Rotation::07_FM1'
    Winter break example: '##Missed-Qs::Rotation::Winter-break'
    """
    rot_num_2d, rot_label = get_current_or_next_rotation_meta()

    # * Special-case: during Winter-break we want a stable, non-numbered tag
    if (rot_label or "").strip().lower() == "winter-break":
        return "##Missed-Qs::Rotation::Winter-break"

    # * Default: numbered segment (e.g., 07_FM1)
    segment = (
        f"{rot_num_2d}_{rot_label}"
        if rot_label != "Unknown"
        else f"{rot_num_2d}_Unknown"
    )
    return f"##Missed-Qs::Rotation::{segment}"


def _add_tag_safe(note, tag: str):
    if hasattr(note, "add_tag"):
        note.add_tag(tag)
    else:
        note.addTag(tag)


# ! Centralized tag applier: adds rotation (always) and month (unless excluded)
def apply_tags_to_selected_notes(browser, tag_list: list[str], action_key: str):
    col = browser.mw.col
    nids = browser.selectedNotes()
    if not nids:
        return
    # $ Build dynamic context tags
    final = list(tag_list or [])
    # Extend exclusion locally to keep "Guessed Correct" clean without touching top config
    local_exclude = set(EXCLUDE_AUTO_MISS) | {"correct_guess"}
    # Append rotation + month only when NOT excluded
    if action_key not in local_exclude:
        final.append(get_missed_tag_for_rotation())
        final.append(missed_month_tag)

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
    tooltip(f"✅ Applied {len(final_tags)} tags to {len(nids)} notes.")


# $ Add a plain "Base" action (no test/rotation/month)
def add_base_plain_action(browser, menu):
    action = QAction("♦️Base", browser)
    action.triggered.connect(
        lambda _: apply_tags_to_selected_notes(
            browser, MISSED_BASE_TAG, action_key="base_plain"
        )
    )
    menu.addAction(action)


def add_tag_menu_items(browser, menu, config=None):
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
            action_key="comquest_test_prompt",
            title="Enter COMQUEST Test Number",
            label="Test #:",
            blank_behavior="base_plus_rotation",
            number_style="rotation_then_number",
        )
    )
    menu.addAction(action)


def add_multi_tag(browser, menu):
    multi_tag = base_tag_path(MULTI_MISS_TAG)
    multi_tag_label = f"{'2x Missed 📌':<24}"
    add_static_action(
        browser, menu, multi_tag_label, [multi_tag], action_key="multi_missed"
    )


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
                action_key="uw_test_prompt",
                title="Enter UWorld Test Number",
                label="Test #:",
                blank_behavior="base_only",
                number_style="range_then_number",
            )
        )
        menu.addAction(action)


def add_other_resources_actions(browser, menu):
    """
    Builds the 'Other' submenu.

    - Kaplan / Amboss / NBOME: simple 'Other::<Source>' tags.
    - True-Learn: behaves like COMQUEST, with rotation + optional test number:
        ##Missed-Qs::Other::True-Learn::07_FM1::04
        (if blank test #: ##Missed-Qs::Other::True-Learn::07_FM1)
    """
    for resource_name in OTHER_RESOURCES:
        label = str(resource_name).strip()

        # * SPECIAL CASE: True-Learn uses rotation + optional test number
        if label == "True-Learn":
            # Base tag: "##Missed-Qs::Other::True-Learn"
            base_tag = base_tag_path(
                OTHER_SUFFIX,
                scrub_resource_label_to_tag(resource_name),
            )

            action = QAction(label, browser)

            # Use the same factory used for COMQUEST, but with "Other::True-Learn"
            handler = make_test_prompt_handler(
                browser,
                base_tag,
                action_key="true_learn_test_prompt",
                title="Enter True-Learn Test Number",
                label="Test #:",
                blank_behavior="base_plus_rotation",  # blank → base_tag::<rotNum>_<rotLabel>
                number_style="rotation_then_number",  # number → base_tag::<rotNum>_<rotLabel>::NN
            )

            action.triggered.connect(handler)
            menu.addAction(action)
            continue  # Skip the generic behavior for this resource

        # * DEFAULT: flat source tag under Other
        resource_tag = base_tag_path(
            OTHER_SUFFIX,
            scrub_resource_label_to_tag(resource_name),
        )

        action = QAction(label, browser)

        def on_click(_, rtag=resource_tag):
            if not browser.selectedNotes():
                showInfo("❌ No notes selected.")
                return
            # -> e.g. "##Missed-Qs::Other::Kaplan"
            tags_to_apply = MISSED_BASE_TAG + [rtag]
            apply_tags_to_selected_notes(
                browser, tags_to_apply, action_key="other_resource"
            )

        action.triggered.connect(on_click)
        menu.addAction(action)


def prompt_and_apply_test_tag(browser, base_tag: str, action_key: str):
    test_num, ok = QInputDialog.getText(browser, "Enter Test Number", "Test #:")
    if ok and test_num.strip():
        try:
            test_input = int(test_num.strip())
            lower = (
                (test_input - 1) // TEST_RANGE_BLOCK_SIZE
            ) * TEST_RANGE_BLOCK_SIZE + 1
            upper = lower + TEST_RANGE_BLOCK_SIZE - 1
            range_tag = f"{lower}-{upper}"
            full_number_tag = f"{base_tag}::{range_tag}::{test_input:02d}"
            apply_tags_to_selected_notes(
                browser, [full_number_tag], action_key=action_key
            )
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
      - "base_plus_rotation" -> blank/non-numeric -> base_tag::<rotNum>_<rotLabel>

    number_style:
      - "range_then_number"    -> base_tag::<lower-upper>::NN
      - "rotation_then_number" -> base_tag::<rotNum>_<rotLabel>::NN
    """

    def on_trigger():
        # Prompt with no placeholder/default text
        test_num, ok = QInputDialog.getText(browser, title, label)
        if not ok:
            return
        test_num = (test_num or "").strip()
        rot_num_2d, rot_label = get_current_or_next_rotation_meta()

        if test_num == "":
            if blank_behavior == "base_only":
                formatted_tag = f"{base_tag}"
            else:
                formatted_tag = f"{base_tag}::{rot_num_2d}_{rot_label}"
        else:
            try:
                tn = int(test_num)
            except ValueError:
                # Treat non-numeric like blank
                if blank_behavior == "base_only":
                    formatted_tag = f"{base_tag}"
                else:
                    formatted_tag = f"{base_tag}::{rot_num_2d}_{rot_label}"
            else:
                if number_style == "rotation_then_number":
                    formatted_tag = f"{base_tag}::{rot_num_2d}_{rot_label}::{tn:02d}"
                else:
                    lower = (
                        (tn - 1) // TEST_RANGE_BLOCK_SIZE
                    ) * TEST_RANGE_BLOCK_SIZE + 1
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
        lambda _, tags=tags, k=action_key: apply_tags_to_selected_notes(
            browser, tags, action_key=k
        )
    )
    menu.addAction(action)


def add_dynamic_test_prompt(browser, menu, base_tag: str, action_key: str):
    action = QAction("♦️Missed Test #", browser)
    action.triggered.connect(
        lambda _, base_tag=base_tag, k=action_key: prompt_and_apply_test_tag(
            browser, base_tag, action_key=k
        )
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
            browser, [key_tag], action_key="add_key_info_action"
        )  # EXCLUDED from month/rotation

    action.triggered.connect(on_click)
    menu.addAction(action)


def add_correct_guess_action(browser, menu):
    action = QAction("Guessed Correct 🎫", browser)
    action.triggered.connect(
        lambda _: apply_tags_to_selected_notes(
            browser, CORRECT_GUESS_TAGS, action_key="correct_guess"
        )
    )
    menu.addAction(action)
