import os, re, json, time, unicodedata
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta



from aqt.qt import QDoubleSpinBox, QDialogButtonBox
from aqt import dialogs


# 📁 Path setup
addon_path = os.path.dirname(__file__)

# 🛠 Config loader (now loads from config_manager)
from ...config_manager import ConfigManager
CONFIG = ConfigManager("global_config", "merge_images_and_tags_config").load()
print("[MergeImages] Config loaded from Anki:", CONFIG.get("fields_to_scan_for_images"))


from ..utils import (
    extract_images,
    extract_srcs,
    clean_img_tag,
)

from ..assets.scrub_match import normalize
from ..assets.scrub_match import group_similar_notes_by_content

from aqt import mw
from aqt.qt import QInputDialog, QMessageBox, QTextEdit, QDialog, QVBoxLayout, QPushButton, QAction
from aqt.browser import Browser
from aqt.gui_hooks import browser_will_show_context_menu



def run_merge_images(note_ids: list[int], threshold=None, base_tag=None, browser=None):
    if not note_ids:
        QMessageBox.information(mw, "Unify Images", "No notes selected.")
        return

    if threshold is None:
        raise ValueError("Threshold must be provided by the caller.")

    if browser is None:
        browser = mw.browser

    all_note_infos = [mw.col.get_note(nid) for nid in note_ids]
    def has_excluded_tag(note):
        return False

    received_tag = f"{base_tag}::received" if base_tag else "IMG_Uni::received"
    unchanged_tag = f"{base_tag}::same" if base_tag else "IMG_Uni::same"
    donor_tag = f"{base_tag}::donor" if base_tag else "IMG_Uni::donor"

    note_groups = group_similar_notes_by_content(all_note_infos, threshold, "Text", has_excluded_tag)
    log_entries = []
    merged = 0
    all_used_donors = set()
    recipients = set()
    same_tagged_nids = []

    for group in note_groups.values():
        model_groups = defaultdict(list)
        for note in group:
            model_name = mw.col.models.get(note.mid)["name"]
            model_groups[model_name].append(note)

        for model_group in model_groups.values():
            if len(model_group) > 2:
                multi_matched_nids = []
                for note in model_group:
                    note.tags = [t for t in note.tags if t != donor_tag]
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
                    field_name = mw.col.models.field_names(mw.col.models.get(donor.mid))[i]
                    if field_name not in CONFIG.get("fields_to_scan_for_images", []):
                        continue
                    raw_imgs = extract_images(field)
                    cleaned_imgs = [clean_img_tag(img) for img in raw_imgs if clean_img_tag(img)]
                    for img in cleaned_imgs:
                        if img not in field_to_images[i]:
                            field_to_images[i].append(img)

            for note in model_group:
                updated_fields = list(note.fields)
                changed = False
                all_existing_imgs = set()
                for i, f in enumerate(note.fields):
                    field_name = mw.col.models.field_names(mw.col.models.get(note.mid))[i]
                    if field_name not in CONFIG.get("fields_to_scan_for_images", []):
                        continue
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
                    missing_srcs = {re.search(r'src="([^"]+)"', img).group(1) for img in missing_imgs}
                    for donor in donors:
                        donor_srcs = set(extract_srcs(extract_images("".join(donor.fields))))
                        if donor_srcs & missing_srcs:
                            used_donors.add(donor.id)
                    changed = True
                    if used_donors:
                        donor_note_list = ", ".join(str(did) for did in sorted(used_donors))
                        log_entries.append(f"🧬 Added to Note ID {note.id} in field {i}: {image_block} (tagged donor = {donor_note_list})")
                        if changed:
                            all_used_donors.update(used_donors)
                    else:
                        log_entries.append(f"🧬 Added to Note ID {note.id} in field {i}: {image_block} (tagged donor = None)")

                if changed:
                    merged += 1
                    note.fields = updated_fields
                    note.tags = list(set(note.tags) | {received_tag})
                    recipients.add(note.id)
                    for donor in donors:
                        if donor.id in used_donors:
                            donor.tags = list(set(donor.tags) | {donor_tag})
                            mw.col.update_note(donor)
                    mw.col.update_note(note)

    src_to_note_ids = defaultdict(list)
    note_to_srcs = {}
    for note in all_note_infos:
        srcs = set()
        field_names = mw.col.models.field_names(mw.col.models.get(note.mid))
        for i, field in enumerate(note.fields):
            if field_names[i] in CONFIG.get("fields_to_scan_for_images", []):
                imgs = extract_images(field)
                srcs.update(extract_srcs(imgs))
        note_to_srcs[note.id] = srcs

    for nid, srcs in note_to_srcs.items():
        if srcs:
            src_to_note_ids[frozenset(srcs)].append(nid)

    for shared_srcs, nids in src_to_note_ids.items():
        if len(nids) >= 2:
            for nid in nids:
                if nid not in recipients and nid not in all_used_donors:
                    note = mw.col.get_note(nid)
                    note.tags = list(set(note.tags) | {unchanged_tag})
                    same_tagged_nids.append(nid)
                    mw.col.update_note(note)

    for shared_srcs, nids in src_to_note_ids.items():
        if len(nids) >= 2 and not any(n in recipients for n in nids):
            for nid in nids:
                if nid not in same_tagged_nids:
                    note = mw.col.get_note(nid)
                    note.tags = list(set(note.tags) | {unchanged_tag})
                    same_tagged_nids.append(nid)
                    mw.col.update_note(note)

    if same_tagged_nids:
        formatted_same = "✅ IMG_Uni::same tagged:\nNID:" + " OR NID:".join(str(nid) for nid in sorted(same_tagged_nids))
        log_entries.append(formatted_same)

    summary = f"📊 Summary:\n🧬 Images Merged: {merged}\n🧾 Notes Tagged Same: {len(same_tagged_nids)}\n"
    log_entries.insert(0, summary)

    if merged == 0:
        show_log_window("\n\n".join(log_entries) if log_entries else "No images were merged and no taggable group actions were logged.")
        return

    log_dir = Path(addon_path) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"merged_images_log_{int(time.time())}.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(log_entries))

    show_log_window("\n\n".join(log_entries))


def merge_images_main(browser=None, threshold=None, base_tag=None):
    if browser is None:
        browser = dialogs.open("Browser", mw)
    note_ids = browser.selectedNotes()
    run_merge_images(note_ids, threshold=threshold, base_tag=base_tag, browser=browser)


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


# Delete old logs utility
def delete_old_logs(days=7):
    log_dir = Path(addon_path) / "logs"
    if not log_dir.exists():
        return
    cutoff = datetime.now() - timedelta(days=days)
    for log_file in log_dir.glob("*.txt"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                log_file.unlink()
        except Exception as e:
            print(f"[MergeImages] Failed to delete {log_file.name}: {e}")