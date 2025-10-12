# Add missing imports
import os, re, json, time
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timedelta
# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt import mw
from aqt.qt import QInputDialog, QMessageBox, QDialogButtonBox, QTextEdit, QDialog, QVBoxLayout, QPushButton, QAction, QDoubleSpinBox
from aqt.browser import Browser
from aqt.gui_hooks import browser_will_show_context_menu

config = {
    "default_threshold": 0.90,
    "min_threshold": 0.80,
    "max_threshold": 1.0,
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
    ],

    "merge_behavior": {
        "wrap_images_in_div": True,
        "insert_new_line_between_images": True,
        "append_to_existing_field": True,
    },

    "logging": {
        "enable_log_popup": True,
        "save_log_to_desktop": True,
        "log_filename_prefix": "merged_images_log_",
    },

    "tagging": {
        "add_to_merged": "IMG_Uni::received",
        "add_to_donor": "IMG_Uni::donor",
        "add_to_unchanged": "IMG_Uni::same",
    },
}

# === Config Access & Runtime Caches ===
CONFIG = config

def cfg(path: str, default=None):
    """
    ! Config getter that walks dot paths, e.g. cfg("logging.enable_log_popup", True)
    """
    node = CONFIG
    for key in path.split("."):
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return default
    return node

# Add-on path and caches
addon_path = Path(mw.addonManager.addonsFolder()) / "_Change_notes"
FIELD_NAMES_BY_MID: dict[int, list[str]] = {}
SCAN_FIELDS = set(cfg("fields_to_scan_for_images", []))

def get_field_names(note):
    mid = note.mid
    if mid not in FIELD_NAMES_BY_MID:
        FIELD_NAMES_BY_MID[mid] = mw.col.models.field_names(mw.col.models.get(mid))
    return FIELD_NAMES_BY_MID[mid]

def has_excluded_tag(note) -> bool:
    excluded = set(cfg("excluded_tags", []))
    if not excluded:
        return False
    return bool(excluded & set(note.tags))

def is_model_allowed(note) -> bool:
    allowed = cfg("allowed_models", [])
    if not allowed:
        return True
    model_name = mw.col.models.get(note.mid)["name"]
    return model_name in allowed


from .utils import (
    extract_images,
    extract_srcs,
    clean_img_tag,
    normalize_cloze_content,
    normalize,
    group_notes_by_similarity,
)


def prompt_threshold(default, minimum, maximum, step=0.01, decimals=2):
    dialog = QDialog(mw)
    dialog.setWindowTitle("Fuzzy Threshold")

    layout = QVBoxLayout(dialog)
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(decimals)
    spin.setSingleStep(step)
    spin.setValue(default)

    layout.addWidget(spin)

    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    layout.addWidget(button_box)

    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)

    if dialog.exec() == QDialog.Accepted:
        return spin.value(), True
    return None, False

