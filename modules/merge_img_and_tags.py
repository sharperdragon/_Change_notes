import os
from aqt import mw
from .merge.logic_merge_imgs import merge_images_main
from .merge.logic_merge_tags import unify_tags_on_duplicates
from .assets.scrub_match import prompt_threshold
from ..config_manager import ConfigManager

def run_combined_merge():
    config = ConfigManager("global_config", "merge_images_and_tags_config").load()

    default_thresh = float(config.get("default_fuzzy", 0.99))
    min_thresh = float(config.get("min_fuzzy", 0.85))
    if config.get("ask_threshold_each_time", True):
        threshold = prompt_threshold(default_thresh, min_thresh, 1.0)
        if threshold is None:
            return
    else:
        threshold = default_thresh

    base_tag = config.get("base_tag", "Tag+IMG_MERGED")

    if config.get("run_image_merge", True):
        merge_images_main(threshold=threshold, base_tag=base_tag)

    if config.get("run_tag_merge", True):
        unify_tags_on_duplicates(mw.form.browser, threshold=threshold, base_tag=base_tag)
