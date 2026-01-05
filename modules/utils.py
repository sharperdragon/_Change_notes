from aqt import mw
import json
import os
import re, sys

import html, re, unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path

from bs4 import BeautifulSoup
# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt.qt import  QInputDialog
from aqt import mw
from aqt.qt import QDialog, QVBoxLayout, QDialogButtonBox, QDoubleSpinBox


 # ConfigManager is located one level up (_Change_notes/config_manager.py)
try:
    from ..config_manager import ConfigManager  # type: ignore
except Exception:
    ConfigManager = None  # Fallback to plain JSON loader below

# --- Centralized config loading helpers ---
_ADDON_ROOT = Path(__file__).resolve().parents[1]
_CONFIG_PATH = _ADDON_ROOT / "config.json"

def _load_config_raw():
    """
    Return the whole config dict using ConfigManager if available,
    otherwise fall back to reading config.json directly.
    """
    # Prefer ConfigManager if present
    try:
        if ConfigManager is not None:
            data = ConfigManager.load()  # expected to return a dict
            if isinstance(data, dict):
                return data
    except Exception:
        pass

    # Plain JSON fallback
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def get_config_section(section_name: str, default=None):
    """
    Fetch a named section from the config (e.g., 'merge_images_config').
    Returns `default` (or {}) if missing.
    """
    data = _load_config_raw() or {}
    if default is None:
        default = {}
    return data.get(section_name, default)

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_config(config):
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


# === Anki Field Index Utilities ===
def get_field_index_from_config(note_type_name, field_name):
    """Return the index of a field for a given note type."""
    for model in mw.col.models.all():
        if model["name"] == note_type_name:
            for i, fld in enumerate(model["flds"]):
                if fld["name"] == field_name:
                    return i
    raise ValueError(f"Field '{field_name}' not found in note type '{note_type_name}'")



def prompt_fuzzy_threshold(default=None):
    """Prompt user for fuzzy threshold (0–100) using a popup input dialog."""
    if default is None:
        # Use merge_images_config.default_threshold as a sensible default source
        mi_cfg = get_config_section("merge_images_config", {})
        default_threshold = float(mi_cfg.get("default_threshold", 0.98))
        default = int(default_threshold * 100)
    val, ok = QInputDialog.getInt(
        mw, "Set Fuzzy Match Threshold",
        "Select fuzzy match threshold (0 = loose, 100 = strict):",
        default, 85, 100, 1
    )
    if ok:
        return val / 100  # Normalize to 0.0–1.0 range
    return None



# === Constants & Global Config ===
TEXT_REPLACEMENT_PATH = Path(__file__).parent / "assets" / "text_replacements.txt"

SYNONYMS = {
    "antinuclear antibodies": ["ana"],
    "ana": ["antinuclear antibodies"],
    "rheumatoid factor": ["rf"],
    "rf": ["rheumatoid factor"],
    "anti-scl-70": ["scl70"],
    "scl70": ["anti-scl-70"],
}

PREFIX_COMBOS = {
    "hyper": [
        "glycemia", "kalemia", "natremia", "calcemia", "reflexia",
        "tonia", "lipidemia", "uricemia", "parathyroidism"
    ],
    "hypo": [
        "glycemia", "kalemia", "natremia", "calcemia", "reflexia",
        "tonia", "albuminemia", "parathyroidism", "magnesemia"
    ],
    "anti": [
        "histamine", "inflammatory", "bacterial", "coagulant"
    ]
}

SUFFIX_COMBOS = {
    "emia": [
        "hyperglyc", "hypoglyc", "hyperuric", "hypouric"
    ],
    "itis": [
        "neur", "hepat", "appendic", "tonsill", "dermat"
    ]
}

def build_morpheme_combos_from_rules():
    combos = {}

    for prefix, roots in PREFIX_COMBOS.items():
        for root in roots:
            combos[(prefix, root)] = prefix + root

    for suffix, stems in SUFFIX_COMBOS.items():
        for stem in stems:
            combos[(stem, suffix)] = stem + suffix

    return combos

MORPHEME_COMBOS = build_morpheme_combos_from_rules()

