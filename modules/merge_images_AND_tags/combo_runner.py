# combo_runner.py

from aqt.browser import Browser
from aqt import mw
from _Change_notes.modules.merge_tags import prompt_fuzzy_threshold, unify_tags_on_duplicates
from merge_images import merge_images_main  # adjust import if path is different

def run_combined_merge(browser: Browser):
    # Phase 1: merge images
    merge_images_main(browser)

    # Phase 2: unify tags
    threshold = prompt_fuzzy_threshold()
    if threshold is not None:
        unify_tags_on_duplicates(browser, threshold)