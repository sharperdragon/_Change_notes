import json
import os
import re
import traceback
from pathlib import Path

from aqt import mw
from aqt.utils import showText, tooltip

from ...config_manager import ConfigManager
from ..shared.defaults import ADD_TABLE_CLASS_DEFAULTS, clone_defaults

CONFIG_SECTION = "add_table_class"
LEGACY_CONFIG_SECTION = "Add_table_class"

_RUNTIME_CONFIG = clone_defaults(ADD_TABLE_CLASS_DEFAULTS)
_LOG_PATH = os.path.expanduser(ADD_TABLE_CLASS_DEFAULTS["log_path"])
_APPLY_TO_EXISTING = bool(ADD_TABLE_CLASS_DEFAULTS["apply_to_existing_classes"])


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


def _load_local_legacy_config() -> dict:
    config_path = Path(__file__).with_name("config.json")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _reload_runtime_config():
    global _RUNTIME_CONFIG
    global _LOG_PATH
    global _APPLY_TO_EXISTING

    cfg = clone_defaults(ADD_TABLE_CLASS_DEFAULTS)
    cfg = ConfigManager.deep_merge_dicts(cfg, _load_local_legacy_config())
    cfg = ConfigManager.deep_merge_dicts(cfg, ConfigManager(CONFIG_SECTION).load())

    legacy_cfg = ConfigManager.get_effective_section(LEGACY_CONFIG_SECTION)
    if legacy_cfg:
        cfg = ConfigManager.deep_merge_dicts(cfg, legacy_cfg)

    _RUNTIME_CONFIG = cfg
    _LOG_PATH = os.path.expanduser(str(cfg.get("log_path", ADD_TABLE_CLASS_DEFAULTS["log_path"])))
    _APPLY_TO_EXISTING = _parse_bool(
        cfg.get("apply_to_existing_classes", ADD_TABLE_CLASS_DEFAULTS["apply_to_existing_classes"]),
        default=True,
    )


_reload_runtime_config()


def log(msg: str) -> None:
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except Exception:
        # Logging failures are non-fatal
        pass


# ----------------------------
# Regexes & constants (module)
# ----------------------------
# Find <table>...</table> blocks (DOTALL to span newlines)
table_block_re = re.compile(r'<table\b[^>]*>.*?</table>', re.IGNORECASE | re.DOTALL)
# Find the first <tr>...</tr> within a table block
first_tr_re = re.compile(r'<tr\b[^>]*>.*?</tr>', re.IGNORECASE | re.DOTALL)
# Enumerate cell tags in a row; we will parse colspan from each
cell_tag_re = re.compile(r'<(?:td|th)\b[^>]*?>', re.IGNORECASE)
# Class attribute pattern
cls_attr_re = re.compile(r'class=("|\')(.*?)\1', re.IGNORECASE)

# Table classes we manage (kept small but future-proof)
TABLE_CLASS_TAGS = {"two-cols", "three-cols", "four-cols"}
TARGET_CLASS = "two-cols"
EXCLUDE_CLASS = "no-auto-class"


# ----------------------------
# Public API: module-level entry points
# ----------------------------