_REPLACEMENTS = {}

# === HTML Extraction Utilities ===
def extract_images(text):
    return re.findall(r'<img [^>]*src="[^"]+"[^>]*>', text, re.IGNORECASE)

def extract_srcs(image_tags):
    return {re.search(r'src="([^"]+)"', img).group(1) for img in image_tags if 'src="' in img}

def clean_img_tag(img_tag):
    src_match = re.search(r'src="([^"]+)"', img_tag, re.IGNORECASE)
    class_match = re.search(r'class="([^"]+)"', img_tag, re.IGNORECASE)
    if not src_match:
        return ""
    src = src_match.group(1)
    class_attr = class_match.group(1) if class_match else None
    return f'<img src="{src}" class="{class_attr}">' if class_attr else f'<img src="{src}">'


# === Text Normalization ===
def strip_html(s):
    return re.sub(r'<[^>]+>', '', s)

# Helper for cloze normalization
def normalize_cloze_content(cloze_content):
    """Normalize cloze content: normalize Ig list format, shuffle words if parenthesis exists."""
    cloze_content = cloze_content.strip()
    cloze_content = cloze_content.replace("<br>", ", ").replace("<br/>", ", ")

    # Handle common conjunctions and clean comma spacing
    cloze_content = cloze_content.replace(" and ", ", ")
    cloze_content = re.sub(r"\s*,\s*", ", ", cloze_content)

    # If parenthesis exists, shuffle inside and outside words
    if "(" in cloze_content and ")" in cloze_content:
        try:
            outer = re.sub(r"\([^)]*\)", "", cloze_content)
            inner = re.search(r"\(([^)]*)\)", cloze_content).group(1)
            tokens = outer.split() + inner.split()
            tokens = sorted(t.strip().lower() for t in tokens if t.strip())
            return " ".join(tokens)
        except Exception:
            pass  # fallback if malformed

    # Normalize comma-separated lists like immunoglobulins
    if "," in cloze_content:
        tokens = [t.strip().lower() for t in cloze_content.split(",")]
    else:
        tokens = [t.strip().lower() for t in cloze_content.split()]

    tokens = combine_morphemes(tokens)

    # Expand synonyms
    expanded_tokens = set()
    for tok in tokens:
        expanded_tokens.add(tok)
        for syn in SYNONYMS.get(tok, []):
            expanded_tokens.add(syn)

    # Return normalized, sorted string
    return " ".join(sorted(expanded_tokens))

def combine_morphemes(tokens):
    """
    Merge known morpheme pairs into a unified medical term.
    Example: ['hemat', 'uria'] -> ['hematuria']
    """
    combined = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens) and (tokens[i], tokens[i + 1]) in MORPHEME_COMBOS:
            combined.append(MORPHEME_COMBOS[(tokens[i], tokens[i + 1])])
            i += 2
        else:
            combined.append(tokens[i])
            i += 1
    return combined

def normalize(text):
    # Step 1: Strip HTML using BeautifulSoup
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text(separator=" ")  # Normalize nested/div-separated segments
    text = html.unescape(text)

    # Step 2: Replace common HTML entities
    text = text.replace("&", "and")
    text = text.replace("&amp;", "and")
    text = text.replace("\xa0", " ")

    # Step 3: Normalize unicode to ascii
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')

    # Normalize e.g. and other parenthetical segments
    text = re.sub(r'\(\s*e\.?g\.?,?\s*', '(e.g. ', text)
    text = re.sub(r'\s*\)', ')', text)

    # Step 4: Collect and normalize all clozes by group (e.g., c1)
    cloze_matches = re.findall(r'\{\{c(\d+)::(.*?)(?:::.*?)?\}\}', text)
    cloze_dict = defaultdict(list)

    for group, content in cloze_matches:
        cloze_dict[group].append(content)

    # Remove all original clozes
    text = re.sub(r'\{\{c\d+::.*?(?:::.*?)?\}\}', '', text)

    # Append normalized clozes
    for group, contents in cloze_dict.items():
        combined = ", ".join(contents)
        normalized = normalize_cloze_content(combined)
        text += f" {{c{group}::{normalized}}}"

    # Step 5: Remove punctuation, arrows
    text = re.sub(r'[.,:;!?]', '', text)
    text = re.sub(r'\s*,\s*', ', ', text)
    text = re.sub(r'\s*/\s*', ' or ', text)
    text = text.replace("↑", "increased").replace("↓", "decreased").replace("↔", "normal")

    # Step 6: Apply custom replacements
    for abbr, full in _REPLACEMENTS.items():
        text = re.sub(rf'\b{abbr}\b', full, text)

    # Step 7: Final whitespace and lowercase normalization
    return re.sub(r'\s+', ' ', text).strip().lower()


