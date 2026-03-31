from __future__ import annotations

import html
import re
import unicodedata
from collections import defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Callable

from bs4 import BeautifulSoup

# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt import mw


TEXT_REPLACEMENT_PATH = Path(__file__).resolve().parents[1] / "assets" / "text_replacements.txt"

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
        "glycemia",
        "kalemia",
        "natremia",
        "calcemia",
        "reflexia",
        "tonia",
        "lipidemia",
        "uricemia",
        "parathyroidism",
    ],
    "hypo": [
        "glycemia",
        "kalemia",
        "natremia",
        "calcemia",
        "reflexia",
        "tonia",
        "albuminemia",
        "parathyroidism",
        "magnesemia",
    ],
    "anti": ["histamine", "inflammatory", "bacterial", "coagulant"],
}

SUFFIX_COMBOS = {
    "emia": ["hyperglyc", "hypoglyc", "hyperuric", "hypouric"],
    "itis": ["neur", "hepat", "appendic", "tonsill", "dermat"],
}


def build_morpheme_combos_from_rules() -> dict[tuple[str, str], str]:
    combos: dict[tuple[str, str], str] = {}
    for prefix, roots in PREFIX_COMBOS.items():
        for root in roots:
            combos[(prefix, root)] = prefix + root
    for suffix, stems in SUFFIX_COMBOS.items():
        for stem in stems:
            combos[(stem, suffix)] = stem + suffix
    return combos


MORPHEME_COMBOS = build_morpheme_combos_from_rules()


def load_replacements(path: Path = TEXT_REPLACEMENT_PATH) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return {
            line.split("=>")[0].strip(): line.split("=>")[1].strip()
            for line in lines
            if "=>" in line
        }
    except FileNotFoundError:
        print(f"[text_similarity] Replacement file not found at {path}, skipping replacements.")
        return {}
    except Exception as exc:
        print(f"[text_similarity] Failed to load replacements: {exc}")
        return {}


_REPLACEMENTS = load_replacements()


def extract_images(text: str) -> list[str]:
    return re.findall(r'<img [^>]*src="[^"]+"[^>]*>', text or "", re.IGNORECASE)


def extract_srcs(image_tags: list[str] | set[str]) -> set[str]:
    return {
        re.search(r'src="([^"]+)"', img).group(1)
        for img in image_tags
        if isinstance(img, str) and 'src="' in img and re.search(r'src="([^"]+)"', img)
    }


def clean_img_tag(img_tag: str) -> str:
    src_match = re.search(r'src="([^"]+)"', img_tag or "", re.IGNORECASE)
    class_match = re.search(r'class="([^"]+)"', img_tag or "", re.IGNORECASE)
    if not src_match:
        return ""
    src = src_match.group(1)
    class_attr = class_match.group(1) if class_match else None
    return f'<img src="{src}" class="{class_attr}">' if class_attr else f'<img src="{src}">'


def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "")


def combine_morphemes(tokens: list[str]) -> list[str]:
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


def normalize_cloze_content(cloze_content: str) -> str:
    cloze_content = (cloze_content or "").strip()
    cloze_content = cloze_content.replace("<br>", ", ").replace("<br/>", ", ")
    cloze_content = cloze_content.replace(" and ", ", ")
    cloze_content = re.sub(r"\s*,\s*", ", ", cloze_content)

    if "(" in cloze_content and ")" in cloze_content:
        try:
            outer = re.sub(r"\([^)]*\)", "", cloze_content)
            inner_match = re.search(r"\(([^)]*)\)", cloze_content)
            inner = inner_match.group(1) if inner_match else ""
            tokens = outer.split() + inner.split()
            tokens = sorted(t.strip().lower() for t in tokens if t.strip())
            return " ".join(tokens)
        except Exception:
            pass

    if "," in cloze_content:
        tokens = [t.strip().lower() for t in cloze_content.split(",")]
    else:
        tokens = [t.strip().lower() for t in cloze_content.split()]

    tokens = combine_morphemes(tokens)

    expanded_tokens = set()
    for tok in tokens:
        expanded_tokens.add(tok)
        for syn in SYNONYMS.get(tok, []):
            expanded_tokens.add(syn)
    return " ".join(sorted(expanded_tokens))


def normalize(text: str) -> str:
    soup = BeautifulSoup(text or "", "html.parser")
    text = soup.get_text(separator=" ")
    text = html.unescape(text)
    text = text.replace("&", "and").replace("&amp;", "and").replace("\xa0", " ")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"\(\s*e\.?g\.?,?\s*", "(e.g. ", text)
    text = re.sub(r"\s*\)", ")", text)

    cloze_matches = re.findall(r"\{\{c(\d+)::(.*?)(?:::.*?)?\}\}", text)
    cloze_dict: dict[str, list[str]] = defaultdict(list)
    for group, content in cloze_matches:
        cloze_dict[group].append(content)
    text = re.sub(r"\{\{c\d+::.*?(?:::.*?)?\}\}", "", text)
    for group, contents in cloze_dict.items():
        combined = ", ".join(contents)
        normalized = normalize_cloze_content(combined)
        text += f" {{c{group}::{normalized}}}"

    text = re.sub(r"[.,:;!?]", "", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s*/\s*", " or ", text)
    text = text.replace("↑", "increased").replace("↓", "decreased").replace("↔", "normal")

    for abbr, full in _REPLACEMENTS.items():
        text = re.sub(rf"\b{abbr}\b", full, text)
    return re.sub(r"\s+", " ", text).strip().lower()


def is_similar(a: str, b: str, threshold: float) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= threshold


def group_notes_by_similarity(
    note_infos: list,
    threshold: float,
    field_name: str = "Text",
    has_excluded_tag: Callable = lambda note: False,
):
    note_lookup: dict[str, list] = defaultdict(list)
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
            continue
        matched_key = next((k for k in note_lookup if is_similar(norm, k, threshold)), None)
        if matched_key:
            note_lookup[matched_key].append(note)
        else:
            note_lookup[norm].append(note)
    return note_lookup


def group_similar_notes_by_content(
    note_infos: list,
    threshold: float,
    field_name: str = "Text",
    has_excluded_tag: Callable = lambda note: False,
):
    return group_notes_by_similarity(note_infos, threshold, field_name, has_excluded_tag)


def group_note_ids_by_similarity(
    note_infos: list,
    threshold: float,
    field_name: str = "Text",
    has_excluded_tag: Callable = lambda note: False,
) -> dict[str, list[int]]:
    grouped = group_notes_by_similarity(note_infos, threshold, field_name, has_excluded_tag)
    return {k: [n.id for n in v] for k, v in grouped.items()}

