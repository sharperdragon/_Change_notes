# merge_all.py
# pyright: reportMissingImports=false
# mypy: ignore-errors

# =========================
# === Config (top) ========
# =========================
DEFAULT_THRESHOLD = 0.96       # $ sensible default if user cancels the dialog
MIN_THRESHOLD      = 0.80
MAX_THRESHOLD      = 1.00
THRESH_STEP        = 0.01
COMPARE_FIELD_NAME = "Text"    # $ which field to fuzzy-compare
TAG_BASE_LABEL     = "DUPE_Merged"   # $ parent tag applied to any merged pair
TAG_MULTI_CHILD    = "multiple"      # $ child tag if both notes had non-overlapping extras
ADD_TAG_ON_MERGE   = True
LOG_DIR_NAME       = "merge_all"     # $ logs/merge_all/*.txt inside this add-on
SCHED_POLICY       = "keep_more_reviewed"  


# ^ options: "keep_more_reviewed" | "keep_newer" | "prefer_receiver"
# ! SCHED_POLICY chooses whose scheduling data (due/ivl/ease/reps/lapses) we copy to the *other* note's first card.

# =========================
# === Imports ============
# =========================
import os, time, re, hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from aqt import mw
from aqt.browser import Browser
from aqt.gui_hooks import browser_will_show_context_menu
from aqt.qt import QDialog, QVBoxLayout, QDoubleSpinBox, QLabel, QDialogButtonBox, QAction
from aqt.utils import tooltip

# -- Prefer shared utils.py (single source of truth)
try:
    # ? If your package is something like ".../addons21/_merge_images/", adjust the relative import as needed.
    from .utils import (
        normalize,
        group_notes_by_similarity,
    )
except Exception:
    # ! If utils cannot be imported, fall back to a trivial normalizer + matcher (keeps this file usable)
    from difflib import SequenceMatcher
    def normalize(s: str) -> str:
        s = re.sub(r"<[^>]+>", "", s or "").strip().lower()
        s = re.sub(r"\s+", " ", s)
        return s
    def group_notes_by_similarity(note_infos, threshold, field_name="Text", has_excluded_tag=lambda n: False):
        # minimal grouping (O(n^2)), acceptable for small selections
        buckets = []
        for n in note_infos:
            if has_excluded_tag(n): 
                continue
            model = mw.col.models.get(n.mid)
            field_names = [f["name"] for f in model["flds"]]
            if field_name not in field_names:
                continue
            idx = field_names.index(field_name)
            key = normalize(n.fields[idx])
            placed = False
            for bucket in buckets:
                if SequenceMatcher(None, key, bucket["key"]).ratio() >= threshold:
                    bucket["items"].append(n)
                    placed = True
                    break
            if not placed:
                buckets.append({"key": key, "items": [n]})
        # convert to dict-like structure {key: [notes...]}
        out = defaultdict(list)
        for b in buckets:
            out[b["key"]].extend(b["items"])
        return out

# =========================
# === UI: threshold ======
# =========================
def ask_threshold_once(default=DEFAULT_THRESHOLD, lo=MIN_THRESHOLD, hi=MAX_THRESHOLD, step=THRESH_STEP) -> float | None:
    """Spinner dialog for a single threshold prompt.
       If utils.prompt_fuzzy_threshold exists, you can import & use that instead."""
    # Attempt to use shared prompt if present
    try:
        from .utils import prompt_fuzzy_threshold as _shared_prompt
        val = _shared_prompt(default=str(default))  # many existing helpers return str
        return None if val in (None, "") else float(val)
    except Exception:
        pass

    d = QDialog(mw)
    d.setWindowTitle("Fuzzy Threshold")
    lay = QVBoxLayout(d)
    lay.addWidget(QLabel("Choose similarity threshold (0–1):"))
    spin = QDoubleSpinBox(d)
    spin.setRange(lo, hi)
    spin.setSingleStep(step)
    spin.setDecimals(2)
    spin.setValue(default)
    lay.addWidget(spin)
    btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, parent=d)
    lay.addWidget(btns)
    btns.accepted.connect(d.accept)
    btns.rejected.connect(d.reject)
    if d.exec():
        return float(spin.value())
    return None

# =========================
# === Logging ============
# =========================
def _log_path() -> Path:
    root = Path(__file__).parent / "logs" / LOG_DIR_NAME
    root.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return root / f"merge_{ts}.txt"

def _log_write(fp: Path, msg: str) -> None:
    with open(fp, "a", encoding="utf-8") as f:
        f.write(msg if msg.endswith("\n") else msg + "\n")

# =========================
# === Helpers ============
# =========================
def _first_card(note):
    cards = note.cards()
    return cards[0] if cards else None

def _img_srcs_from_html(html: str) -> set[str]:
    # very light parser; relies on distinct src attribute
    return set(re.findall(r'<img[^>]+src="([^"]+)"', html or "", flags=re.I))

def _inject_img_if_missing(field_html: str, donor_img_tag: str) -> str:
    """Simple append for minimalism; keep your existing 'clean_img_tag' if needed."""
    if donor_img_tag in (field_html or ""):
        return field_html
    return (field_html or "") + ("\n" if field_html else "") + donor_img_tag

