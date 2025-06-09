from aqt.qt import QAction, QMenu
from aqt.utils import showInfo

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
    showInfo(f"✅ Applied {len(tag_list)} tags to {len(nids)} notes.")


def add_tag_menu_items(browser, menu, config: dict):
    tag_config = config.get("tag_selected_notes_config", {})
    if not tag_config:
        return

    tag_menu = QMenu("📝 Apply Config Tags", browser)

    i = 1
    while True:
        name_key = f"set_{i}_name"
        tags_key = f"tag_set_{i}"
        if name_key not in tag_config or tags_key not in tag_config:
            break

        set_name = tag_config[name_key]
        tags = tag_config[tags_key]

        action = QAction(set_name, browser)
        action.triggered.connect(lambda _, tags=tags: apply_tags_to_selected_notes(browser, tags))
        tag_menu.addAction(action)
        i += 1

    if tag_menu.actions():
        menu.addSeparator()
        menu.addMenu(tag_menu)


