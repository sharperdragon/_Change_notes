from aqt.qt import QAction, QMenu, QInputDialog
from aqt.utils import showInfo, tooltip
from datetime import datetime

ROTATION_SCHEDULE = [
    ("IM1",       "2025-06-30", "2025-07-25"),
    ("FM2",       "2025-07-28", "2025-08-22"),
    ("ACM",       "2025-08-25", "2025-09-05"),
    ("OMM",       "2025-09-08", "2025-09-19"),
    ("IM2",       "2025-09-22", "2025-10-17"),
    ("Surgery",   "2025-10-20", "2025-11-14"),
    ("FM1",       "2025-11-17", "2025-12-12"),
    ("Pediatrics","2026-01-05", "2026-01-30"),
    ("OBGYN",     "2026-02-02", "2026-02-27"),
    ("Psych",     "2026-03-02", "2026-03-27"),
]

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

MONTH = datetime.now().strftime("%B")

Correct_guess_tags = [
    "Custom::correct_marked"
]

def apply_tags_to_selected_notes(browser, tag_list: list[str]):
    col = browser.mw.col
    nids = browser.selectedNotes()
    if not nids or not tag_list:
        return

    rotation_tag = get_current_or_next_rotation_tag()
    if rotation_tag not in tag_list:
        tag_list.append(rotation_tag)

    for nid in nids:
        note = col.get_note(nid)
        for tag in tag_list:
            if tag not in note.tags:
                note.add_tag(tag)
        note.flush()
    
    browser.model.reset()
    tooltip(f"✅ Applied {len(tag_list)} tags to {len(nids)} notes.")



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
        if test_num.isdigit() and int(test_num) > 0:
            formatted_tag = f"{base_tag}::{int(test_num):02d}"
        else:
            formatted_tag = base_tag  # fallback if blank or invalid

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
    combined_action = QAction("📕BASE + Test#", browser)
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
