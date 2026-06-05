# Add missing imports
import os
import re
import time
from collections import defaultdict
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

# pyright: reportMissingImports=false
# mypy: disable_error_code=import
from aqt import mw
from aqt.qt import QDialog, QDialogButtonBox, QDoubleSpinBox, QMessageBox, QPushButton, QTextEdit, QVBoxLayout
from aqt.utils import tooltip

from ..config_manager import ConfigManager
from .shared.defaults import MERGE_IMAGES_DEFAULTS, clone_defaults
from .utils import (
    clean_img_tag,
    extract_images,
    extract_srcs,
    group_notes_by_similarity,
    prompt_checkbox_option,
    prompt_similarity_threshold,
)

SKETCHY_PREFIX = "https://dashboard.sketchy.com"
SKETCHY_DOMAIN_RE = r'https?://(?:[^"/]*\.)?sketchy\.com[^"]+'

# User-tunable settings intentionally kept in-file (not config.json).
ASK_THRESHOLD_EACH_TIME = True
MERGE_WRAP_IMAGES_IN_DIV = True
MERGE_INSERT_NEW_LINE_BETWEEN_IMAGES = True
MERGE_APPEND_TO_EXISTING_FIELD = True
PROMPT_LOG_EXPORT_CHECKBOX_DEFAULT = True
PROMPT_LOG_EXPORT_CHECKBOX_LABEL = "Export log .txt to Desktop/subfolder"
PROMPT_LOG_EXPORT_TITLE = "Merge Images Log Export"
PROMPT_LOG_EXPORT_MEMORY_SECTION = "merge_images_config"
PROMPT_LOG_EXPORT_MEMORY_KEY = "export_log_to_desktop"
MERGE_INSERT_BR_BEFORE_APPENDED_DIV = True

# Insertion policy (top-level for easy future edits).
IMAGE_INSERT_POLICY = "append_only"
SUPPORTED_IMAGE_INSERT_POLICIES = {"append_only"}

DEFAULT_CONFIG = clone_defaults(MERGE_IMAGES_DEFAULTS)

CONFIG = {}
GLOBAL_FUZZY_OPTS = {
    "default_fuzz": 0.90,
    "min_fuzz": 0.80,
}


def cfg(path: str, default=None):
    node = CONFIG
    for key in path.split("."):
        if isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return default
    return node


