import os
import io
import re
from urllib.parse import unquote

# cache of names loaded from larger_imgs.txt
_LARGER_NAMES: set[str] | None = None

def _list_path() -> str:
    """Path to larger_imgs.txt in the same folder."""
    return os.path.join(os.path.dirname(__file__), "larger_imgs.txt")

def _normalize_name(s: str) -> str:
    return unquote(s).strip()

def _load_names() -> set[str]:
    names: set[str] = set()
    try:
        with io.open(_list_path(), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                nm = _normalize_name(line)
                if nm:
                    names.add(nm)
                    names.add(os.path.basename(nm))
    except Exception:
        pass
    return names

def _get_names() -> set[str]:
    global _LARGER_NAMES
    if _LARGER_NAMES is None:
        _LARGER_NAMES = _load_names()
    return _LARGER_NAMES

_SRC_RE = re.compile(r'''(?i)\bsrc\s*=\s*(['"])(.*?)\1''')

def _extract_src(tag_html: str) -> str | None:
    m = _SRC_RE.search(tag_html)
    return m.group(2) if m else None

def _ensure_class(tag_html: str, cls: str) -> str:
    m = re.search(r'(?i)\bclass\s*=\s*([\'"])(.*?)\1', tag_html)
    if m:
        quote = m.group(1)
        classes = m.group(2).split()
        if cls not in classes:
            classes.append(cls)
            new = f'class={quote}{" ".join(classes)}{quote}'
            start, end = m.span()
            return tag_html[:start] + new + tag_html[end:]
        return tag_html
    else:
        return tag_html.replace("<img", f'<img class="{cls}"', 1)

def should_force_larger(src: str | None) -> bool:
    if not src or src.startswith("data:"):
        return False
    names = _get_names()
    norm = _normalize_name(src)
    base = os.path.basename(norm)
    return norm in names or base in names

def add_larger_if_listed(img_tag_html: str) -> str:
    """Ensure <img> has 'larger' class if its src is listed in larger_imgs.txt."""
    src = _extract_src(img_tag_html)
    if should_force_larger(src):
        return _ensure_class(img_tag_html, "larger")
    return img_tag_html