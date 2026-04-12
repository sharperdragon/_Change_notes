from __future__ import annotations

from aqt import mw
from aqt.qt import QDialog, QDialogButtonBox, QDoubleSpinBox, QVBoxLayout

try:
    from ..config_manager import ConfigManager  # type: ignore
except Exception:
    ConfigManager = None  # type: ignore

from .shared.text_similarity import (
    clean_img_tag,
    combine_morphemes,
    extract_images,
    extract_srcs,
    group_notes_by_similarity,
    is_similar,
    load_replacements,
    normalize,
    normalize_cloze_content,
    strip_html,
)

__all__ = [
    "clean_img_tag",
    "combine_morphemes",
    "extract_images",
    "extract_srcs",
    "group_notes_by_similarity",
    "is_similar",
    "load_replacements",
    "normalize",
    "normalize_cloze_content",
    "strip_html",
    "get_config_section",
    "load_config",
    "save_config",
    "get_field_index_from_config",
    "prompt_similarity_threshold",
]

# ! --------------------------- USER-TUNABLE CONSTANTS ---------------------------
ROOT_ADDON_NAME = "_Change_notes"
# ! -----------------------------------------------------------------------------


def _load_config_raw():
    """Load normalized runtime config, preferring root ConfigManager."""
    try:
        if ConfigManager is not None:
            data = ConfigManager(ROOT_ADDON_NAME).load()
            if isinstance(data, dict):
                return data
    except Exception:
        pass

    addon_manager = getattr(mw, "addonManager", None)
    if addon_manager is None:
        return {}

    try:
        fallback_data = addon_manager.getConfig(ROOT_ADDON_NAME) or {}
        return fallback_data if isinstance(fallback_data, dict) else {}
    except Exception:
        return {}


def get_config_section(section_name: str, default=None):
    data = _load_config_raw() or {}
    if default is None:
        default = {}
    return data.get(section_name, default)


def load_config():
    return _load_config_raw()


def save_config(config):
    if not isinstance(config, dict):
        raise ValueError("Configuration must be a JSON object.")

    if ConfigManager is not None:
        ConfigManager(ROOT_ADDON_NAME).save_config(config)
        return

    addon_manager = getattr(mw, "addonManager", None)
    if addon_manager is None:
        return
    addon_manager.writeConfig(ROOT_ADDON_NAME, config)


def get_field_index_from_config(note_type_name, field_name):
    for model in mw.col.models.all():
        if model["name"] == note_type_name:
            for i, fld in enumerate(model["flds"]):
                if fld["name"] == field_name:
                    return i
    raise ValueError(f"Field '{field_name}' not found in note type '{note_type_name}'")


def prompt_similarity_threshold(
    *,
    default: float = 0.90,
    minimum: float = 0.80,
    maximum: float = 1.00,
    ui: str = "float",
    step: float = 0.01,
    decimals: int = 2,
    title: str = "Fuzzy Threshold",
    percent_suffix: str = "%",
) -> tuple[float | None, bool]:
    dlg = QDialog(mw)
    dlg.setWindowTitle(title)
    lay = QVBoxLayout(dlg)

    spin = QDoubleSpinBox()

    if ui == "percent":
        use_min, use_max, use_def = minimum, maximum, default
        if maximum <= 1.0:
            use_min, use_max, use_def = minimum * 100, maximum * 100, default * 100
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
        lo = minimum if maximum <= 1.0 else minimum / 100.0
        hi = maximum if maximum <= 1.0 else maximum / 100.0
        val = max(min(val, hi), lo)
    else:
        val = max(min(val, maximum), minimum)

    return val, True
