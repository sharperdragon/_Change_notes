import os
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

from aqt import mw
from aqt.utils import tooltip

from ..config_manager import ConfigManager


DEFAULT_SIMILARITY_THRESHOLD = 0.94
DEFAULT_ABORT_ON_CANCEL = True
DEFAULT_MULTI_CARD_POLICY = "skip"
MULTI_CARD_POLICIES = {"skip", "first_card", "all_cards"}


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return default


def _parse_threshold(value, default=DEFAULT_SIMILARITY_THRESHOLD) -> float:
    try:
        parsed = float(value)
    except Exception:
        parsed = float(default)
    if parsed > 1.0:
        parsed /= 100.0
    return max(0.0, min(parsed, 1.0))


def _normalize_multi_card_policy(value) -> str:
    policy = str(value or DEFAULT_MULTI_CARD_POLICY).strip().lower()
    return policy if policy in MULTI_CARD_POLICIES else DEFAULT_MULTI_CARD_POLICY


def _earliest_review_id(card_id: int) -> int:
    return mw.col.db.scalar("SELECT MIN(id) FROM revlog WHERE cid = ?", card_id) or 0


def _copy_scheduling(donor_card, receiver_card) -> None:
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


def run_merge_by_similarity(
    config_section,
    field_index,
    merge_function,
    tag_on_merge=None,
    context_name="",
    browser=None,
):
    from .assets.scrub_match_sched import normalize, prompt_threshold_with_cancel

    default_threshold = _parse_threshold(
        config_section.get("merge_similarity_threshold", DEFAULT_SIMILARITY_THRESHOLD),
        default=DEFAULT_SIMILARITY_THRESHOLD,
    )
    abort_on_cancel = _parse_bool(
        config_section.get("abort_on_cancel", DEFAULT_ABORT_ON_CANCEL),
        default=DEFAULT_ABORT_ON_CANCEL,
    )
    multi_card_policy = _normalize_multi_card_policy(
        config_section.get("multi_card_policy", DEFAULT_MULTI_CARD_POLICY)
    )

    threshold, accepted = prompt_threshold_with_cancel(default=default_threshold)
    if not accepted:
        if abort_on_cancel:
            tooltip("Merge Scheduling cancelled. No changes were applied.")
            return {
                "aborted": True,
                "reason": "user_cancelled_threshold_prompt",
                "merged_pairs": 0,
            }
        threshold = default_threshold

    selected_ids = browser.selectedNotes()
    log_dir = Path(__file__).resolve().parents[1] / "logs" / "merge_sched"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(str(log_dir), "merge_log.txt")

    with open(log_path, "w", encoding="utf-8") as log_file:
        log_file.write(
            f"[{datetime.now()}] Merge Scheduling Log Started\n"
            f"  threshold={threshold:.4f}, policy={multi_card_policy}, "
            f"abort_on_cancel={abort_on_cancel}\n\n"
        )

    notes = [mw.col.get_note(nid) for nid in selected_ids]
    matches = []

    for i, n1 in enumerate(notes):
        if field_index >= len(n1.fields):
            continue
        text1 = normalize(n1.fields[field_index])
        for j in range(i + 1, len(notes)):
            n2 = notes[j]
            if field_index >= len(n2.fields):
                continue
            text2 = normalize(n2.fields[field_index])
            if SequenceMatcher(None, text1, text2).ratio() >= threshold:
                matches.append((n1, n2))

    freq = {}
    for n1, n2 in matches:
        freq[n1.id] = freq.get(n1.id, 0) + 1
        freq[n2.id] = freq.get(n2.id, 0) + 1
    final_pairs = [(a, b) for a, b in matches if freq[a.id] == 1 and freq[b.id] == 1]

    merged_pairs = 0
    merged_cards_total = 0
    merged_ids = set()
    skipped_no_cards = 0
    skipped_multi_card = 0
    skipped_no_common_templates = 0
    skipped_already_consumed = 0

    for n1, n2 in final_pairs:
        if n1.id in merged_ids or n2.id in merged_ids:
            skipped_already_consumed += 1
            continue

        cards1 = n1.cards()
        cards2 = n2.cards()
        if not cards1 or not cards2:
            skipped_no_cards += 1
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(
                    f"[{datetime.now()}] SKIP no cards\n"
                    f"  Note IDs: {n1.id}, {n2.id}\n\n"
                )
            continue

        if multi_card_policy == "skip" and (len(cards1) != 1 or len(cards2) != 1):
            skipped_multi_card += 1
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(
                    f"[{datetime.now()}] SKIP multi-card pair\n"
                    f"  Note IDs: {n1.id} (cards={len(cards1)}), {n2.id} (cards={len(cards2)})\n\n"
                )
            continue

        card1, card2 = cards1[0], cards2[0]
        if card1.reps != card2.reps:
            donor, receiver = (n1, n2) if card1.reps > card2.reps else (n2, n1)
            donor_metric_card = card1 if donor.id == n1.id else card2
            receiver_metric_card = card2 if donor.id == n1.id else card1
        else:
            r1 = _earliest_review_id(card1.id)
            r2 = _earliest_review_id(card2.id)
            if r1 != r2:
                donor, receiver = (n1, n2) if r1 < r2 else (n2, n1)
                donor_metric_card = card1 if donor.id == n1.id else card2
                receiver_metric_card = card2 if donor.id == n1.id else card1
            else:
                donor, receiver = (n1, n2) if card1.due > card2.due else (n2, n1)
                donor_metric_card = card1 if donor.id == n1.id else card2
                receiver_metric_card = card2 if donor.id == n1.id else card1

        merged_ok, merged_cards, reason = merge_function(
            donor,
            receiver,
            donor_metric_card,
            receiver_metric_card,
            multi_card_policy,
        )
        if not merged_ok:
            if reason == "no_common_card_templates":
                skipped_no_common_templates += 1
            with open(log_path, "a", encoding="utf-8") as log_file:
                log_file.write(
                    f"[{datetime.now()}] SKIP merge_function returned false ({reason})\n"
                    f"  Donor Note ID: {donor.id}, Receiver Note ID: {receiver.id}\n\n"
                )
            continue

        with open(log_path, "a", encoding="utf-8") as log_file:
            log_file.write(
                f"[{datetime.now()}] MERGED\n"
                f"  Donor   → Note ID: {donor.id}, Card ID: {donor_metric_card.id}, Reps: {donor_metric_card.reps}, Field: {donor.fields[field_index]}\n"
                f"  Receiver→ Note ID: {receiver.id}, Card ID: {receiver_metric_card.id}, Reps: {receiver_metric_card.reps}, Field: {receiver.fields[field_index]}\n"
                f"  Cards merged: {merged_cards}\n\n"
            )

        if tag_on_merge:
            for note in (donor, receiver):
                if tag_on_merge not in note.tags:
                    note.add_tag(tag_on_merge)
                    note.flush()

        merged_ids.update([donor.id, receiver.id])
        merged_pairs += 1
        merged_cards_total += merged_cards

    summary = (
        f"{merged_pairs} {context_name} pairs merged "
        f"({merged_cards_total} card updates). "
        f"Skipped: no-cards={skipped_no_cards}, "
        f"multi-card={skipped_multi_card}, "
        f"no-common-templates={skipped_no_common_templates}, "
        f"already-consumed={skipped_already_consumed}."
    )
    tooltip(summary)

    with open(log_path, "a", encoding="utf-8") as log_file:
        log_file.write(
            f"[{datetime.now()}] SUMMARY\n"
            f"  merged_pairs={merged_pairs}\n"
            f"  merged_cards_total={merged_cards_total}\n"
            f"  skipped_no_cards={skipped_no_cards}\n"
            f"  skipped_multi_card={skipped_multi_card}\n"
            f"  skipped_no_common_templates={skipped_no_common_templates}\n"
            f"  skipped_already_consumed={skipped_already_consumed}\n"
        )

    return {
        "aborted": False,
        "merged_pairs": merged_pairs,
        "merged_cards_total": merged_cards_total,
        "skipped_no_cards": skipped_no_cards,
        "skipped_multi_card": skipped_multi_card,
        "skipped_no_common_templates": skipped_no_common_templates,
        "skipped_already_consumed": skipped_already_consumed,
    }


