from aqt.qt import QAction, QMenu, QInputDialog
import re
# --- Helper to scrub resource label for tag suffix ---
def scrub_resource_label_to_tag(label: str) -> str:
    """
    - Trim whitespace
    - Remove any character that is not a letter, digit, space, or hyphen
    - Collapse multiple spaces to one
    """
    base = str(label).strip()
    base = re.sub(r'[^A-Za-z0-9\- ]+', '', base)
    base = re.sub(r'\s+', ' ', base).strip()
    return base
from aqt.utils import showInfo, tooltip
from datetime import datetime

ROTATION_SCHEDULE = [
    ("IM1",       "2025-06-30", "2025-07-25"),
    ("FM2",       "2025-07-28", "2025-08-22"),
    ("ACM",       "2025-08-25", "2025-09-05"),
    ("OMM",       "2025-09-08", "2025-09-18"),
    ("Surgery",   "2025-09-22", "2025-10-17"),
    ("IM2",       "2025-10-20", "2025-11-14"),
    ("FM1",       "2025-11-17", "2025-12-12"),
    ("Pediatrics","2026-01-05", "2026-01-30"),
    ("OBGYN",     "2026-02-02", "2026-02-27"),
    ("Psych",     "2026-03-02", "2026-03-27"),
]

# --- Helper: resolve current-or-next rotation label and its 1-based index ---
def get_current_or_next_rotation_meta():
    """
    Returns (rot_num_2d, rot_label) where:
      - rot_num_2d is a zero-padded 2-digit string (e.g., "02") representing the 1-based
        position within ROTATION_SCHEDULE
      - rot_label is the rotation abbreviation string (e.g., "FM2")
    If today is between a rotation's start/end, that rotation is returned.
    If not in any range, the next upcoming rotation is returned.
    Fallback: ("00", "Unknown").
    """
    today = datetime.today().date()
    # First pass: exact match (currently in this rotation)
    for idx, (rotation, start_str, end_str) in enumerate(ROTATION_SCHEDULE, start=1):
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        if start <= today <= end:
            return f"{idx:02d}", rotation
    # Second pass: next upcoming rotation
    for idx, (rotation, start_str, _end_str) in enumerate(ROTATION_SCHEDULE, start=1):
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        if today < start:
            return f"{idx:02d}", rotation
    # Fallback when today is after all entries
    return "00", "Unknown"

def get_current_or_next_rotation_tag() -> str:
    today = datetime.today().date()
    for rotation, start_str, end_str in ROTATION_SCHEDULE:
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date()
        if start <= today <= end:
            return f"##Missed-Qs::Rotation::{rotation}"
        elif today < start:
            return f"##Missed-Qs::Rotation::{rotation}"
    return "##Missed-Qs::Rotation::Unknown"

DEFAULT_TEST_TAG_PREFIX = "##Missed-Qs::UW_Tests"

month_tag = f"##Missed-Qs::{datetime.now().year}::{datetime.now().strftime('%B')}"

TEST_RANGE_BLOCK_SIZE = 25

MULTI_MISS_TAG = "##Missed-Qs::2x"
# NOTE: Defaults only. These can be overridden via config under
# tag_selected_notes_config.other_menu {label, prefix, resources}.
# --- Other Resources submenu constants ---
# Prefix for resource-specific tags applied alongside Base Tags
OTHER_PREFIX = "##Missed-Qs::Other::"
# Exact resource labels to display and to append to OTHER_PREFIX
OTHER_RESOURCES = [" Kaplan ", "  True-Learn  ", "  Amboss  ", "  NBOME  "]

MONTH = datetime.now().strftime("%B")

Correct_guess_tags = [
    "#Custom::correct_marked"
]

 # --- Helper: add a tag to a note safely across Anki versions ---
def _add_tag_safe(note, tag: str):
    """Use add_tag if available, otherwise fallback to addTag (older API)."""
    if hasattr(note, "add_tag"):
        note.add_tag(tag)
    else:
        # Older Anki API
        note.addTag(tag)

