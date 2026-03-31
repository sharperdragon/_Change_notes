"""Compatibility wrapper around shared utility helpers."""

from . import utils as _utils


clean_img_tag = _utils.clean_img_tag
combine_morphemes = _utils.combine_morphemes
extract_images = _utils.extract_images
extract_srcs = _utils.extract_srcs
get_config_section = _utils.get_config_section
get_field_index_from_config = _utils.get_field_index_from_config
group_notes_by_similarity = _utils.group_notes_by_similarity
is_similar = _utils.is_similar
load_config = _utils.load_config
load_replacements = _utils.load_replacements
normalize = _utils.normalize
normalize_cloze_content = _utils.normalize_cloze_content
prompt_similarity_threshold = _utils.prompt_similarity_threshold
save_config = _utils.save_config
strip_html = _utils.strip_html

__all__ = [
    "clean_img_tag",
    "combine_morphemes",
    "extract_images",
    "extract_srcs",
    "get_config_section",
    "get_field_index_from_config",
    "group_notes_by_similarity",
    "is_similar",
    "load_config",
    "load_replacements",
    "normalize",
    "normalize_cloze_content",
    "prompt_similarity_threshold",
    "save_config",
    "strip_html",
]