def run_merge_scheduling(browser):
    sched_config = ConfigManager.get_effective_section_with_aliases(
        "merge_scheduling",
        aliases=("merge_scheduling_config",),
    )
    if not sched_config:
        sched_config = ConfigManager("merge_scheduling").load()
    try:
        field_index = int(sched_config.get("merge_field_index", 0))
    except Exception:
        field_index = 0
    tag = sched_config.get("tag_on_merge")

    def scheduling_merge_function(donor, receiver, donor_card, receiver_card, policy):
        if policy == "all_cards":
            donor_by_ord = {card.ord: card for card in donor.cards()}
            receiver_by_ord = {card.ord: card for card in receiver.cards()}
            common_ords = sorted(set(donor_by_ord.keys()) & set(receiver_by_ord.keys()))
            if not common_ords:
                return False, 0, "no_common_card_templates"
            for ord_ in common_ords:
                _copy_scheduling(donor_by_ord[ord_], receiver_by_ord[ord_])
            return True, len(common_ords), "ok"

        _copy_scheduling(donor_card, receiver_card)
        return True, 1, "ok"

    return run_merge_by_similarity(
        config_section=sched_config,
        field_index=field_index,
        merge_function=scheduling_merge_function,
        tag_on_merge=tag,
        context_name="Scheduling",
        browser=browser,
    )