def apply_tags_to_selected_notes(browser, tag_list: list[str]):
    col = browser.mw.col
    nids = browser.selectedNotes()
    if not nids:
        return

    # Always compute rotation tag and append it
    rotation_tag = get_current_or_next_rotation_tag()

    # Build final ordered tag list: incoming tags + rotation (de-duplicated, preserve order)
    combined = list(tag_list or []) + [rotation_tag]
    seen = set()
    final_tags = []
    for t in combined:
        if t and t not in seen:
            seen.add(t)
            final_tags.append(t)

    # Apply to all selected notes
    for nid in nids:
        note = col.get_note(nid)
        # Ensure all tags are present
        current = set(note.tags)
        for tag in final_tags:
            if tag not in current:
                _add_tag_safe(note, tag)
        note.flush()

    browser.model.reset()
    # Brief confirmation including the rotation tag added
    tooltip(f"✅ Applied {len(final_tags)} tags (incl. rotation) to {len(nids)} notes.")



def add_tag_menu_items(browser, menu, config: dict):
    # Extract tag configuration from the passed-in config dictionary
    tag_config = config.get("tag_selected_notes_config", {})
    if not tag_config:
        return

    # Create a submenu under the browser's context menu for applying tag presets
    tag_menu = QMenu(" 📝 Apply Config Tags ", browser)

    # Add combined base + test# action first
    add_combined_base_plus_test(browser, tag_menu, tag_config)
    # Add base tags and missed test tag
    add_base_tags(browser, tag_menu, tag_config)
    # Add separator
    tag_menu.addSeparator()
        # Add COMQUEST Test + Month action
    add_COMQUEST_tag(browser, tag_menu, tag_config)
    tag_menu.addSeparator()

    add_UW_test_tag(browser, tag_menu, tag_config)
    tag_menu.addSeparator()
    
    add_multi_tag(browser, tag_menu, tag_config)
    tag_menu.addSeparator()
    
    
    add_correct_guess_action(browser, tag_menu)

    # Add UW Test This Month action
    add_uw_month_tag(browser, tag_menu)
    
    # Place resource actions (flat, not submenu) at the very end
    tag_menu.addSeparator()
    add_other_resources_actions(browser, tag_menu, tag_config)

    # Add the submenu to the context menu only if actions were added
    if tag_menu.actions():
        menu.addSeparator()
        menu.addMenu(tag_menu)

# --- New helper functions ---
def add_COMQUEST_tag(browser, menu, tag_config):
    """Prompt for COMQUEST test number, apply tag with optional child, and add month tag."""
    set_3_name = tag_config.get("set_3_name")
    set_3_tags = tag_config.get("tag_set_3", [])
    if not (set_3_name and set_3_tags):
        return

    base_tag = set_3_tags[0]  # "##Missed-Qs::COMQUEST"
    padded_name = f"{set_3_name:<24}"

    def on_trigger():
        test_num, ok = QInputDialog.getText(browser, "Enter COMQUEST Test Number", "Test #:")
        if not ok:
            return

        test_num = test_num.strip()
        # Build tag as: ##Missed-Qs::COMQUEST::nn_{Rotation}::TT
        # where nn = 2-digit rotation index, {Rotation} = current label, TT = 2-digit test number
        rot_num_2d, rot_label = get_current_or_next_rotation_meta()
        if test_num.isdigit() and int(test_num) > 0:
            formatted_tag = f"{base_tag}::{rot_num_2d}_{rot_label}::{int(test_num):02d}"
        else:
            # Fallback keeps the nn_{Rotation} segment even if test number is invalid/blank
            formatted_tag = f"{base_tag}::{rot_num_2d}_{rot_label}"

        if not browser.selectedNotes():
            showInfo("❌ No notes selected.")
            return

        apply_tags_to_selected_notes(browser, [formatted_tag, month_tag])

    action = QAction(padded_name, browser)
    action.triggered.connect(on_trigger)
    menu.addAction(action)



def add_multi_tag(browser, menu, tag_config):
    multi_tag = MULTI_MISS_TAG  # Already a string, no need for f-string
    multi_tag_label = f"{'2x Missed 📌':<24}"
    combined_tags = [multi_tag, month_tag]
    add_static_config_action(browser, menu, multi_tag_label, combined_tags)


def add_base_tags(browser, menu, tag_config):
    """Add static tag sets 1, 2, and 3 to the menu using config-defined names."""
    for i in (1, 2):
        set_name = tag_config.get(f"set_{i}_name")
        tags = tag_config.get(f"tag_set_{i}", [])
        if set_name and tags:
            # Append month_tag only to tag_set_1 and tag_set_3
            should_append_month = i in (1, 3)
            full_tags = tags + ([month_tag] if should_append_month else [])
            padded_name = f"{set_name:<24}"
            add_static_config_action(browser, menu, padded_name, full_tags)

