# _Change_notes Configuration Guide

This guide explains each top-level section in `config.json` in plain language.

## Quick Start (No Terminal Needed)

1. In Anki: `Tools -> Add-ons -> _Change_notes -> Config`.
2. Or open `config.json` directly in VSCode.
3. Change only the values you want.
4. Save, then run the tool again in Anki.

## Before You Edit

- Use valid JSON: double quotes for keys/strings, commas between items, and `true`/`false` without quotes.
- Most fuzzy/threshold values are decimal numbers from `0.0` to `1.0`.
- `merge_similarity_threshold` also accepts `0-100` (for example, `85` = `0.85`).

## How Settings Are Loaded

- `config.json` is the shipped default config.
- Anki stores your profile overrides separately and merges them at runtime.
- Legacy section names are auto-migrated (`merge_scheduling_config` -> `merge_scheduling`, `Add_img_class` -> `add_img_class`, `Add_table_class` -> `add_table_class`).

## Most Common Settings to Change

- `merge_tags_config.default_fuzzy`: stricter/looser tag grouping.
- `merge_tags_config.merge_only_parents`: limit merges to specific parent tags.
- `merge_images_config.excluded_tags`: skip image merge on certain tags.
- `merge_images_config.fields_to_scan_for_images`: fields checked for `<img>` tags.
- `tag_dupes_config.unmatched_tag`: custom tag for unmatched notes.
- `batch_note_change_config.backup_directory`: where backups are written.

## `global_config`

Shared defaults used by multiple modules.

- `default_fuzzy`: fallback fuzzy value.
- `default_note_type`: fallback note type name.
- `log_folder`: default log folder.

## `global_fuzzy_opts`

Global fuzzy bounds used by related tools.

- `default_fuzz`
- `min_fuzz`
- `max_fuzz`

## `merge_tags_config`

Fuzzy grouping + tag unification across selected notes.

- `comparison_field`: field name used for text comparison.
- `default_fuzzy`: default threshold.
- `min_fuzzy`, `max_fuzzy`: clamp bounds.
- `ask_fuzzy_each_time`: prompt on each run when `true`.
- `base_tag`: parent tag used for run labels.
- `merge_select_only`: if `true`, parent filtering is enforced.
- `merge_only_parents`: allowed parent tags when filtering is enabled.
- `merge_only_from_parents`: legacy alias for `merge_only_parents`.

## `tag_dupes_config`

Tags near-duplicate notes and (optionally) unmatched notes.

- `comparison_field`: field used for duplicate detection.
- `base_tag`: prefix used when building output tags.
- `multi_tag_child`: suffix segment for groups with 3+ matches.
- `tag_unmatched`: preferred boolean switch for unmatched tagging.
- `TAG UNMATCHED`: legacy string-based switch (kept for compatibility).
- `unmatched_tag`: explicit unmatched tag label.
- `log_folder`: custom log folder (relative to `modules/` unless absolute).

## `merge_scheduling`

Merges scheduling state across fuzzy-matched notes.

- `merge_similarity_threshold`: match threshold (`0-1` or `0-100`).
- `merge_field_index`: field index used for comparisons.
- `tag_on_merge`: optional tag added after successful merge.
- `abort_on_cancel`: if `true`, canceling threshold prompt aborts run.
- `multi_card_policy`: one of `skip`, `first_card`, `all_cards`.
- `default_fuzzy`, `min_fuzzy`, `scheduling_merge_log_path`, `use_text_replacements`: kept for compatibility; current runtime behavior primarily uses the keys above.

## `merge_images_config`

Merges image content between notes.

- `default_threshold`, `min_threshold`, `max_threshold`: image match thresholds.
- `ask_threshold_each_time`: prompt on each run.
- `allowed_models`: optional allow-list of note types.
- `excluded_tags`: notes with these tags are skipped.
- `fields_to_scan_for_images`: fields checked for image tags.
- `merge_behavior`: HTML insertion formatting options.
- `logging`: popup/file logging options.
- `tagging`: tags applied by merge outcome.
- Image insertion policy is append-only in code (`modules/merge_imgs.py`, `IMAGE_INSERT_POLICY = "append_only"`).

## `merge_images_and_tags_config`

Combined image + tag merge behavior.

- `default_fuzzy`
- `min_fuzzy`
- `base_tag`
- `log_folder`

## `batch_note_change_config`

Batch note-type conversion workflow settings.

- `hide_menu_when_one_type_selected`
- `allow_single_type_override`
- `last_target_model`
- `field_mappings`
- `batch_size`
- `show_progress`
- `last_mapping_profile`
- `auto_confirm_mappings`
- `tag_on_change`
- `enable_backup`
- `backup_directory`

## `delete_empty_notes_config`

Safeguards for delete-empty workflow.

- `protected_notes`: note types that should never be removed.

## `add_custom_tags`

First custom-tags menu in the Browser context menu.

- `submenu_label`: root menu label.
- `group_labels`: optional display labels for groups.
- `presets`: list of preset buttons.
- `presets[].label`: menu text.
- `presets[].tags`: tags applied when clicked.
- `presets[].group`: optional one-level submenu key.

## `add_custom_tags_2` (Optional)

Second top-level custom-tags menu. Same schema as `add_custom_tags`.

- Hidden automatically when `presets` is empty.

## `tag_missed_qid_notes`

Canonical config for missed-question tagging.

- `ui.menu_label`: menu label.
- `rotation.schedule`: list of `{label, start, end}` windows.
- `rotation.exhausted_policy`: `unknown` or `next`.
- `rotation.parent_tag_segment`, `winter_break_label`, `post_rotation_label`: rotation tag naming.
- `actions.base`: base action tags.
- `actions.uworld`, `actions.nbme`, `actions.amboss`: source-specific behaviors.
- `actions.multi_missed`: extra segment for repeated misses.
- `actions.key_info`: key-info tag base.
- `actions.correct_guess`: correct-guess tagging behavior.
- `actions.other`: custom "other resource" tags.
- `Q_Banks`: legacy/informational only.

Legacy sections `add_missed_tags`, `add_tags`, and `tag_selected_notes_config` are still merged into this canonical section for compatibility.

## `add_table_class`

Controls automatic class assignment for HTML tables.

- `apply_to_existing_classes`: when `false`, tables that already have a `class` are skipped.
- `log_path`: output log path.

## `add_img_class`

Controls image aspect-ratio classification.

- `small_width`
- `ultra-wide_ratio`
- `landscape_ratio_min`
- `tall_ratio`
- `square_min`
- `square_max`

These values control which CSS classes are added (for example, `small`, `img-landscape`, `img-tall`, `img-square`).

## Script-Level Tunables (VSCode)

Some behavior is intentionally hardcoded in Python files and not exposed in `config.json`:

- `modules/merge_imgs.py`: `IMAGE_INSERT_POLICY` (currently append-only).
- `modules/add_custom_tags.py`: no-selection/success message strings.
- `modules/add_missed_tags.py`: some prompt labels and validation messages.
- `modules/add_table_class/main.py`: constants like `TARGET_CLASS` and `EXCLUDE_CLASS`.
