from aqt.qt import QAction, QMenu
from aqt.utils import showInfo, tooltip
from datetime import datetime

DEFAULT_TEST_TAG_PREFIX = "##Missed-Qs::UW_Tests"

month_tag = f"##Missed-Qs::{datetime.now().year}::{datetime.now().strftime('%B')}"

TEST_RANGE_BLOCK_SIZE = 25


MONTH = datetime.now().strftime("%B")

Correct_guess_tags = [
    "#Focus-Review::correct_marked",
    "#Focus-Review::ZIP::Correct_Guess"
]

def apply_tags_to_selected_notes(browser, tag_list: list[str]):
    col = browser.mw.col
    nids = browser.selectedNotes()
    if not nids or not tag_list:
        return

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
    tag_menu = QMenu("📝 Apply Config Tags", browser)

    # Add combined base + test# action first
    add_combined_base_plus_test(browser, tag_menu, tag_config)
    # Add base tags and missed test tag
    add_base_tags(browser, tag_menu, tag_config)
    # Add separator
    tag_menu.addSeparator()
    
    add_missed_test_tag(browser, tag_menu, tag_config)
    
    spacer = QAction(" ", browser)
    spacer.setEnabled(False)
    tag_menu.addAction(spacer)
    
    
    add_correct_guess_action(browser, tag_menu)

    # Add UW Test This Month action
    add_uw_month_tag(browser, tag_menu)

    # Add the submenu to the context menu only if actions were added
    if tag_menu.actions():
        menu.addSeparator()
        menu.addMenu(tag_menu)


# --- New helper functions ---

def add_base_tags(browser, menu, tag_config):
    """Add Set 1 and Set 2 static tag sets to the menu."""
    set_1_name = tag_config.get("set_1_name")
    set_1_tags = tag_config.get("tag_set_1", [])
    if set_1_name and set_1_tags:
        add_static_config_action(browser, menu, "📙Base Tags", set_1_tags + [month_tag])

    set_2_name = tag_config.get("set_2_name")
    set_2_tags = tag_config.get("tag_set_2", [])
    if set_2_name and set_2_tags and set_2_name != "Test number":
        add_static_config_action(browser, menu, set_2_name, set_2_tags)

def add_missed_test_tag(browser, menu, tag_config):
    """Add dynamic test number prompt action if configured."""
    if tag_config.get("set_1_name") == "Test number" or tag_config.get("set_2_name") == "Test number":
        set_2_tags = tag_config.get("tag_set_2", [])
        base_tag = set_2_tags[0] if set_2_tags else DEFAULT_TEST_TAG_PREFIX
        add_dynamic_test_prompt(browser, menu, base_tag)


# --- New function for prompting test number and applying tag ---
from aqt.qt import QInputDialog

def prompt_and_apply_test_tag(browser, base_tag: str):
    """Prompt the user for a test number and apply a dynamically constructed tag to selected notes."""
    test_num, ok = QInputDialog.getText(browser, "Enter Test Number", "Test #:")
    if ok and test_num.strip():
        try:
            test_input = int(test_num.strip())
            lower = ((test_input - 1) // TEST_RANGE_BLOCK_SIZE) * TEST_RANGE_BLOCK_SIZE + 1
            upper = lower + TEST_RANGE_BLOCK_SIZE - 1
            range_tag = f"{lower}-{upper}"
            full_number_tag = f"{base_tag}::{range_tag}::{test_input}"
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
                final_missed_test_tag = f"{test_tag_base}::{range_tag}::{test_input}"
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
                final_tag = f"UW-Tests::{month_str}::{test_input}"
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
