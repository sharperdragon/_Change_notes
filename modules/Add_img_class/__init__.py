"""
Add_img_class module (callable from _Change_notes)

- Keeps vendor path injection and PIL import on module import
- Keeps UI tooltips/warnings and hard-coded log path
- Exposes `main(browser)` for _Change_notes to call
- No automatic menu/context-menu wiring and no standalone Browser launcher
"""

import os
import re
import sys
import traceback
from urllib.parse import unquote  # needed for decoding media src
from .larger_helper import add_larger_if_listed

# Only config manager is needed in module mode; the config UI is owned by _Change_notes
from .config_manager import ConfigManager

# -----------------------------
# Logging (hard-coded path kept)
# -----------------------------
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_path = os.path.join(LOG_DIR, "Add_img_class_log.txt")


def log(msg: str) -> None:
    """Append a single log line to the module log file."""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")


# We keep vendor path injection but do not import PIL at module top-level
# until after vendor is injected in initialize_addon().
Image = None  # will be assigned in initialize_addon()
pil_info = "Pillow not initialized"


# -----------------------------
# Regexes at module scope
# -----------------------------
# Find <img ... src=... ...>
# Supports:
# - src="..."
# - src='...'
# - src = "..." (space around '=')
# - src=unquoted-value
img_tag_re = re.compile(
    r"<img\b[^>]*\bsrc\s*=\s*(?:\"(?P<src_dq>[^\"]*)\"|'(?P<src_sq>[^']*)'|(?P<src_unquoted>[^\s\"'>]+))[^>]*>",
    re.IGNORECASE,
)
class_attr_re = re.compile(r"(?i)\bclass\s*=\s*([\"'])(.*?)\1", re.DOTALL)
verification_class_re = re.compile(
    r"(?i)class\s*=\s*([\"'])[^\"']*(?:ultra-wide|img-landscape|img-tall|img-square|img-default|small|larger)[^\"']*\1"
)

MANAGED_IMG_CLASS_TAGS = {"ultra-wide", "img-landscape", "img-tall", "img-square", "img-default", "small"}


# -----------------------------
# Core helpers
# -----------------------------

def classify_image(image_path: str) -> str:
    """Return one or more CSS classes for the given image based on aspect ratio.
    Keeps logging and thresholds from config. No UI here; UI is handled by caller.
    """
    global Image
    try:
        if Image is None:
            # If PIL is still missing at runtime, just return empty (caller handles UI).
            log("PIL Image is None in classify_image(); returning empty class")
            return ""

        config = ConfigManager("add_img_class").load_config()
        with Image.open(image_path) as img:
            log(f"  successfully opened image: {image_path}")
            w, h = img.size
            ratio = w / h if h else 0
            classes = []
            log(
                "  img size: %sx%s, ratio=%.3f" % (w, h, ratio)
            )
            log(
                "  thresholds: wide=%s, landscape_min=%s, tall=%s, square=(%s-%s)"
                % (
                    config.get("ultra-wide_ratio"),
                    config.get("landscape_ratio_min"),
                    config.get("tall_ratio"),
                    config.get("square_min"),
                    config.get("square_max"),
                )
            )

            if w < config.get("small_width", 340):
                classes.append("small")
            if ratio > config.get("ultra-wide_ratio", 1.89999999999):
                classes.append("ultra-wide")
            elif ratio > config.get("landscape_ratio_min", 1.2400000001):
                classes.append("img-landscape")
            elif ratio < config.get("tall_ratio", 0.899999):
                classes.append("img-tall")
            elif config.get("square_min", 0.8999991) < ratio < config.get("square_max", 1.12):
                classes.append("img-square")

            if not classes:
                log("  → no class matched")
            return " ".join(classes)
    except Exception as e:
        log(f"  ❌ failed to classify image: {image_path} — {e}")
        return ""


# -----------------------------
# Public entry point (callable)
# -----------------------------