def _as_float(value, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return float(default)


def _load_global_fuzzy_opts() -> dict[str, float]:
    global_cfg = ConfigManager("global_config").load()
    fuzzy_opts = global_cfg.get("fuzzy_opts") if isinstance(global_cfg, dict) else None
    if not isinstance(fuzzy_opts, dict):
        fuzzy_opts = {}
    return {
        "default_fuzz": _as_float(fuzzy_opts.get("default_fuzz"), 0.90),
        "min_fuzz": _as_float(fuzzy_opts.get("min_fuzz"), 0.80),
    }


# Add-on path and caches
addon_path = Path(mw.addonManager.addonsFolder()) / "_Change_notes"
FIELD_NAMES_BY_MID: dict[int, list[str]] = {}
SCAN_FIELDS = set()


def _reload_runtime_config():
    global CONFIG
    global GLOBAL_FUZZY_OPTS
    global SCAN_FIELDS
    section = ConfigManager("merge_images_config").load()
    CONFIG = ConfigManager.deep_merge_dicts(DEFAULT_CONFIG, section)
    GLOBAL_FUZZY_OPTS = _load_global_fuzzy_opts()
    SCAN_FIELDS = set(cfg("fields_to_scan_for_images", []))


_reload_runtime_config()


def extract_all_imgs(fields_html: list[str]) -> list[tuple[int, str, tuple[int, int]]]:
    """
    Return list of (field_index, src, match_span) for every <img>.
    """
    found = []
    for i, html in enumerate(fields_html):
        for m in clean_img_tag.finditer(html):
            found.append((i, m.group("src"), m.span()))
    return found


def norm_src(s: str) -> str:
    s = unescape(s)
    # strip query/hash
    parts = urlsplit(s)
    base = parts.path or s
    return os.path.basename(base).lower()


def canonical_img_src(src: str) -> str:
    """
    Canonical image source key used for duplicate detection.
    Drops query/fragment and normalizes scheme/host case.
    """
    raw = unescape((src or "").strip())
    if not raw:
        return ""
    parts = urlsplit(raw)
    scheme = (parts.scheme or "").lower()
    netloc = (parts.netloc or "").lower()
    path = parts.path or raw
    if scheme or netloc:
        return f"{scheme}://{netloc}{path}"
    return path


def canonical_src_set(srcs) -> set[str]:
    out = set()
    for src in srcs or []:
        key = canonical_img_src(src)
        if key:
            out.add(key)
    return out


def _prefix_br_for_appended_div(original_html: str, append_block: str, wrap_in_div: bool) -> str:
    """
    When appending a wrapped image block (<div>...</div>) to existing content,
    optionally add a leading <br> for visual separation.
    """
    if not append_block:
        return append_block
    if not MERGE_INSERT_BR_BEFORE_APPENDED_DIV or not wrap_in_div:
        return append_block
    if not append_block.lstrip().lower().startswith("<div"):
        return append_block
    if not (original_html or "").strip():
        return append_block
    if re.search(r"<br\s*/?>\s*$", original_html or "", flags=re.IGNORECASE):
        return append_block
    return "<br>" + append_block


def get_field_names(note):
    mid = note.mid
    if mid not in FIELD_NAMES_BY_MID:
        FIELD_NAMES_BY_MID[mid] = mw.col.models.field_names(mw.col.models.get(mid))
    return FIELD_NAMES_BY_MID[mid]


def has_excluded_tag(note) -> bool:
    excluded = set(cfg("excluded_tags", []))
    if not excluded:
        return False
    return bool(excluded & set(note.tags))


def is_model_allowed(note) -> bool:
    allowed = cfg("allowed_models", [])
    if not allowed:
        return True
    model_name = mw.col.models.get(note.mid)["name"]
    return model_name in allowed


# --- Sketchy link helpers ----------------------------------------------------
def extract_sketchy_links(html: str):
    """
    ? Return list of (href, full_anchor_html) for Sketchy dashboard links in html.
    """
    if not html:
        return []
    anchors = re.findall(
        r'(<a\b[^>]*?href="(' + SKETCHY_DOMAIN_RE + r')"[^>]*>.*?</a>)', html, flags=re.IGNORECASE | re.DOTALL
    )
    # anchors: list of tuples [(full_anchor_html, href)]
    return [(href, full_html) for (full_html, href) in anchors]


# ? Detect bare Sketchy URLs and build anchors when needed
SKETCHY_URL_ONLY_RE = re.compile(r"(" + SKETCHY_DOMAIN_RE + r")", flags=re.IGNORECASE)


def _as_real_anchor(href: str, link_html: str | None) -> str:
    """
    Normalize into a real <a href="...">...</a>. If donor had a bare URL or escaped anchor,
    we generate a short anchor to avoid losing the link.
    """
    if link_html and "<a" in link_html.lower():
        return link_html  # already a real anchor
    # short, consistent label avoids weird donor text
    return f'<a href="{href}" target="_blank" rel="noopener">Sketchy</a>'


def _find_links_any_form(html_unescaped: str):
    """
    Return list of tuples: (href, link_html_real, start_idx, end_idx)
    Accepts:
      - real anchors
      - escaped anchors (once unescaped)
      - bare URLs
    """
    results = []

    # 1) real anchors
    for m in re.finditer(
        r'(&lt;a\b[^&gt;]*?href="(' + SKETCHY_DOMAIN_RE + r')"[^&gt;]*&gt;.*?&lt;/a&gt;)',
        html_unescaped,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        # If anchors are still escaped, they'll match here. We'll unescape below.
        full_escaped = m.group(1)
        href = m.group(2)
        full_real = unescape(full_escaped)
        results.append((href, _as_real_anchor(href, full_real), m.start(), m.end()))

    # Also search already-unescaped real anchors
    for m in re.finditer(
        r'(<a\b[^>]*?href="(' + SKETCHY_DOMAIN_RE + r')"[^>]*>.*?</a>)',
        html_unescaped,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        full = m.group(1)
        href = m.group(2)
        results.append((href, _as_real_anchor(href, full), m.start(), m.end()))

    # 2) bare URLs (avoid double-adding ones already inside anchors)
    for m in SKETCHY_URL_ONLY_RE.finditer(html_unescaped):
        href = m.group(1)
        # Skip if this position is inside an existing anchor match
        inside_anchor = any(m.start() >= s and m.end() <= e for _, _, s, e in results)
        if not inside_anchor:
            results.append((href, _as_real_anchor(href, None), m.start(), m.end()))

    # Sort by start for determinism
    results.sort(key=lambda t: t[2])
    return results


# * Normalizes a URL for reliable comparisons (scheme/host/path; drops fragment; lowercases host).
def _normalize_url(u: str) -> str:
    try:
        from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

        parts = urlsplit(u.strip())
        # normalize scheme and host
        scheme = "https" if parts.scheme in ("http", "https", "") else parts.scheme
        netloc = parts.netloc.lower()
        path = parts.path or "/"
        # Optionally drop tracking params; keep meaningful ones
        q_pairs = [
            (k, v)
            for (k, v) in parse_qsl(parts.query, keep_blank_values=True)
            if not k.lower().startswith(("utm_", "fbclid"))
        ]
        query = urlencode(q_pairs, doseq=True)
        # fragment ignored for equality
        return urlunsplit((scheme, netloc, path, query, ""))
    except Exception:
        return (u or "").strip()


# * Checks if an equivalent Sketchy URL already exists in the (possibly escaped) field HTML.
def field_contains_sketchy_href_any_form(field_html: str, href: str) -> bool:
    if not field_html or not href:
        return False
    target_norm = _normalize_url(href)
    html_u = unescape(field_html)
    for found_href, _, _, _ in _find_links_any_form(html_u):
        if _normalize_url(found_href) == target_norm:
            return True
    return False


def parse_image_link_groups(field_html: str):
    """
    Identify pairs of (one-or-more &lt;img&gt;) + (Sketchy link) even if images are wrapped,
    the link is BEFORE or AFTER the images, or the link is a bare URL / escaped anchor.
    Returns: [{"srcs":[...ordered...], "link_html":..., "href":...}, ...]
    """
    results = []
    if not field_html:
        return results

    # Work on unescaped HTML so escaped anchors become searchable
    html_u = unescape(field_html)

    # Windows around the link where we sniff for neighboring &lt;img&gt; runs
    WINDOW = 1400

    # a run of &lt;img&gt; tags possibly wrapped with a closing div edge
    IMG_RUN = re.compile(
        r"(?:</div>\s*)?(?:<br\s*/?>\s*)?((?:<img\b[^>]*?>\s*)+)", flags=re.IGNORECASE | re.DOTALL
    )

    # Also permit an &lt;img&gt; run FOLLOWED by optional &lt;br/&gt; or opening &lt;div&gt; before the link
    IMG_RUN_FORWARD = re.compile(
        r"((?:<img\b[^>]*?>\s*)+)(?:<br\s*/?>\s*)?(?:<div\b[^>]*?>\s*)?", flags=re.IGNORECASE | re.DOTALL
    )

    for href, link_html_real, s, e in _find_links_any_form(html_u):
        # Look backward
        back_start = max(0, s - WINDOW)
        before = html_u[back_start:s]
        back_match = None
        # we want the trailing run nearest the link
        for m in IMG_RUN.finditer(before):
            back_match = m  # keep last

        # Look forward
        fwd_end = min(len(html_u), e + WINDOW)
        after = html_u[e:fwd_end]
        fwd_match = IMG_RUN_FORWARD.match(after)

        imgs_block = None
        # Prefer whichever side is closer: if both exist, choose the side with shorter gap
        if back_match and fwd_match:
            gap_back = s - (back_start + back_match.start())
            gap_fwd = (e + fwd_match.end()) - e
            imgs_block = back_match.group(1) if gap_back <= gap_fwd else fwd_match.group(1)
        elif back_match:
            imgs_block = back_match.group(1)
        elif fwd_match:
            imgs_block = fwd_match.group(1)

        if not imgs_block:
            continue

        imgs = extract_images(imgs_block)  # RAW &lt;img …&gt;
        srcs = extract_srcs(imgs)

        if srcs:
            results.append(
                {
                    "srcs": srcs,  # keep original order
                    "link_html": link_html_real,  # guaranteed real anchor
                    "href": href,
                }
            )

    return results


def field_contains_href(html: str, href: str) -> bool:
    if not html or not href:
        return False
    return re.search(re.escape(href), html, flags=re.IGNORECASE) is not None


def insert_link_below_images(field_html: str, group_srcs: list[str], link_html: str):
    """
    ? Insert "<br>" + link_html immediately after the last <img> whose src is in group_srcs.
    ? Returns (new_html, inserted_bool)
    """
    if not field_html or not group_srcs or not link_html:
        return field_html, False

    last_end = -1
    last_match_span = None

    # Find the last occurring <img ... src="X"> among the group's srcs
    for src in group_srcs:
        # Capture full <img ...> to know exact insertion point after this tag
        img_pat = re.compile(
            r'(<img\b[^>]*?src="' + re.escape(src) + r'"[^>]*>)', flags=re.IGNORECASE | re.DOTALL
        )
        for m in img_pat.finditer(field_html):
            if m.end() > last_end:
                last_end = m.end()
                last_match_span = (m.start(), m.end())

    if last_match_span is None:
        # Fallback: no image found; append link at end to avoid losing data
        separator = "" if field_html.endswith("<br>") else "<br>"
        return field_html + separator + link_html, True

    insert_at = last_match_span[1]

    # Always ensure a <br> before the link; avoid duplicate if one is already present
    after = field_html[insert_at : insert_at + 4].lower()  # quick peek for '<br'
    needs_br = not after.startswith("<br")

    insertion = ("<br>" if needs_br else "") + link_html

    new_html = field_html[:insert_at] + insertion + field_html[insert_at:]
    return new_html, True


# -----------------------------------------------------------------------------


def prompt_threshold(default, minimum, maximum, step=0.01, decimals=2):
    dialog = QDialog(mw)
    dialog.setWindowTitle("Fuzzy Threshold")

    layout = QVBoxLayout(dialog)
    spin = QDoubleSpinBox()
    spin.setRange(minimum, maximum)
    spin.setDecimals(decimals)
    spin.setSingleStep(step)
    spin.setValue(default)

    layout.addWidget(spin)

    button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    layout.addWidget(button_box)

    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return spin.value(), True
    return None, False


def run_merge_images(
    note_ids: list[int],
    browser=None,
    threshold: float | None = None,
    export_log_to_desktop: bool | None = None,
    show_summary_popup: bool = True,
):
    _reload_runtime_config()
    if not note_ids:
        QMessageBox.information(mw, "Unify Images", "No notes selected.")
        return None

    # ! Threshold defaulting (UI prompt moved to merge_images_main)
    if threshold is None:
        # Use global fuzzy defaults and clamp to [min, max]
        default_threshold = GLOBAL_FUZZY_OPTS["default_fuzz"]
        min_threshold = GLOBAL_FUZZY_OPTS["min_fuzz"]
        max_threshold = 1.0
        threshold = max(min(default_threshold, max_threshold), min_threshold)

    # print(f"[MergeImages] Using threshold={threshold:.3f}")

    if browser is None:
        browser = mw.form.browser

    all_note_infos = [mw.col.get_note(nid) for nid in note_ids]
    # Apply model + tag gating from config
    candidates = [n for n in all_note_infos if is_model_allowed(n) and not has_excluded_tag(n)]

    received_tag = cfg("tagging.add_to_merged", "DONE::IMG_Uni::received")
    unchanged_tag = cfg("tagging.add_to_unchanged", "IMG_Uni::same")
    donor_tag = cfg("tagging.add_to_donor", "IMG_Uni::donor")
    enable_popup = cfg("logging.enable_log_popup", True)
    save_to_desktop_cfg = cfg("logging.save_log_to_desktop", False)
    if export_log_to_desktop is None:
        save_to_desktop = bool(save_to_desktop_cfg)
    else:
        save_to_desktop = bool(export_log_to_desktop)
    log_prefix = cfg("logging.log_filename_prefix", "merged_images_log_")

    note_groups = group_notes_by_similarity(candidates, threshold, "Text", has_excluded_tag)
    # Merge behavior flags
    wrap_in_div = MERGE_WRAP_IMAGES_IN_DIV
    insert_br = MERGE_INSERT_NEW_LINE_BETWEEN_IMAGES
    append_to_existing = MERGE_APPEND_TO_EXISTING_FIELD
    image_insert_policy = (
        IMAGE_INSERT_POLICY if IMAGE_INSERT_POLICY in SUPPORTED_IMAGE_INSERT_POLICIES else "append_only"
    )

    def make_block(src_list, src_map):
        """Build an HTML block for a list of srcs respecting config flags."""
        if not src_list:
            return ""
        imgtags = [src_map[s] for s in src_list if s in src_map]
        if not imgtags:
            return ""
        body = "<br>".join(imgtags) if insert_br else "".join(imgtags)
        return f"<div>{body}</div>" if wrap_in_div else body

    log_entries = [f"⚙️ Image insert policy: {image_insert_policy}"]
    merged = 0
    all_used_donors = set()
    recipients = set()
    same_tagged_nids = []

    for group in note_groups.values():
        model_groups = defaultdict(list)
        for note in group:
            model_name = mw.col.models.get(note.mid)["name"]
            model_groups[model_name].append(note)

        for model_group in model_groups.values():
            if len(model_group) > 2:
                multi_matched_nids = []
                for note in model_group:
                    note.tags = [t for t in note.tags if t != donor_tag]
                    note.tags = list(set(note.tags) | {"IMG_Uni::multiple_match"})
                    mw.col.update_note(note)
                    multi_matched_nids.append(str(note.id))
                log_entries.append(
                    "⚠️ IMG_Uni::multiple_match tagged:\n\n" + ", ".join(multi_matched_nids) + ",\n"
                )
                continue
            if len(model_group) < 2:
                continue
            donors = []
            for note in model_group:
                for field in note.fields:
                    if extract_images(field):
                        donors.append(note)
                        break

            field_to_images = defaultdict(list)
            for donor in donors:
                for i, field in enumerate(donor.fields):
                    field_name = get_field_names(donor)[i]
                    if field_name not in SCAN_FIELDS:
                        continue
                    raw_imgs = extract_images(field)
                    cleaned_imgs = [clean_img_tag(img) for img in raw_imgs if clean_img_tag(img)]
                    for img in cleaned_imgs:
                        if img not in field_to_images[i]:
                            field_to_images[i].append(img)

            # Build ordered src list per field to respect donor ordering
            field_to_src_order = {}
            for idx, imgs in field_to_images.items():
                ordered_srcs = []
                for img in imgs:
                    m = re.search(r'src="([^"]+)"', img)
                    if m:
                        ordered_srcs.append(m.group(1))
                field_to_src_order[idx] = ordered_srcs
            # Map src -> full <img> tag for quick reconstruction
            src_to_imgtag = {}
            for idx, imgs in field_to_images.items():
                for img in imgs:
                    m = re.search(r'src="([^"]+)"', img)
                    if m:
                        src_to_imgtag[m.group(1)] = img

            # Collect Sketchy image-link groups from donor fields
            copy_links = cfg("merge_behavior.copy_sketchy_links", True)
            donor_link_groups = []
            if copy_links:
                for donor in donors:
                    field_names_donor = get_field_names(donor)
                    for di, fhtml in enumerate(donor.fields):
                        if field_names_donor[di] not in SCAN_FIELDS:
                            continue
                        groups = parse_image_link_groups(fhtml)
                        if groups:
                            for g in groups:
                                g2 = dict(g)
                                g2["donor_id"] = donor.id
                                donor_link_groups.append(g2)
            # ? De-dup by (normalized href, ordered src tuple)
            _seen_groups = set()
            _unique_groups = []
            for g in donor_link_groups:
                key = (_normalize_url(g.get("href", "")), tuple(g.get("srcs", [])))
                if key in _seen_groups:
                    continue
                _seen_groups.add(key)
                _unique_groups.append(g)
            donor_link_groups = _unique_groups

            for note in model_group:
                updated_fields = list(note.fields)
                field_names = get_field_names(note)
                changed = False
                used_donors = set()

                for i, images in field_to_images.items():
                    donor_src_order = field_to_src_order.get(i, [])
                    # Existing images in this field (order as they appear in the note)
                    existing_imgs_ordered = extract_images(updated_fields[i])
                    existing_srcs_set = canonical_src_set(extract_srcs(existing_imgs_ordered))

                    # Determine missing srcs in donor order
                    missing_srcs_ordered = []
                    queued_src_keys = set()
                    for src in donor_src_order:
                        src_key = canonical_img_src(src)
                        if not src_key or src_key in existing_srcs_set or src_key in queued_src_keys:
                            continue
                        missing_srcs_ordered.append(src)
                        queued_src_keys.add(src_key)

                    if not missing_srcs_ordered:
                        continue

                    # Append-only policy keeps donor order and always writes to field end.
                    to_append_srcs = missing_srcs_ordered
                    append_block = make_block(to_append_srcs, src_to_imgtag)

                    # Apply updates per config
                    original_html = updated_fields[i]
                    if append_to_existing:
                        if append_block:
                            block_to_append = _prefix_br_for_appended_div(original_html or "", append_block, wrap_in_div)
                            updated_fields[i] = (original_html or "") + block_to_append
                    else:
                        # Replace the field content with only the newly constructed images.
                        updated_fields[i] = append_block

                    # Track donors used for logging
                    missing_srcs = canonical_src_set(missing_srcs_ordered)
                    for donor in donors:
                        donor_srcs = canonical_src_set(extract_srcs(extract_images("".join(donor.fields))))
                        if donor_srcs & missing_srcs:
                            used_donors.add(donor.id)

                    changed = True

                    # Logging reflecting append-only insertion
                    field_name = get_field_names(note)[i]
                    if to_append_srcs:
                        block = make_block(to_append_srcs, src_to_imgtag)
                        log_entries.append(
                            f"🧬 Append to Note {note.id} field '{field_name}': {block} (donors={', '.join(str(d) for d in sorted(used_donors)) or 'None'})"
                        )
                    if not append_to_existing and to_append_srcs:
                        log_entries.append(
                            f"🔁 Replaced content in Note {note.id} field '{field_name}' due to append_to_existing_field=False"
                        )

                # ---- Copy Sketchy links under their corresponding images ----
                if copy_links and donor_link_groups:
                    # Recompute current src sets per field after image merges
                    current_field_srcs = {}
                    for fi, fhtml in enumerate(updated_fields):
                        if field_names[fi] not in SCAN_FIELDS:
                            continue
                        imgs_now = extract_images(fhtml)
                        current_field_srcs[fi] = canonical_src_set(extract_srcs(imgs_now))

                    # Track per-field normalized hrefs present (pre + during this pass)
                    field_href_norms = {}
                    for fi, fhtml in enumerate(updated_fields):
                        if field_names[fi] not in SCAN_FIELDS:
                            continue
                        html_u = unescape(fhtml)
                        present = set()
                        for found_href, _, _, _ in _find_links_any_form(html_u):
                            present.add(_normalize_url(found_href))
                        field_href_norms[fi] = present

                    for grp in donor_link_groups:
                        grp_set = canonical_src_set(grp["srcs"])

                        # 1) Ideal: a field containing ALL srcs
                        exact_target = next(
                            (fi for fi, sset in current_field_srcs.items() if grp_set.issubset(sset)), None
                        )

                        target_index = exact_target
                        if target_index is None:
                            # 2) Next-best: field with MAX OVERLAP
                            best_idx, best_overlap = None, 0
                            for fi, sset in current_field_srcs.items():
                                overlap = len(grp_set & sset)
                                if overlap > best_overlap:
                                    best_idx, best_overlap = fi, overlap
                            if best_overlap > 0:
                                target_index = best_idx

                        if target_index is None:
                            # 3) Last resort: first SCAN_FIELDS field
                            for fi, name in enumerate(field_names):
                                if name in SCAN_FIELDS:
                                    target_index = fi
                                    break

                        if target_index is None:
                            continue

                        # Skip if an equivalent href (anchor/escaped/bare) already present in this field
                        if field_contains_sketchy_href_any_form(
                            updated_fields[target_index], grp["href"]
                        ) or _normalize_url(grp["href"]) in field_href_norms.get(target_index, set()):
                            log_entries.append(
                                f"🔁 Skip link (already present) in Note {note.id} field '{field_names[target_index]}': {grp['href']}"
                            )
                            continue

                        new_html, inserted = insert_link_below_images(
                            updated_fields[target_index], grp["srcs"], grp["link_html"]
                        )
                        if inserted:
                            updated_fields[target_index] = new_html
                            changed = True
                            field_href_norms.setdefault(target_index, set()).add(_normalize_url(grp["href"]))
                            t_field_name = field_names[target_index]
                            log_entries.append(
                                f"🔗 Added Sketchy link under images in Note {note.id} field '{t_field_name}': {grp['href']}"
                            )
                            if grp.get("donor_id") is not None:
                                used_donors.add(grp["donor_id"])
                # ----------------------------------------------------------------

                if changed:
                    merged += 1
                    note.fields = updated_fields
                    note.tags = list(set(note.tags) | {received_tag})
                    recipients.add(note.id)
                    for donor in donors:
                        if donor.id in used_donors:
                            donor.tags = list(set(donor.tags) | {donor_tag})
                            mw.col.update_note(donor)
                    # Track all donors (including link-only donors) to avoid mislabeling them as "same"
                    all_used_donors.update(used_donors)
                    mw.col.update_note(note)

    src_to_note_ids = defaultdict(list)
    note_to_srcs = {}
    for note in all_note_infos:
        srcs = set()
        field_names = get_field_names(note)
        for i, field in enumerate(note.fields):
            if field_names[i] in SCAN_FIELDS:
                imgs = extract_images(field)
                srcs.update(canonical_src_set(extract_srcs(imgs)))
        note_to_srcs[note.id] = srcs

    # Tag notes with no images at all
    no_images_tag = cfg("tagging.no_images_found", "IMG_Uni::no_images")
    for note in all_note_infos:
        if not note_to_srcs.get(note.id):
            note.tags = list(set(note.tags) | {no_images_tag})
            mw.col.update_note(note)

    for nid, srcs in note_to_srcs.items():
        if srcs:
            src_to_note_ids[frozenset(srcs)].append(nid)

    for shared_srcs, nids in src_to_note_ids.items():
        if len(nids) >= 2:
            for nid in nids:
                if nid not in recipients and nid not in all_used_donors:
                    note = mw.col.get_note(nid)
                    note.tags = list(set(note.tags) | {unchanged_tag})
                    same_tagged_nids.append(nid)
                    mw.col.update_note(note)

    for shared_srcs, nids in src_to_note_ids.items():
        if len(nids) >= 2 and not any(n in recipients for n in nids):
            for nid in nids:
                if nid not in same_tagged_nids:
                    note = mw.col.get_note(nid)
                    note.tags = list(set(note.tags) | {unchanged_tag})
                    same_tagged_nids.append(nid)
                    mw.col.update_note(note)

    if same_tagged_nids:
        formatted_same = "✅ IMG_Uni::same tagged:\nNID:" + ",".join(str(nid) for nid in sorted(same_tagged_nids))
        log_entries.append(formatted_same)

    summary = f"📊 Summary:\n🧬 Images Merged: {merged}\n🧾 Notes Tagged Same: {len(same_tagged_nids)}\n"
    log_entries.insert(0, summary)

    if merged == 0:
        log_path = None
        if save_to_desktop:
            log_dir = Path.home() / "Desktop/anki_logs/Merged IMGs"
            log_dir.mkdir(parents=True, exist_ok=True)
            log_path = log_dir / f"{log_prefix}{int(time.time())}.txt"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n\n".join(log_entries))
        if show_summary_popup and enable_popup and log_entries:
            show_log_window("\n\n".join(log_entries))
        msg = "Merge Images: 0 merges."
        if log_path is not None:
            msg += f" Log saved to: {log_path}"
        elif not enable_popup:
            msg += " Popup disabled by config; see log output settings."
        tooltip(msg, period=3500)
        return {
            "merged": merged,
            "tagged_same": len(same_tagged_nids),
            "log_path": str(log_path) if log_path is not None else None,
            "summary_text": summary.strip(),
            "status_message": msg,
        }

    # Write logs to Desktop or addon logs dir based on config
    if save_to_desktop:
        log_dir = Path.home() / "Desktop/anki_logs/Merged IMGs"
    else:
        log_dir = Path(addon_path) / "logs"

    # ! ensure log directory exists to avoid FileNotFoundError
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / f"{log_prefix}{int(time.time())}.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(log_entries))

        if show_summary_popup and enable_popup:
            show_log_window("\n\n".join(log_entries))

    tooltip(
        f"Merge Images complete: merged={merged}, tagged_same={len(same_tagged_nids)}.",
        period=3500,
    )
    return {
        "merged": merged,
        "tagged_same": len(same_tagged_nids),
        "log_path": str(log_path),
        "summary_text": summary.strip(),
        "status_message": f"Merge Images complete: merged={merged}, tagged_same={len(same_tagged_nids)}.",
    }


def show_log_window(log_text):
    dlg = QDialog(mw)
    dlg.setWindowTitle("Unify Images Log")
    layout = QVBoxLayout()
    text_edit = QTextEdit()
    text_edit.setReadOnly(True)
    text_edit.setPlainText(log_text)
    layout.addWidget(text_edit)
    btn_close = QPushButton("Close")
    btn_close.clicked.connect(dlg.close)
    layout.addWidget(btn_close)
    dlg.setLayout(layout)
    dlg.resize(800, 500)
    dlg.exec()


# Delete old logs utility
def delete_old_logs(days=7):
    # Only prune addon logs dir; never touch Desktop
    save_to_desktop = cfg("logging.save_log_to_desktop", False)
    if save_to_desktop:
        return
    log_dir = Path(addon_path) / "logs"
    if not log_dir.exists():
        return
    cutoff = datetime.now() - timedelta(days=days)
    for log_file in log_dir.glob("*.txt"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                log_file.unlink()
        except Exception as e:
            print(f"[MergeImages] Failed to delete {log_file.name}: {e}")


def collect_used_donors_for_block(missing_imgs, donor_notes):

    used_donors = set()
    for donor in donor_notes:
        donor_imgs = extract_srcs(extract_images("".join(donor.fields)))
        for img in missing_imgs:
            src_match = re.search(r'src="([^"]+)"', img)
            if src_match:
                src = src_match.group(1)
                if src in donor_imgs:
                    used_donors.add(donor.id)
                    break


def merge_images_main(selected=None, browser=None):
    _reload_runtime_config()
    # --- Resolve browser ---
    if browser is None:
        browser = mw.form.browser

    # --- Resolve selected note IDs (be flexible) ---
    note_ids = None
    if selected is None:
        # No explicit selection provided; pull from the browser
        note_ids = browser.selectedNotes()
    else:
        # Normalize various possible forms of 'selected'
        if isinstance(selected, int):
            note_ids = [selected]
        elif isinstance(selected, (list, tuple, set)):
            # Ensure all are ints/strings convertible to int if needed
            note_ids = list(selected)
        else:
            # Fallback: try to treat as an iterable; if not, ignore and pull from browser
            try:
                note_ids = list(selected)
            except Exception:
                note_ids = browser.selectedNotes()

    if not note_ids:
        QMessageBox.information(mw, "Unify Images", "No notes selected.")
        return

    # ? Gather threshold config here (UI edge)
    default_threshold = GLOBAL_FUZZY_OPTS["default_fuzz"]
    min_threshold = GLOBAL_FUZZY_OPTS["min_fuzz"]
    max_threshold = 1.0
    ask_each = ASK_THRESHOLD_EACH_TIME

    # Decide threshold (prompt or silent clamp)
    if ask_each:
        t, ok = prompt_similarity_threshold(
            default=default_threshold,
            minimum=min_threshold,
            maximum=max_threshold,
            ui="float",
            title="Fuzzy Threshold (Images)",
            parent=browser,
        )
        if not ok:
            return  # user canceled
        threshold = max(min(t, max_threshold), min_threshold)
    else:
        threshold = max(min(default_threshold, max_threshold), min_threshold)

    export_logs_to_desktop = prompt_checkbox_option(
        title=PROMPT_LOG_EXPORT_TITLE,
        checkbox_label=PROMPT_LOG_EXPORT_CHECKBOX_LABEL,
        checked=PROMPT_LOG_EXPORT_CHECKBOX_DEFAULT,
        remember_section=PROMPT_LOG_EXPORT_MEMORY_SECTION,
        remember_key=PROMPT_LOG_EXPORT_MEMORY_KEY,
        parent=browser,
    )
    if export_logs_to_desktop is None:
        return

    # Delegate
    run_merge_images(
        note_ids,
        browser,
        threshold=threshold,
        export_log_to_desktop=export_logs_to_desktop,
    )
