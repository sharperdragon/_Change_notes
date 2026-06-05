from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher
from PyQt6.QtWidgets import QInputDialog

# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt import mw
from aqt.utils import showInfo
from aqt.browser import Browser

# Dynamically add the modules directory to sys.path
from ..config_manager import ConfigManager
from .assets.scrub_match import (
    normalize
)
from .shared.defaults import MERGE_TAGS_DEFAULTS
from .shared.parsing import parse_bool
from .utils import prompt_checkbox_option

DEBUG_MODE = False
config = {}
base_tag = MERGE_TAGS_DEFAULTS["base_tag"]
merged_tag = f"{base_tag}::{datetime.now().strftime('%B_%d')}"
ALLOWED_PARENTS = []
ALLOWED_PARENTS_LOWER = []
EXCLUDED_TRANSFER_TAGS = []
EXCLUDED_TRANSFER_TAGS_LOWER = []
MERGE_SELECT_ONLY = False

MERGE_TAGS_LOG_FOLDER = "logs"
MERGE_TAGS_DESKTOP_LOG_SUBFOLDER = Path("anki_logs") / "Merge Tags"
PROMPT_LOG_EXPORT_CHECKBOX_DEFAULT = True
PROMPT_LOG_EXPORT_CHECKBOX_LABEL = "Export log .txt to Desktop/subfolder"
PROMPT_LOG_EXPORT_TITLE = "Merge Tags Log Export"
PROMPT_LOG_EXPORT_MEMORY_SECTION = "merge_tags_config"
PROMPT_LOG_EXPORT_MEMORY_KEY = "export_log_to_desktop"

LOG_DIR = Path(mw.addonManager.addonsFolder()) / "_Change_notes" / MERGE_TAGS_LOG_FOLDER / "merge_tags"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m')}_merge_tags.log"


def _as_string_list(value) -> list[str]:
    """Normalize config value into a clean list of non-empty strings."""
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if not isinstance(value, (list, tuple, set)):
        return []
    normalized = []
    for item in value:
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                normalized.append(stripped)
    return normalized


def _safe_float(value, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _global_fuzzy_opts() -> tuple[float, float]:
    """Return (default_fuzz, min_fuzz) sourced from global_config.fuzzy_opts."""
    fuzzy_opts = config.get("fuzzy_opts")
    if not isinstance(fuzzy_opts, dict):
        fuzzy_opts = {}
    default_fuzzy = _safe_float(
        fuzzy_opts.get("default_fuzz"),
        MERGE_TAGS_DEFAULTS["run_default_fuzzy"],
    )
    min_fuzzy = _safe_float(
        fuzzy_opts.get("min_fuzz"),
        MERGE_TAGS_DEFAULTS["min_fuzzy"],
    )
    return default_fuzzy, min_fuzzy


def _reload_runtime_config():
    global config
    global base_tag
    global merged_tag
    global ALLOWED_PARENTS
    global ALLOWED_PARENTS_LOWER
    global EXCLUDED_TRANSFER_TAGS
    global EXCLUDED_TRANSFER_TAGS_LOWER
    global MERGE_SELECT_ONLY

    global_cfg = ConfigManager("global_config").load()
    section_cfg = ConfigManager("merge_tags_config").load()
    config = ConfigManager.deep_merge_dicts(global_cfg, section_cfg)

    base_tag = config.get("base_tag", MERGE_TAGS_DEFAULTS["base_tag"])
    date_suffix = datetime.now().strftime("%B_%d")
    merged_tag = f"{base_tag}::{date_suffix}"

    parents_new = config.get("merge_only_parents")
    ALLOWED_PARENTS = _as_string_list(parents_new)
    ALLOWED_PARENTS_LOWER = [p.lower() for p in ALLOWED_PARENTS]

    excluded_tags = config.get("excluded_tags")
    EXCLUDED_TRANSFER_TAGS = _as_string_list(excluded_tags)
    EXCLUDED_TRANSFER_TAGS_LOWER = [t.lower() for t in EXCLUDED_TRANSFER_TAGS]

    MERGE_SELECT_ONLY = parse_bool(
        config.get("merge_select_only", MERGE_TAGS_DEFAULTS["merge_select_only"]),
        default=MERGE_TAGS_DEFAULTS["merge_select_only"],
    )

# Helper: case-insensitive parent check
def _is_tag_in_parents(tag: str) -> bool:
    """
    Returns True if tag equals a parent or starts with 'parent::'
    Comparison is case-insensitive.
    """
    t = tag.lower()
    for pl in ALLOWED_PARENTS_LOWER:
        if t == pl or t.startswith(pl + "::"):
            return True
    return False


def _is_tag_excluded_from_transfer(tag: str) -> bool:
    """
    Returns True if tag equals an excluded tag or starts with 'excluded_tag::'
    Comparison is case-insensitive.
    """
    t = tag.lower()
    for ex in EXCLUDED_TRANSFER_TAGS_LOWER:
        if t == ex or t.startswith(ex + "::"):
            return True
    return False

# Gate: if MERGE_SELECT_ONLY is False, allow all tags (parents list ignored per spec)
def tag_is_allowed(tag: str) -> bool:
    if _is_tag_excluded_from_transfer(tag):
        return False
    if not MERGE_SELECT_ONLY:
        return True
    return _is_tag_in_parents(tag)





def log_debug(msg):
    timestamped = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}"
    if DEBUG_MODE:
        print(timestamped)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(timestamped + "\n")


