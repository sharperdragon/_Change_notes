# Add missing imports
import re, os, sys, json
from collections import defaultdict
# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt import mw
from aqt.qt import QAction
from aqt.browser import Browser
from aqt.gui_hooks import browser_will_show_context_menu
from ...config_manager import ConfigManager

# 📁 Path setup
addon_path = os.path.dirname(__file__)
config_path = os.path.join(addon_path, "config.json")

# 🛠 Config loader
def load_config():
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[MergeImages] Failed to load config.json: {e}")
        return {}

CONFIG = load_config()
print("[MergeImages] Config loaded successfully.")


from ..utils import normalize, group_notes_by_similarity, extract_images, clean_img_tag, extract_srcs

from aqt import mw
from aqt.qt import QInputDialog, QMessageBox, QTextEdit, QDialog, QVBoxLayout, QPushButton
from aqt.browser import Browser
from aqt.gui_hooks import browser_will_show_context_menu
from aqt.qt import QAction



def merge_images_main(browser=None):
    default_threshold = CONFIG.get("default_threshold", 0.95)
    min_threshold = CONFIG.get("min_threshold", 0.85)
    max_threshold = CONFIG.get("max_threshold", 1.0)
    if browser is None:
        browser = mw.form.browser
    note_ids = browser.selectedNotes()
    if not note_ids:
        QMessageBox.information(mw, "Unify Images", "No notes selected.")
        return
    threshold, ok = QInputDialog.getDouble(
        mw, "Fuzzy Threshold", "Enter fuzzy match threshold:",
        value=default_threshold, min=min_threshold, max=max_threshold, decimals=2
    )
    if not ok:
        return

    all_note_infos = [mw.col.get_note(nid) for nid in note_ids]
    def has_excluded_tag(note):
        return False

    # Load tagging and logging config before loop
    received_tag = CONFIG["tagging"].get("add_to_merged", "IMG_Uni::received")
    unchanged_tag = CONFIG["tagging"].get("add_to_merged_unchanged", "IMG_Uni::same")
    enable_popup = CONFIG["logging"].get("enable_log_popup", True)
    save_to_desktop = CONFIG["logging"].get("save_log_to_desktop", False)
    log_prefix = CONFIG["logging"].get("log_filename_prefix", "merged_images_log_")

    note_groups = group_notes_by_similarity(all_note_infos, threshold, "Text", has_excluded_tag)
    log_entries = []
    merged = 0

    for group in note_groups.values():
        model_groups = defaultdict(list)
        for note in group:
            model_name = mw.col.models.get(note.mid)["name"]
            model_groups[model_name].append(note)

        for model_group in model_groups.values():
            # Removed block that adds donor tag to any note with image

            if len(model_group) > 2:
                multi_matched_nids = []
                for note in model_group:
                    note.tags = [t for t in note.tags if t != CONFIG["tagging"].get("add_to_donor", "IMG_Uni::donor")]
                    note.tags = list(set(note.tags) | {"IMG_Uni::multiple_match"})
                    mw.col.update_note(note)
                    multi_matched_nids.append(str(note.id))
                log_entries.append("⚠️ IMG_Uni::multiple_match tagged:\n\n" + ", ".join(multi_matched_nids) + ",\n")
                continue
            if len(model_group) < 2:
                continue
            donors = []
            for note in model_group:
                for field in note.fields:
                    if extract_images(field):
                        donors.append(note)
                        break

            field_to_images = defaultdict(list)
            for donor in donors:
                for i, field in enumerate(donor.fields):
                    raw_imgs = extract_images(field)
                    cleaned_imgs = [clean_img_tag(img) for img in raw_imgs if clean_img_tag(img)]
                    for img in cleaned_imgs:
                        if img not in field_to_images[i]:
                            field_to_images[i].append(img)

            if not any(field_to_images.values()):
                continue

            for note in model_group:
                updated_fields = list(note.fields)
                changed = False
                all_existing_imgs = set()
                for f in note.fields:
                    all_existing_imgs.update(extract_images(f))
                all_existing_srcs = extract_srcs(all_existing_imgs)

                used_donors = set()

                for i, images in field_to_images.items():
                    missing_imgs = [
                        img for img in images
                        if re.search(r'src="([^"]+)"', img).group(1) not in all_existing_srcs
                    ]
                    if not missing_imgs:
                        continue
                    image_block = "<div>" + "<br>".join(missing_imgs) + "</div>"
                    if updated_fields[i].strip():
                        updated_fields[i] += image_block
                    else:
                        updated_fields[i] = image_block
                    for donor in donors:
                        if any(img in extract_images("".join(donor.fields)) for img in missing_imgs):
                            used_donors.add(donor.id)
                    changed = True
                    donor_ids = [str(donor.id) for donor in donors if donor.id in used_donors]
                    donor_note_list = ", ".join(donor_ids) if donor_ids else "None"
                    log_entries.append(f"🧬 Added to Note ID {note.id} in field {i}: {image_block} (tagged donor = {donor_note_list})")

                if changed:
                    note.fields = updated_fields
                    note.tags = list(set(note.tags) | {received_tag})
                    for donor in donors:
                        if donor.id in used_donors:
                            donor.tags = list(set(donor.tags) | {CONFIG["tagging"].get("add_to_donor", "IMG_Uni::donor")})
                            mw.col.update_note(donor)
                    mw.col.update_note(note)
                    merged += 1
                else:
                    if (
                        note in group and len(model_group) == 2
                    ):
                        note_imgs = set(extract_images("".join(note.fields)))
                        donor_imgs = set()
                        for donor in donors:
                            if donor.id != note.id:
                                donor_imgs.update(extract_images("".join(donor.fields)))
                        if note_imgs == donor_imgs:
                            note.tags = list(set(note.tags) | {unchanged_tag})
                            log_entries.append(f"✅ IMG_Uni::same tagged: Note ID {note.id}")
                            mw.col.update_note(note)

    if merged == 0:
        if enable_popup and log_entries:
            show_log_window("\n\n".join(log_entries))
        else:
            show_log_window("No images were merged and no taggable group actions were logged.")
        return

    # Save log to desktop if enabled
    if save_to_desktop:
        from pathlib import Path
        import time
        log_path = Path.home() / f"Desktop/{log_prefix}{int(time.time())}.txt"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n\n".join(log_entries))

    if enable_popup:
        show_log_window("\n\n".join(log_entries))