def add_UW_test_tag(browser, menu, tag_config):
    """Add dynamic test number prompt action if configured."""
    if tag_config.get("set_1_name") == "Test number" or tag_config.get("set_2_name") == "Test number":
        set_2_tags = tag_config.get("tag_set_2", [])
        base_tag = set_2_tags[0] if set_2_tags else DEFAULT_TEST_TAG_PREFIX
        add_dynamic_test_prompt(browser, menu, base_tag)


# --- Helper to get Base Tags (tag_set_1 + month_tag) ---
def get_base_tags(tag_config: dict) -> list[str]:
    """Return base tags from config (tag_set_1) plus month_tag, mirroring existing behavior."""
    base = tag_config.get("tag_set_1", [])
    # Ensure we always append the current month_tag
    return base + [month_tag]


# --- "Other" submenu: Base Tags + one resource tag ---
def add_other_resources_menu(browser, menu, tag_config):
    """
    Create an "Other" submenu that applies Base Tags (tag_set_1 + month_tag)
    plus exactly one resource tag with the prefix OTHER_PREFIX.

    Items: Kaplan, True-Learn, Amboss.
    """
    # Pull configurable values from config, fallback to defaults defined above
    other_cfg = tag_config.get("other_menu", {}) if isinstance(tag_config, dict) else {}
    other_label = other_cfg.get("label", "Other")
    cfg_prefix = other_cfg.get("prefix", OTHER_PREFIX)
    cfg_resources = other_cfg.get("resources", OTHER_RESOURCES)

    other_menu = QMenu(other_label, browser)  # opens on hover as a submenu

    # Build actions for each resource
    for resource_name in cfg_resources:
        # Construct label: strip config whitespace, then pad with 3 spaces each side
        label = f"   {str(resource_name).strip()}   "
        # Compute the resource-specific tag using scrubd label
        resource_tag = f"{cfg_prefix}{scrub_resource_label_to_tag(resource_name)}"

        action = QAction(label, browser)

        def on_click(_, rtag=resource_tag):
            # Guard: require a selection; match existing UX for error messaging
            if not browser.selectedNotes():
                showInfo("❌ No notes selected.")
                return
            # Gather Base Tags (tag_set_1 + month_tag) and append this resource tag
            tags_to_apply = get_base_tags(tag_config) + [rtag]
            # Reuse centralized applier so rotation tag auto-add still happens
            apply_tags_to_selected_notes(browser, tags_to_apply)

        action.triggered.connect(on_click)
        other_menu.addAction(action)

    # Only add the submenu if we actually created actions
    if other_menu.actions():
        menu.addMenu(other_menu)

# --- "Other" resources as flat actions at end of main menu ---
# NOTE: We keep the legacy submenu function above for reference, but this
# inline version is now used to append actions directly to the main tag menu.
# This preserves behavior (Base Tags + month_tag + resource tag + auto-rotation)
# while avoiding a nested submenu. Resource labels are stripped so stray
# whitespace from config does not leak into QAction labels or tag text.

def add_other_resources_actions(browser, menu, tag_config):
    """
    Append flat 'Other resource' actions to the end of the main tag menu.
    Each action applies: Base Tags (tag_set_1 + month_tag) + one resource tag.

    We intentionally do **not** modify config or defaults here; instead we
    scrub labels at runtime via `.strip()` to remain robust to whitespace
    in the configured names (e.g., " Kaplan ").
    """
    # Pull configurable values; keep defaults if missing
    other_cfg = tag_config.get("other_menu", {}) if isinstance(tag_config, dict) else {}
    cfg_prefix = other_cfg.get("prefix", OTHER_PREFIX)
    cfg_resources = other_cfg.get("resources", OTHER_RESOURCES)

    # Build actions directly on the main menu (no submenu)
    for resource_name in cfg_resources:
        # Normalize label and tag (defensive against stray spaces in config)
        label = str(resource_name).strip()
        resource_tag = f"{cfg_prefix}{scrub_resource_label_to_tag(resource_name)}"

        action = QAction(label, browser)

        # IMPORTANT: keep rotation auto-append by routing through
        # apply_tags_to_selected_notes(), which computes and adds the rotation tag.
        def on_click(_, rtag=resource_tag):
            if not browser.selectedNotes():
                showInfo("❌ No notes selected.")
                return
            # Base Tags = tag_set_1 + month_tag (see get_base_tags)
            tags_to_apply = get_base_tags(tag_config) + [rtag]
            apply_tags_to_selected_notes(browser, tags_to_apply)

        action.triggered.connect(on_click)
        menu.addAction(action)

