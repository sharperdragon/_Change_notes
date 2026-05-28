from ..config_manager import ConfigManager
from .merge_imgs import run_merge_images
from .merge_tags import unify_tags_on_duplicates
from .shared.defaults import IMG_TAGS_MERGE_DEFAULTS, clone_defaults
from .utils import prompt_similarity_threshold

# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt import mw
from aqt.qt import QMessageBox


from aqt.browser import Browser as AqtBrowser

# User-tunable settings intentionally kept in-file (not config.json).
MERGE_IMAGES_AND_TAGS_DEFAULT_FUZZY = 0.99
MERGE_IMAGES_AND_TAGS_MIN_FUZZY = 0.78
MERGE_IMAGES_AND_TAGS_BASE_TAG = "Tag+IMG_MERGED"
MERGE_IMAGES_AND_TAGS_LOG_FOLDER = ""

CONFIG = {}


def _reload_runtime_config():
    global CONFIG

    global_cfg = ConfigManager("global_config").load()
    legacy_root_cfg = ConfigManager("_Change_notes").load()

    merged_cfg = clone_defaults(IMG_TAGS_MERGE_DEFAULTS)
    merged_cfg["merge_images_and_tags_config"] = {
        "default_fuzzy": MERGE_IMAGES_AND_TAGS_DEFAULT_FUZZY,
        "min_fuzzy": MERGE_IMAGES_AND_TAGS_MIN_FUZZY,
        "base_tag": MERGE_IMAGES_AND_TAGS_BASE_TAG,
        "log_folder": MERGE_IMAGES_AND_TAGS_LOG_FOLDER,
    }

    fuzzy_opts_new = global_cfg.get("fuzzy_opts") if isinstance(global_cfg, dict) else None
    fuzzy_opts_old = legacy_root_cfg.get("global_fuzzy_opts")

    if isinstance(fuzzy_opts_new, dict) and fuzzy_opts_new:
        merged_cfg["fuzzy_opts"] = fuzzy_opts_new
    elif isinstance(fuzzy_opts_old, dict) and fuzzy_opts_old:
        # Backward-compat fallback for unmigrated configs.
        merged_cfg["fuzzy_opts"] = fuzzy_opts_old

    CONFIG = merged_cfg


_reload_runtime_config()

def cfg(path: str, default=None):
    node = CONFIG
    for key in path.split("."):
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return default
    return node

def _f(path: str, default):
    val = cfg(path, default)
    try:
        return float(val)
    except Exception:
        return float(default)



def merge_imgs_and_tags(selected=None, browser=None, *, threshold: float | None = None, tag_threshold: float | None = None):
    _reload_runtime_config()

    if isinstance(selected, AqtBrowser) and browser is None:
        browser, selected = selected, None

    if browser is None:
        QMessageBox.information(mw, "Unify Images + Tags", "Open the Browser first, or run this from the Browser context.")
        return
    # --- Resolve selected note IDs (be flexible) ---
    if selected is None:
        try:
            note_ids = browser.selectedNotes()
        except Exception:
            QMessageBox.information(mw, "Unify Images + Tags", "Could not read the current selection from the Browser.")
            return
    else:
        if isinstance(selected, int):
            note_ids = [selected]
        elif isinstance(selected, (list, tuple, set)):
            note_ids = list(selected)
        else:
            try:
                note_ids = list(selected)
            except Exception:
                note_ids = browser.selectedNotes()

    if not note_ids:
        QMessageBox.information(mw, "Unify Images + Tags", "No notes selected.")
        return
    # --- Decide thresholds (prompt once if needed) ---
    if threshold is None and tag_threshold is None:
        # Pull unified fuzzy settings from global_config.fuzzy_opts.
        default_threshold = _f("fuzzy_opts.default_fuzz", MERGE_IMAGES_AND_TAGS_DEFAULT_FUZZY)
        min_threshold     = _f("fuzzy_opts.min_fuzz", MERGE_IMAGES_AND_TAGS_MIN_FUZZY)
        max_threshold     = 1.0

        t, ok = prompt_similarity_threshold(
            default=default_threshold,
            minimum=min_threshold,
            maximum=max_threshold,
            ui="float",
            title="Fuzzy Threshold (Global)",
            parent=browser,
        )
        if not ok:
            return
        threshold = max(min(t, max_threshold), min_threshold)
        tag_threshold = threshold
    else:
        # backfill if only one provided
        if threshold is None:
            threshold = tag_threshold
        if tag_threshold is None:
            tag_threshold = threshold
    run_merge_images(note_ids, browser, threshold=threshold)
    unify_tags_on_duplicates(browser, threshold=tag_threshold)