def _pick_sched_source(a, b, policy=SCHED_POLICY):
    ca, cb = _first_card(a), _first_card(b)
    if not ca or not cb:
        return a  # fallback
    if policy == "prefer_receiver":
        return b
    if policy == "keep_newer":
        return a if a.mod > b.mod else b
    # default: keep_more_reviewed
    return a if ca.reps >= cb.reps else b

def _copy_sched(from_note, to_note):
    """Copy basic scheduling stats from from_note's first card → to_note's first card."""
    src, dst = _first_card(from_note), _first_card(to_note)
    if not src or not dst:
        return
    # ! This touches scheduling; keep it conservative.
    dst.type   = src.type
    dst.queue  = src.queue
    dst.due    = src.due
    dst.ivl    = src.ivl
    dst.left   = src.left
    dst.factor = src.factor
    dst.reps   = src.reps
    dst.lapses = src.lapses
    dst.flush()

# =========================
# === Core merge ops =====
# =========================
def merge_images(donor, receiver, field_name=COMPARE_FIELD_NAME) -> int:
    """Add any donor <img> tags that receiver lacks (compares by src)."""
    model = mw.col.models.get(receiver.mid)
    flds = [f["name"] for f in model["flds"]]
    if field_name not in flds:
        return 0
    idx = flds.index(field_name)
    r_html = receiver.fields[idx]
    d_html = donor.fields[idx]

    r_srcs = _img_srcs_from_html(r_html)
    added = 0
    for m in re.finditer(r'(<img[^>]*src="([^"]+)"[^>]*>)', d_html or "", flags=re.I):
        tag, src = m.group(1), m.group(2)
        if src not in r_srcs:
            r_html = _inject_img_if_missing(r_html, tag)
            r_srcs.add(src)
            added += 1
    if added:
        receiver.fields[idx] = r_html
        receiver.flush()
    return added

def merge_tags(donor, receiver) -> int:
    """Union donor tags into receiver; add base label and optional 'multiple' child if both had extras."""
    before = set(receiver.tags)
    receiver_tags = set(receiver.tags)
    donor_tags = set(donor.tags)
    # $ leave out Anki internals
    drop = {"leech", "marked"}
    receiver_tags = {t for t in receiver_tags if t not in drop}
    donor_tags    = {t for t in donor_tags if t not in drop}

    # detect if both had non-overlapping extras
    non_overlap = (receiver_tags - donor_tags) and (donor_tags - receiver_tags)

    merged = sorted(receiver_tags | donor_tags)
    receiver.tags = list(merged)
    if ADD_TAG_ON_MERGE:
        base = TAG_BASE_LABEL
        if base not in receiver.tags:
            receiver.add_tag(base)
        if non_overlap:
            child = f"{TAG_BASE_LABEL}::{TAG_MULTI_CHILD}"
            if child not in receiver.tags:
                receiver.add_tag(child)

    receiver.flush()
    return int(set(receiver.tags) != before)

def merge_scheduling(donor, receiver) -> int:
    """Copy chosen scheduling (per SCHED_POLICY) from selected source to the other note."""
    src = _pick_sched_source(donor, receiver, policy=SCHED_POLICY)
    dst = receiver if src is donor else donor
    _copy_sched(src, dst)
    return 1

# =========================
# === Orchestrator =======
# =========================
def run_merge_all(browser: Browser) -> None:
    threshold = ask_threshold_once(default=DEFAULT_THRESHOLD,
                                   lo=MIN_THRESHOLD, hi=MAX_THRESHOLD, step=THRESH_STEP)
    if threshold is None:
        return

    log_fp = _log_path()
    _log_write(log_fp, f"[{datetime.now()}] Merge-All start | threshold={threshold} | field={COMPARE_FIELD_NAME}")

    nids = browser.selectedNotes()
    if not nids:
        tooltip("No notes selected.")
        return
    notes = [mw.col.get_note(nid) for nid in nids]

    # Group by fuzzy-similarity using the shared utils matcher
    groups = group_notes_by_similarity(notes, threshold, field_name=COMPARE_FIELD_NAME)

    total_pairs = 0
    imgs_added = 0
    tag_unions = 0
    sched_copies = 0

    for _, cluster in groups.items():
        # Only act on 2+ sized clusters
        if len(cluster) < 2:
            continue
        # Process as pairwise merges against the first item (simple, predictable)
        base = cluster[0]
        for other in cluster[1:]:
            total_pairs += 1

            # === Images
            imgs_added += merge_images(donor=other, receiver=base, field_name=COMPARE_FIELD_NAME)

            # === Tags
            tag_unions += merge_tags(donor=other, receiver=base)

            # === Scheduling
            sched_copies += merge_scheduling(donor=other, receiver=base)

            _log_write(
                log_fp,
                f"- Pair merged | base={base.id} other={other.id} | imgs+={imgs_added} tags+={tag_unions} sched+={sched_copies}"
            )

    mw.col.reset()
    tooltip(f"Merge-All complete • pairs={total_pairs} • imgs added={imgs_added} • tag merges={tag_unions} • sched syncs={sched_copies}")