# === Similarity & Grouping ===
def is_similar(a, b, threshold):
    return SequenceMatcher(None, a, b).ratio() >= threshold

def group_notes_by_similarity(note_infos, threshold, field_name="Text", has_excluded_tag=lambda note: False):
    note_lookup = defaultdict(list)
    for note in note_infos:
        if has_excluded_tag(note):
            continue
        field_names = [fld["name"] for fld in mw.col.models.get(note.mid)["flds"]]
        if field_name not in field_names:
            continue
        field_index = field_names.index(field_name)
        norm = normalize(note.fields[field_index])
        if norm in note_lookup:
            note_lookup[norm].append(note)
        else:
            matched_key = next((k for k in note_lookup if is_similar(norm, k, threshold)), None)
            if matched_key:
                note_lookup[matched_key].append(note)
            else:
                note_lookup[norm].append(note)
    return note_lookup

# === File/Replacement Handling ===
def load_replacements(path=TEXT_REPLACEMENT_PATH):
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        return {
            line.split("=>")[0].strip(): line.split("=>")[1].strip()
            for line in lines if "=>" in line
        }
    except FileNotFoundError:
        print(f"⚠️ Replacement file not found at {path}, skipping replacements.")
        return {}
    except Exception as e:
        print(f"Failed to load replacements: {e}")
        return {}

_REPLACEMENTS = load_replacements()





def prompt_similarity_threshold(
    *,
    default: float = 0.90,
    minimum: float = 0.80,
    maximum: float = 1.00,
    ui: str = "float",
    step: float = 0.01,
    decimals: int = 2,
    title: str = "Fuzzy Threshold",
    percent_suffix: str = "%"
) -> tuple[float | None, bool]:
    dlg = QDialog(mw)
    dlg.setWindowTitle(title)
    lay = QVBoxLayout(dlg)

    spin = QDoubleSpinBox()

    if ui == "percent":
        # If caller passed floats (0.85..1.00), convert to percents.
        use_min, use_max, use_def = minimum, maximum, default
        if maximum <= 1.0:
            use_min, use_max, use_def = minimum * 100, maximum * 100, default * 100

        # ? Percent UX defaults: whole % steps, no decimals
        spin.setDecimals(0 if decimals is None else decimals)
        if decimals is None:
            spin.setDecimals(0)
        spin.setRange(use_min, use_max)
        spin.setSingleStep(max(1.0, step * 100))
        spin.setValue(use_def)
        spin.setSuffix(percent_suffix)
    else:
        spin.setDecimals(decimals)
        spin.setRange(minimum, maximum)
        spin.setSingleStep(step)
        spin.setValue(default)

    lay.addWidget(spin)

    btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    btns.accepted.connect(dlg.accept)
    btns.rejected.connect(dlg.reject)
    lay.addWidget(btns)

    if dlg.exec() != QDialog.DialogCode.Accepted:
        return None, False

    val = spin.value()
    if ui == "percent":
        val /= 100.0
        # Clamp to the caller’s FLOAT domain after conversion
        lo = minimum if maximum <= 1.0 else minimum
        hi = maximum if maximum <= 1.0 else maximum
        # If caller passed percent bounds (85..100), convert them for clamp:
        if maximum > 1.0:
            lo, hi = minimum / 100.0, maximum / 100.0
        val = max(min(val, hi), lo)
    else:
        # Clamp to float domain
        val = max(min(val, maximum), minimum)

    return val, True