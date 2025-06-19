import json
import os

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