def prompt_merge_tags_log_export(parent=None) -> bool | None:
    """Ask whether to export a run log to Desktop/subfolder."""
    return prompt_checkbox_option(
        title=PROMPT_LOG_EXPORT_TITLE,
        checkbox_label=PROMPT_LOG_EXPORT_CHECKBOX_LABEL,
        checked=PROMPT_LOG_EXPORT_CHECKBOX_DEFAULT,
        remember_section=PROMPT_LOG_EXPORT_MEMORY_SECTION,
        remember_key=PROMPT_LOG_EXPORT_MEMORY_KEY,
        parent=parent,
    )


def _write_desktop_run_log(lines: list[str]) -> Path | None:
    """Write merge-tags run log to Desktop subfolder and return the path."""
    if not lines:
        return None
    try:
        desktop_dir = Path.home() / "Desktop" / MERGE_TAGS_DESKTOP_LOG_SUBFOLDER
        desktop_dir.mkdir(parents=True, exist_ok=True)
        out_path = desktop_dir / f"merge_tags_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        return out_path
    except Exception as e:
        log_debug(f"Desktop log export failed: {e!r}")
        return None

# Log effective config (once per module import)
_reload_runtime_config()
log_debug(
    f"Config — MERGE_SELECT_ONLY={MERGE_SELECT_ONLY}, "
    f"ALLOWED_PARENTS={ALLOWED_PARENTS if MERGE_SELECT_ONLY else '(ignored)'}, "
    f"EXCLUDED_TRANSFER_TAGS={EXCLUDED_TRANSFER_TAGS or '(none)'}"
)

# --- Fuzzy matching helper ---

def prompt_fuzzy_threshold(default=None, parent=None):
    """Prompt user for fuzzy threshold (0–100) using a popup input dialog."""
    if default is None:
        default_fuzzy, _ = _global_fuzzy_opts()
        default = int(default_fuzzy * 100)
    dialog_parent = parent or mw
    val, ok = QInputDialog.getInt(
        dialog_parent, "Set Fuzzy Match Threshold",
        "Select fuzzy match threshold (0 = loose, 100 = strict):",
        default, 85, 100, 1
    )
    if ok:
        return val / 100  # Normalize to 0.0–1.0 range
    return None

