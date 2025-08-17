from aqt import mw
import json
import os
import re, sys
from ..config_manager import ConfigManager

config_manager = ConfigManager("Change_notes")
config = config_manager.load()

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
        default = int(float(config.get("default_fuzzy", 0.98)) * 100)
    val, ok = QInputDialog.getInt(
        mw, "Set Fuzzy Match Threshold",
        "Select fuzzy match threshold (0 = loose, 100 = strict):",
        default, 85, 100, 1
    )
    if ok:
        return val / 100  # Normalize to 0.0–1.0 range
    return None