def run_merge_images(note_ids: list[int], browser=None):
    if not note_ids:
        QMessageBox.information(mw, "Unify Images", "No notes selected.")
        return

    default_threshold = cfg("default_threshold", 0.98)
    min_threshold = cfg("min_threshold", 0.85)
    max_threshold = cfg("max_threshold", 1.0)
    ask_each = cfg("ask_threshold_each_time", True)

    if ask_each:
        t, ok = prompt_threshold(default_threshold, min_threshold, max_threshold)
        if not ok:
            return
        threshold = max(min(t, max_threshold), min_threshold)
    else:
        threshold = max(min(default_threshold, max_threshold), min_threshold)

    if browser is None:
        browser = mw.form.browser

    all_note_infos = [mw.col.get_note(nid) for nid in note_ids]
    # Apply model + tag gating from config
    candidates = [n for n in all_note_infos if is_model_allowed(n) and not has_excluded_tag(n)]

    received_tag = cfg("tagging.add_to_merged", "IMG_Uni::received")
    unchanged_tag = cfg("tagging.add_to_unchanged", "IMG_Uni::same")
    donor_tag   = cfg("tagging.add_to_donor", "IMG_Uni::donor")
    enable_popup = cfg("logging.enable_log_popup", True)
    save_to_desktop = cfg("logging.save_log_to_desktop", False)
    log_prefix = cfg("logging.log_filename_prefix", "merged_images_log_")

    note_groups = group_notes_by_similarity(candidates, threshold, "Text", has_excluded_tag)
    # Merge behavior flags
    wrap_in_div = cfg("merge_behavior.wrap_images_in_div", True)
    insert_br = cfg("merge_behavior.insert_new_line_between_images", True)
    append_to_existing = cfg("merge_behavior.append_to_existing_field", True)

    def make_block(src_list, src_map):
        """Build an HTML block for a list of srcs respecting config flags."""
        if not src_list:
            return ""
        imgtags = [src_map[s] for s in src_list if s in src_map]
        if not imgtags:
            return ""
        body = "<br>".join(imgtags) if insert_br else "".join(imgtags)
        return f"<div>{body}</div>" if wrap_in_div else body

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
                    field_name = get_field_names(donor)[i]
                    if field_name not in SCAN_FIELDS:
                        continue
                    raw_imgs = extract_images(field)
                    cleaned_imgs = [clean_img_tag(img) for img in raw_imgs if clean_img_tag(img)]
                    for img in cleaned_imgs:
                        if img not in field_to_images[i]:
                            field_to_images[i].append(img)

            # Build ordered src list per field to respect donor ordering
            field_to_src_order = {}
            for idx, imgs in field_to_images.items():
                ordered_srcs = []
                for img in imgs:
                    m = re.search(r'src="([^"]+)"', img)
                    if m:
                        ordered_srcs.append(m.group(1))
                field_to_src_order[idx] = ordered_srcs
            # Map src -> full <img> tag for quick reconstruction
            src_to_imgtag = {}
            for idx, imgs in field_to_images.items():
                for img in imgs:
                    m = re.search(r'src="([^"]+)"', img)
                    if m:
                        src_to_imgtag[m.group(1)] = img

            for note in model_group:
                updated_fields = list(note.fields)
                changed = False
                all_existing_imgs = set()
                field_names = get_field_names(note)
                for i, f in enumerate(note.fields):
                    field_name = field_names[i]
                    if field_name not in SCAN_FIELDS:
                        continue
                    all_existing_imgs.update(extract_images(f))
                all_existing_srcs = extract_srcs(all_existing_imgs)
                used_donors = set()

                for i, images in field_to_images.items():
                    donor_src_order = field_to_src_order.get(i, [])
                    # Existing images in this field (order as they appear in the note)
                    existing_imgs_ordered = extract_images(updated_fields[i])
                    existing_srcs_ordered = extract_srcs(existing_imgs_ordered)
                    existing_srcs_set = set(existing_srcs_ordered)

                    # Determine missing srcs in donor order
                    missing_srcs_ordered = [s for s in donor_src_order if s not in existing_srcs_set]

                    if not missing_srcs_ordered:
                        continue

                    # Identify where the recipient overlaps the donor order
                    shared_indices = [donor_src_order.index(s) for s in existing_srcs_ordered if s in donor_src_order]
                    first_shared_idx = min(shared_indices) if shared_indices else None
                    last_shared_idx = max(shared_indices) if shared_indices else None

                    # Split missing images into those that should be prepended vs appended
                    to_prepend_srcs = []
                    to_append_srcs = []
                    if first_shared_idx is None:
                        # No overlap: keep donor ordering; prepend everything so donor-leading images appear first
                        to_prepend_srcs = missing_srcs_ordered
                    else:
                        for s in missing_srcs_ordered:
                            idx_in_donor = donor_src_order.index(s)
                            if idx_in_donor < first_shared_idx:
                                to_prepend_srcs.append(s)
                            elif last_shared_idx is not None and idx_in_donor > last_shared_idx:
                                to_append_srcs.append(s)
                            else:
                                # Missing between first and last shared — append to end to avoid mid-string HTML surgery
                                to_append_srcs.append(s)

                    prepend_block = make_block(to_prepend_srcs, src_to_imgtag)
                    append_block = make_block(to_append_srcs, src_to_imgtag)

                    # Apply updates per config
                    original_html = updated_fields[i]
                    if append_to_existing:
                        if prepend_block:
                            updated_fields[i] = prepend_block + (original_html or "")
                        if not original_html and not prepend_block and append_block:
                            updated_fields[i] = append_block
                        elif append_block:
                            updated_fields[i] = updated_fields[i] + append_block
                    else:
                        # Replace the field content with only the newly constructed images
                        updated_fields[i] = (prepend_block or "") + (append_block or "")

                    # Track donors used for logging
                    missing_srcs = set(missing_srcs_ordered)
                    for donor in donors:
                        donor_srcs = set(extract_srcs(extract_images("".join(donor.fields))))
                        if donor_srcs & missing_srcs:
                            used_donors.add(donor.id)

                    changed = True

                    # Logging reflecting prepend/append
                    field_name = get_field_names(note)[i]
                    if to_prepend_srcs:
                        block = make_block(to_prepend_srcs, src_to_imgtag)
                        log_entries.append(f"🧬 Prepend to Note {note.id} field '{field_name}': {block} (donors={', '.join(str(d) for d in sorted(used_donors)) or 'None'})")
                    if to_append_srcs:
                        block = make_block(to_append_srcs, src_to_imgtag)
                        log_entries.append(f"🧬 Append to Note {note.id} field '{field_name}': {block} (donors={', '.join(str(d) for d in sorted(used_donors)) or 'None'})")
                    if not append_to_existing and (to_prepend_srcs or to_append_srcs):
                        log_entries.append(f"🔁 Replaced content in Note {note.id} field '{field_name}' due to append_to_existing_field=False")

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
        field_names = get_field_names(note)
        for i, field in enumerate(note.fields):
            if field_names[i] in SCAN_FIELDS:
                imgs = extract_images(field)
                srcs.update(extract_srcs(imgs))
        note_to_srcs[note.id] = srcs

    # Tag notes with no images at all
    no_images_tag = cfg("tagging.no_images_found", "IMG_Uni::no_images")
    for note in all_note_infos:
        if not note_to_srcs.get(note.id):
            note.tags = list(set(note.tags) | {no_images_tag})
            mw.col.update_note(note)

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
        if enable_popup and log_entries:
            show_log_window("\n\n".join(log_entries))
        else:
            show_log_window("No images were merged and no taggable group actions were logged.")
        return

    # Write logs to Desktop or addon logs dir based on config
    if save_to_desktop:
        log_dir = Path.home() / "Desktop"
    else:
        log_dir = Path(addon_path) / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"{log_prefix}{int(time.time())}.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(log_entries))

    if enable_popup:
        show_log_window("\n\n".join(log_entries))


def merge_images_main(browser=None):
    if browser is None:
        browser = mw.form.browser
    note_ids = browser.selectedNotes()
    run_merge_images(note_ids, browser)


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





# Delete old logs utility
def delete_old_logs(days=7):
    # Only prune addon logs dir; never touch Desktop
    save_to_desktop = cfg("logging.save_log_to_desktop", False)
    if save_to_desktop:
        return
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



def collect_used_donors_for_block(missing_imgs, donor_notes):
    used_donors = set()
    for donor in donor_notes:
        donor_imgs = extract_srcs(extract_images("".join(donor.fields)))
        for img in missing_imgs:
            src_match = re.search(r'src="([^"]+)"', img)
            if src_match:
                src = src_match.group(1)
                if src in donor_imgs:
                    used_donors.add(donor.id)
                    break