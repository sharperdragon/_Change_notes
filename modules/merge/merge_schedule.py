import os
from datetime import datetime
from aqt import mw
from aqt.utils import tooltip
from difflib import SequenceMatcher
from ..assets.scrub_match_sched import load_replacements
from ...config_manager import ConfigManager


def run_merge_by_similarity(config_section, field_index, merge_function, tag_on_merge=None, context_name="", browser=None):
    from ..assets.scrub_match_sched import normalize, prompt_threshold
    threshold = float(prompt_threshold(default=config_section.get("merge_similarity_threshold", "0.94")))
    selected_ids = browser.selectedNotes()

    log_dir = os.path.expanduser("~/Library/Application Support/Anki2/addons21/_Change_notes/modules/logs/merge_sched")
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "merge_log.txt")
    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write(f"[{datetime.now()}] Merge Scheduling Log Started\n\n")

    notes = [mw.col.get_note(nid) for nid in selected_ids]

    replacements = load_replacements() if config_section.get("use_text_replacements") else {}

    def clean(text):
        return normalize(text)

    matches = []
    seen = set()
    text_map = {}

    for i, n1 in enumerate(notes):
        text1 = clean(n1.fields[field_index])
        for j in range(i + 1, len(notes)):
            n2 = notes[j]
            text2 = clean(n2.fields[field_index])
            sim = SequenceMatcher(None, text1, text2).ratio()
            if sim >= threshold:
                matches.append((n1, n2))

    # Build match frequency map
    freq = {}
    for n1, n2 in matches:
        freq[n1.id] = freq.get(n1.id, 0) + 1
        freq[n2.id] = freq.get(n2.id, 0) + 1

    # Filter to 1-to-1 only
    final_pairs = [(a, b) for a, b in matches if freq[a.id] == 1 and freq[b.id] == 1]
    merged = 0
    merged_ids = set()

    for n1, n2 in final_pairs:
        if n1.id in merged_ids or n2.id in merged_ids:
            continue

        card1, card2 = n1.cards()[0], n2.cards()[0]
        if card1.reps != card2.reps:
            donor, receiver = (n1, n2) if card1.reps > card2.reps else (n2, n1)
        else:
            revlog = mw.col.db
            r1 = revlog.scalar("SELECT MIN(id) FROM revlog WHERE cid = ?", card1.id) or 0
            r2 = revlog.scalar("SELECT MIN(id) FROM revlog WHERE cid = ?", card2.id) or 0
            if r1 != r2:
                donor, receiver = (n1, n2) if r1 < r2 else (n2, n1)
            else:
                donor, receiver = (n1, n2) if card1.due > card2.due else (n2, n1)

        if merge_function(donor, receiver):
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(
                    f"[{datetime.now()}] MERGED\n"
                    f"  Donor   → Note ID: {donor.id}, Card ID: {donor.cards()[0].id}, Reps: {donor.cards()[0].reps}, Field: {donor.fields[field_index]}\n"
                    f"  Receiver→ Note ID: {receiver.id}, Card ID: {receiver.cards()[0].id}, Reps: {receiver.cards()[0].reps}, Field: {receiver.fields[field_index]}\n\n"
                )
            if tag_on_merge:
                for n in (donor, receiver):
                    if tag_on_merge not in n.tags:
                        n.add_tag(tag_on_merge)
                        n.flush()
            merged_ids.update([donor.id, receiver.id])
            merged += 1

    tooltip(f"{merged} {context_name} pairs merged.")
def run_merge_scheduling(browser):
    from ..utils import get_field_index_from_config

    config = mw.addonManager.getConfig(__name__)
    sched_config = config.get("merge_scheduling", {})
    field_index = sched_config.get("merge_field_index", 0)
    tag = sched_config.get("tag_on_merge")

    def scheduling_merge_function(donor, receiver):
        donor_card = donor.cards()[0]
        receiver_card = receiver.cards()[0]

        # Apply scheduling from donor to receiver — no restrictions
        receiver_card.ivl = donor_card.ivl
        receiver_card.due = donor_card.due
        receiver_card.factor = donor_card.factor
        receiver_card.reps = donor_card.reps
        receiver_card.lapses = donor_card.lapses
        receiver_card.left = donor_card.left
        receiver_card.odue = donor_card.odue
        receiver_card.type = donor_card.type
        receiver_card.queue = donor_card.queue
        receiver_card.flush()
        return True

    run_merge_by_similarity(
        config_section=sched_config,
        field_index=field_index,
        merge_function=scheduling_merge_function,
        tag_on_merge=tag,
        context_name="Scheduling",
        browser=browser
    )