def main(browser) -> bool:
    """Process selected notes in the given Browser and insert image classes.
    UI tooltips/warnings are preserved here per request.
    Returns True if any notes were updated.
    """
    # Local imports to avoid issues during add-on load
    from aqt import mw
    from aqt.utils import tooltip, showWarning, showText

    # reset log each run
    open(log_path, "w", encoding="utf-8").close()
    log("main() triggered")
    log(f"Using IMG regex: {img_tag_re.pattern}")

    updated_notes_counter = 0
    updated_any = False

    try:
        if Image is None:
            log("Pillow (PIL) not available; aborting run.")
            tooltip(
                "Add_img_class: Pillow not found. Bundle PIL in vendor/ and try again.",
                period=4000,
            )
            showWarning(
                "Add_img_class: Pillow (PIL) is missing. Please ensure it is bundled in the 'vendor' folder inside your add-on (vendor/PIL)."
            )
            return False

        media_folder = mw.col.media.dir()

        note_ids = browser.selectedNotes()
        if not note_ids:
            log("No notes selected; exiting.")
            # give focus back to search field for convenience
            browser.form.searchEdit.setFocus()
            browser.form.searchEdit.selectAll()
            tooltip("Add_img_class: No notes selected. Run a search and select notes first.", period=3000)
            return False

        rows = [(nid, mw.col.get_note(nid)) for nid in note_ids]

        for nid, note in rows:
            log(f"Note {nid} → {sum(len(list(img_tag_re.finditer(f))) for f in note.fields)} <img> tags found")
            updated = False
            fields_list = note.fields
            new_fields_list = fields_list.copy()

            for i, field in enumerate(fields_list):
                def replace_img_tag(match):
                    nonlocal updated  # allow this closure to flag note-level updates
                    src = (
                        match.group("src_dq")
                        or match.group("src_sq")
                        or match.group("src_unquoted")
                    )
                    log(f"Image src: {src}")
                    decoded_src = unquote(src or "").strip()
                    local_src = decoded_src.split("?", 1)[0].split("#", 1)[0].lstrip("/\\")
                    img_path = os.path.join(media_folder, local_src)
                    if not os.path.exists(img_path):
                        log(f"  ⚠️ image not found in media folder: {img_path}")
                        log("  🌐 external image detected; using fallback class 'img-default'")
                        cls = "img-default"
                    else:
                        cls = classify_image(img_path)
                    log(f"  → class: {cls if cls else '(none)'}")
                    if not cls:
                        return match.group(0)

                    old_tag = match.group(0)
                    existing_class_match = class_attr_re.search(old_tag)
                    if existing_class_match:
                        class_quote = existing_class_match.group(1)
                        existing_classes = existing_class_match.group(2).split()
                        cleaned_classes = [c for c in existing_classes if c not in MANAGED_IMG_CLASS_TAGS]
                        new_classes = sorted(set(cleaned_classes + cls.split()))
                        new_class_attr = f"class={class_quote}{' '.join(new_classes)}{class_quote}"
                        start, end = existing_class_match.span()
                        new_tag = old_tag[:start] + new_class_attr + old_tag[end:]
                    else:
                        new_class_attr = 'class="' + cls + '"'
                        new_tag = re.sub(r"\s*(/?)>\s*$", lambda m: (" " + new_class_attr + (" /" if m.group(1) else "") + ">"), old_tag)

                    new_tag = add_larger_if_listed(new_tag)

                    original_attrs = re.search(r"<img\s+(.*?)>", old_tag)
                    new_attrs = re.search(r"<img\s+(.*?)>", new_tag)
                    if original_attrs and new_attrs:
                        log(f"Comparing: '{original_attrs.group(1)}' vs '{new_attrs.group(1)}'")
                        if original_attrs.group(1) != new_attrs.group(1):
                            updated = True  # mark note as changed when tag attributes differ
                            return new_tag
                    # Fallback: any textual change counts as an update
                    if new_tag != old_tag:
                        updated = True
                        return new_tag
                    return old_tag

                new_field = img_tag_re.sub(replace_img_tag, field)
                # Log the updated field after calculation and before setting it
                log(f"Updated field {i}: {new_field[:200].replace(os.linesep, ' ')}")
                new_fields_list[i] = new_field
                # Log the original field after setting the new field
                log(f"Original field {i}: {fields_list[i][:200].replace(os.linesep, ' ')}")

            if updated:
                log(f"✏️ Saving note {nid}")
                note.fields = new_fields_list
                try:
                    mw.col.update_note(note)
                except Exception as e:
                    log(f"update_note failed; falling back to note.flush(): {e}")
                    note.flush()
                # Post-save verification
                verified_note = mw.col.get_note(nid)
                verification_hit = any(
                    verification_class_re.search(f or "")
                    for f in verified_note.fields
                )
                if verification_hit:
                    log(f"✅ Verified class present after save for note {nid}")
                else:
                    log(f"⚠️ Verification failed: class not found after save for note {nid}")
                updated_any = True
                updated_notes_counter += 1
            else:
                log(f"No changes for note {nid}")

        if updated_any:
            try:
                mw.reset()  # refresh Browser/editor so class changes are immediately visible
            except Exception as e:
                log(f"mw.reset() failed (non-fatal): {e}")
            log(f"✅ Tags updated in {updated_notes_counter} notes")
            tooltip(f"Add_img_class: {updated_notes_counter} note(s) updated.", period=3000)
        else:
            log("ℹ️ No updates made to any notes.")
            tooltip("Add_img_class: 0 notes updated.", period=3000)

    except Exception:
        # Import here to avoid top-level import issues
        from aqt.utils import showText
        showText(f"Unexpected error:\n{traceback.format_exc()}", title="Add_img_class Critical Error", plain_text=True)
    return updated_any


# -----------------------------
# One-time initializer (keeps vendor path edits and logs PIL info)
# -----------------------------

def initialize_addon() -> None:
    """Inject vendor path and import PIL safely; log its info."""
    global Image, pil_info

    # Inject vendor path for bundled Pillow (keep per request)
    vendor_path = os.path.join(os.path.dirname(__file__), "vendor")
    if vendor_path not in sys.path:
        sys.path.insert(0, vendor_path)

    try:
        from PIL import Image as _Image
        try:
            import PIL
            pil_info = f"Pillow version: {getattr(PIL, '__version__', 'unknown')}, path: {getattr(PIL, '__file__', 'unknown')}"
        except Exception:
            pil_info = "Pillow present but could not introspect version/path"
        Image = _Image
    except ImportError:
        Image = None
        pil_info = "Pillow not found"

    # Log PIL info each import
    # (Ensure the log file exists and is fresh on first import)
    try:
        open(log_path, "a", encoding="utf-8").close()
    except Exception:
        pass
    log(pil_info)


# Run initializer on import so PIL and vendor wiring are ready
initialize_addon()