def show_log_window(log_text):
    dlg = QDialog(mw)
    dlg.setWindowTitle("Unify Images Log")
    layout = QVBoxLayout()
    text_edit = QTextEdit()
    text_edit.setReadOnly(True)
    text_edit.setPlainText(log_text)
    layout.addWidget(text_edit)
    btn_close = QPushButton("Close")
    btn_close.clicked.connect(dlg.close)
    layout.addWidget(btn_close)
    dlg.setLayout(layout)
    dlg.resize(800, 500)
    dlg.exec()

def browser_menu_hook(menu, browser: Browser):
    act = QAction("🧬 Unify Images from Donors", menu)
    act.triggered.connect(lambda: merge_images_main(browser))
    menu.addAction(act)

browser_will_show_context_menu.append(browser_menu_hook)



















def on_browser_will_show_context_menu(browser: Browser, menu):
    selected = browser.selectedNotes()
    if not selected:
        return
    action = QAction("🧬 Unify Images from Donors", browser)
    action.triggered.connect(lambda: merge_images_main(browser))
    print("[MergeImages] Injecting browser context menu item.")
    menu.addSeparator()
    menu.addAction(action)

if not getattr(mw, "_merge_images_menu_injected", False):
    browser_will_show_context_menu.append(on_browser_will_show_context_menu)
    mw._merge_images_menu_injected = True