def unify_tags_on_duplicates(
    browser: Browser,
    threshold: float | None = None,
    export_log_to_desktop: bool = False,
    show_summary_popup: bool = True,
):
    _reload_runtime_config()
    skipped_by_parent_filter = 0
    skipped_by_excluded_transfer = 0
    run_log_lines: list[str] = []

    def _run_log(msg: str) -> None:
        timestamped = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {msg}"
        run_log_lines.append(timestamped)
        log_debug(msg)

    _run_log(
        f"Run start — threshold={threshold}, MERGE_SELECT_ONLY={MERGE_SELECT_ONLY}, "
        f"parents={ALLOWED_PARENTS if MERGE_SELECT_ONLY else '(ignored)'}, "
        f"excluded_transfer={EXCLUDED_TRANSFER_TAGS or '(none)'}"
    )

    col = browser.mw.col
    selected_nids = browser.selectedNotes()
    _run_log(f"Selected NIDs: {selected_nids}")
    field_name = config.get("comparison_field", MERGE_TAGS_DEFAULTS["comparison_field"])

    # Build map of normalized text -> NIDs
    nid_to_norm = {}
    for nid in selected_nids:
        note = col.get_note(nid)
        flds = col.models.field_names(note.model())
        if field_name in flds:
            raw = note.fields[flds.index(field_name)]
            norm = normalize(raw)
            if norm:
                nid_to_norm[nid] = norm
    _run_log(f"Normalized NID Map: {nid_to_norm}")

    clustered = []
    visited = set()

    # Group NIDs by fuzzy-similar normalized values
    for nid1, norm1 in nid_to_norm.items():
        if nid1 in visited:
            continue
        group = [nid1]
        visited.add(nid1)
        for nid2, norm2 in nid_to_norm.items():
            if nid2 in visited:
                continue
            if SequenceMatcher(None, norm1, norm2).ratio() >= threshold:
                group.append(nid2)
                visited.add(nid2)
        clustered.append(group)
    _run_log(f"Formed {len(clustered)} clusters with threshold {threshold}")

    updated = 0
    for group in clustered:
        if len(group) < 2:
            continue
        all_tags = set()
        notes = [col.get_note(nid) for nid in group]
        # Only collect tags that are allowed to transfer across notes.
        for note in notes:
            for tag in note.tags:
                if tag_is_allowed(tag):
                    all_tags.add(tag)
                else:
                    if _is_tag_excluded_from_transfer(tag):
                        skipped_by_excluded_transfer += 1
                    else:
                        skipped_by_parent_filter += 1
        for note in notes:
            existing_allowed_tags = {tag for tag in note.tags if tag_is_allowed(tag)}
            if existing_allowed_tags != all_tags:
                disallowed_existing = {tag for tag in note.tags if not tag_is_allowed(tag)}
                note.tags = sorted(disallowed_existing.union(all_tags).union({merged_tag}))
                note.flush()
                updated += 1
                _run_log(f"Updated tags for note {note.id} -> Tags: {note.tags}")

    mw.reset()
    _run_log(
        f"Completed tag merge. Updated {updated} notes. "
        f"Skipped tags by parent filter: {skipped_by_parent_filter}. "
        f"Skipped tags by excluded-transfer filter: {skipped_by_excluded_transfer}"
    )
    exported_path = None
    if export_log_to_desktop:
        exported_path = _write_desktop_run_log(run_log_lines)

    info_msg = f"Updated tags on {updated} duplicate notes."
    if MERGE_SELECT_ONLY:
        info_msg += f"\n(Parent filter active; skipped tags: {skipped_by_parent_filter})"
    if EXCLUDED_TRANSFER_TAGS:
        info_msg += f"\n(Excluded-transfer filter active; skipped tags: {skipped_by_excluded_transfer})"
    if export_log_to_desktop:
        if exported_path:
            info_msg += f"\n(Log exported to: {exported_path})"
        else:
            info_msg += "\n(Log export requested, but Desktop log write failed.)"
    if show_summary_popup:
        showInfo(info_msg)
    return {
        "updated": updated,
        "skipped_by_parent_filter": skipped_by_parent_filter,
        "skipped_by_excluded_transfer": skipped_by_excluded_transfer,
        "log_path": str(exported_path) if exported_path else None,
        "summary_text": info_msg,
    }


def unify_tags_main(browser: Browser | None = None):
    _reload_runtime_config()
    if browser is None:
        browser = mw.form.browser

    selected_nids = browser.selectedNotes()
    if not selected_nids:
        showInfo("No notes selected.")
        return

    # ? UI config fetch
    default_fuzzy, min_fuzzy = _global_fuzzy_opts()
    max_fuzzy = 1.0
    ask_each = parse_bool(
        config.get("ask_fuzzy_each_time", MERGE_TAGS_DEFAULTS["ask_fuzzy_each_time"]),
        default=MERGE_TAGS_DEFAULTS["ask_fuzzy_each_time"],
    )

    # Decide threshold (prompt or silent clamp)
    if ask_each:
        default_pct = max(min(int(default_fuzzy * 100), 100), 0)
        t = prompt_fuzzy_threshold(default=default_pct, parent=browser)
        if t is None:
            return  # user canceled
        threshold = max(min(t, max_fuzzy), min_fuzzy)
    else:
        threshold = max(min(default_fuzzy, max_fuzzy), min_fuzzy)

    export_logs_to_desktop = prompt_merge_tags_log_export(parent=browser)
    if export_logs_to_desktop is None:
        return

    unify_tags_on_duplicates(
        browser,
        threshold=threshold,
        export_log_to_desktop=export_logs_to_desktop,
    )
