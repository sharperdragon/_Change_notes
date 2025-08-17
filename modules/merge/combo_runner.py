# combo_runner.py

from aqt.browser import Browser
from aqt import mw
from .merge_tags import prompt_fuzzy_threshold, unify_tags_on_duplicates
from .Mod_merge_imgs import merge_images_main # adjust import if path is different
from ...config_manager import ConfigManager

def run_combined_merge(browser: Browser):
    # Phase 1: merge images
    merge_images_main(browser)

    # Phase 2: unify tags
    threshold = prompt_fuzzy_threshold()
    if threshold is not None:
        unify_tags_on_duplicates(browser, threshold)