# --- New function for prompting test number and applying tag ---
def prompt_and_apply_test_tag(browser, base_tag: str):
    """Prompt the user for a test number and apply a dynamically constructed tag to selected notes."""
    test_num, ok = QInputDialog.getText(browser, "Enter Test Number", "Test #:")
    if ok and test_num.strip():
        try:
            test_input = int(test_num.strip())
            lower = ((test_input - 1) // TEST_RANGE_BLOCK_SIZE) * TEST_RANGE_BLOCK_SIZE + 1
            upper = lower + TEST_RANGE_BLOCK_SIZE - 1
            range_tag = f"{lower}-{upper}"
            
            full_number_tag = f"{base_tag}::{range_tag}::{test_input:02d}"
            apply_tags_to_selected_notes(browser, [full_number_tag])
        except ValueError:
            showInfo("❌ Please enter a valid integer test number.")


# Helper functions for modular menu action addition

def add_static_config_action(browser, menu, set_name, tags):
    """Add a static tag set action to the menu."""
    action = QAction(set_name, browser)
    action.triggered.connect(lambda _, tags=tags: apply_tags_to_selected_notes(browser, tags))
    menu.addAction(action)

def add_dynamic_test_prompt(browser, menu, base_tag):
    """Add a dynamic test number prompt action to the menu."""
    action = QAction("♦️Missed Test #", browser)
    action.triggered.connect(lambda _, base_tag=base_tag: prompt_and_apply_test_tag(browser, base_tag))
    menu.addAction(action)

def add_combined_base_plus_test(browser, menu, tag_config):
    """Add combined Set 1 + Test# action with prompt."""
    combined_action = QAction("📕BASE + Test (UW)", browser)
    def handle_combined_action():
        test_tag_base = tag_config.get("tag_set_2", [DEFAULT_TEST_TAG_PREFIX])[0]
        from aqt.qt import QInputDialog
        test_num, ok = QInputDialog.getText(browser, "Enter Test Number", "Test #:")
        if ok and test_num.strip():
            try:
                test_input = int(test_num.strip())
                lower = ((test_input - 1) // TEST_RANGE_BLOCK_SIZE) * TEST_RANGE_BLOCK_SIZE + 1
                upper = lower + TEST_RANGE_BLOCK_SIZE - 1
                range_tag = f"{lower}-{upper}"
                final_missed_test_tag = f"{test_tag_base}::{range_tag}::{test_input:02d}"
                set1_tags = tag_config.get("tag_set_1", []) + [month_tag]
                combined_tags = set1_tags + [final_missed_test_tag]
                apply_tags_to_selected_notes(browser, combined_tags)
            except ValueError:
                showInfo("❌ Please enter a valid integer test number.")
    combined_action.triggered.connect(handle_combined_action)
    menu.addAction(combined_action)

def add_uw_month_tag(browser, menu):
    """Add action to tag as UW-Tests::{Month}::{TestNumber}."""
    month_test_action = QAction("📒Full UW Test Tag– Month", browser)
    def handle_month_test_tag():
        test_num, ok = QInputDialog.getText(browser, "Enter Test Number", "Test #:")
        if ok and test_num.strip():
            try:
                test_input = int(test_num.strip())
                month_str = datetime.now().strftime("%B")
                final_tag = f"UW-Tests::{month_str}::{test_input:02d}"
                apply_tags_to_selected_notes(browser, [final_tag])
            except ValueError:
                showInfo("❌ Please enter a valid integer test number.")
    month_test_action.triggered.connect(handle_month_test_tag)
    menu.addAction(month_test_action)

# --- Add Correct Guess Action ---
def add_correct_guess_action(browser, menu):
    """Add action to tag notes as correct guesses."""
    action = QAction("Guessed Correct 🎫", browser)
    action.triggered.connect(lambda _, tags=Correct_guess_tags: apply_tags_to_selected_notes(browser, tags))
    menu.addAction(action)