def add_class_main(browser):
    """
    Run on currently selected notes in Browser.
    - Adds TARGET_CLASS (default: 'two-cols') to <table> opening tag if table has exactly 2 columns.
    - Skips tables that contain EXCLUDE_CLASS ('no-auto-class').
    - Respects _APPLY_TO_EXISTING: if False and a class attribute exists (but not EXCLUDE_CLASS), we still merge TARGET_CLASS
      after removing any existing managed classes; if True (default), we always merge.
    """
    try:
        _reload_runtime_config()

        # fresh log for each run
        try:
            open(_LOG_PATH, "w", encoding="utf-8").close()
        except Exception:
            pass
        log("add_class_main() triggered")
        log(
            f"Runtime config: apply_to_existing_classes={_APPLY_TO_EXISTING}, "
            f"log_path={_LOG_PATH}"
        )

        note_ids = browser.selectedNotes()
        log(f"{len(note_ids)} notes selected")
        if not note_ids:
            browser.form.searchEdit.setFocus()
            browser.form.searchEdit.selectAll()
            return False

        rows = [(nid, mw.col.get_note(nid)) for nid in note_ids]
        updated_any = False
        tables_seen = 0
        tables_updated = 0
        tables_skipped_exclusion = 0
        tables_skipped_existing = 0
        tables_skipped_non_two_col = 0

        # --- helpers ---
        def _count_columns_in_table(table_html: str) -> int:
            """Count columns in the first row of the table, colspan-aware. Falls back to 0 if no row found."""
            first_tr_match = first_tr_re.search(table_html)
            if not first_tr_match:
                return 0
            row_html = first_tr_match.group(0)
            cols = 0
            for cell in cell_tag_re.findall(row_html):
                # Extract colspan if present; default to 1
                cs = 1
                m = re.search(r'\bcolspan\s*=\s*"?(\d+)"?', cell, re.IGNORECASE)
                if m:
                    try:
                        cs = max(1, int(m.group(1)))
                    except Exception:
                        cs = 1
                cols += cs
            return cols

        for nid, note in rows:
            updated = False
            fields_list = note.fields
            new_fields_list = fields_list.copy()

            def replace_table_block(tb_match: re.Match) -> str:
                """
                Inject a class into the <table> opening tag based on detected column count.
                Currently: add TARGET_CLASS if exactly 2 columns. Safe-merge with existing classes.
                """
                nonlocal updated  # ensure any change flags the enclosing note as updated
                nonlocal tables_seen
                nonlocal tables_updated
                nonlocal tables_skipped_exclusion
                nonlocal tables_skipped_existing
                nonlocal tables_skipped_non_two_col

                tb_html = tb_match.group(0)
                tables_seen += 1
                # Locate opening <table ...>
                open_tag_match = re.search(r'<table\b[^>]*>', tb_html, re.IGNORECASE)
                if not open_tag_match:
                    return tb_html
                open_tag = open_tag_match.group(0)

                # Parse existing classes (if any)
                existing_classes: list[str] = []
                m = cls_attr_re.search(open_tag)
                if m:
                    existing_classes = m.group(2).split()
                    # Honor explicit exclusion tag
                    if EXCLUDE_CLASS in existing_classes:
                        tables_skipped_exclusion += 1
                        try:
                            log(f"Skip table: has exclusion class '{EXCLUDE_CLASS}' → classes={existing_classes}")
                        except Exception:
                            pass
                        return tb_html
                    if not _APPLY_TO_EXISTING:
                        tables_skipped_existing += 1
                        log(
                            "Skip table: class exists and apply_to_existing_classes=False "
                            f"→ classes={existing_classes}"
                        )
                        return tb_html

                # Determine column count from first <tr>
                col_count = _count_columns_in_table(tb_html)
                if col_count != 2:
                    tables_skipped_non_two_col += 1
                    try:
                        log(f"Skip table: detected {col_count} column(s) (only 2-col gets class).")
                    except Exception:
                        pass
                    return tb_html

                new_cls = TARGET_CLASS

                # Merge TARGET_CLASS with existing classes, removing any managed classes first
                cleaned = [c for c in existing_classes if c not in TABLE_CLASS_TAGS]
                merged = ' '.join(sorted(set(cleaned + [new_cls])))

                if m:
                    new_open_tag = cls_attr_re.sub(f'class="{merged}"', open_tag, count=1)
                else:
                    new_open_tag = re.sub(r'>\s*$', f' class="{new_cls}">', open_tag, count=1)

                # Only mark updated if attributes actually changed
                if open_tag != new_open_tag:
                    updated = True
                    tables_updated += 1
                    # Log comparison for debugging
                    log(f"Table cols={col_count} → class='{new_cls}'")
                    log(f"Comparing table open tag: '{open_tag}' vs '{new_open_tag}'")
                    # Replace only the first occurrence of the opening tag inside the block
                    return tb_html.replace(open_tag, new_open_tag, 1)
                return tb_html

            # Process each field
            for i, field in enumerate(fields_list):
                new_field = field
                if "<table" in new_field:
                    new_field = table_block_re.sub(replace_table_block, new_field)
                new_fields_list[i] = new_field

            if updated:
                log(f"✏️ Saving note {nid}")
                note.fields = new_fields_list
                try:
                    mw.col.update_note(note)  # ensure changes are persisted in Anki 25.x
                except Exception as e:
                    log(f"update_note failed → falling back to note.flush(): {e}")
                    try:
                        note.flush()
                    except Exception as e2:
                        log(f"note.flush() also failed: {e2}")
                        raise
                updated_any = True

        # Refresh UI so Browser/editor reflect saved changes
        try:
            mw.reset()
        except Exception as e:
            log(f"mw.reset() failed (non-fatal): {e}")

        # Simple count of notes containing <table> blocks (UX only)
        notes_with_tables = sum(1 for nid, note in rows if any(table_block_re.search(f) for f in note.fields))

        if updated_any:
            log(f"✅ Updates made. Notes with <table>: {notes_with_tables}")
        else:
            log("ℹ️ No updates made to any notes.")

        summary = (
            f"Table class run complete. Notes with tables={notes_with_tables}, "
            f"tables seen={tables_seen}, updated={tables_updated}, "
            f"skipped exclusion={tables_skipped_exclusion}, "
            f"skipped existing={tables_skipped_existing}, "
            f"skipped non-two-col={tables_skipped_non_two_col}."
        )
        log(summary)
        tooltip(summary, period=4500)
        return updated_any

    except Exception:
        showText(
            f"Unexpected error:\n{traceback.format_exc()}",
            title="Add_table_class Critical Error",
            plain_text=True,
        )
        return False


def initialize_addon():
    """Optional one-time setup. Kept for compatibility; no-op by default."""
    return

# No auto-run needed; _Change_notes/__init__.py calls add_class_main(browser)
