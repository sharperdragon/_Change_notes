# Standard Library
import html
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
# Third-Party
from bs4 import BeautifulSoup

# Anki / aqt
from aqt import mw

# === Constants & Global Config ===
TEXT_REPLACEMENT_PATH = Path(__file__).parent / "text_replacements.txt"

SYNONYMS = {
    "antinuclear antibodies": ["ana"],
    "ana": ["antinuclear antibodies"],
    "rheumatoid factor": ["rf"],
    "rf": ["rheumatoid factor"],
    "anti-scl-70": ["scl70"],
    "scl70": ["anti-scl-70"],
}

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

    # Expand synonyms
    expanded_tokens = set()
    for tok in tokens:
        expanded_tokens.add(tok)
        for syn in SYNONYMS.get(tok, []):
            expanded_tokens.add(syn)

    # Return normalized, sorted string
    return " ".join(sorted(expanded_tokens))

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

def group_similar_notes_by_content(note_infos, threshold, field_name="Text"):
    note_lookup = defaultdict(list)
    for note in note_infos:
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

def group_note_ids_by_similarity(note_infos, threshold, field_name="Text", has_excluded_tag=lambda note: False):
    filtered_notes = [note for note in note_infos if not has_excluded_tag(note)]
    grouped = group_notes_by_similarity(filtered_notes, threshold, field_name)
    return {k: [n.id for n in v] for k, v in grouped.items()}

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