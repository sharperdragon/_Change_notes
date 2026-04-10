# Merge Settings

## What This Tab Controls
This tab groups all merge-related settings for tags, images, mixed merge logic, and scheduling merge.

## Key Sections
- `merge_tags_config`
- `merge_images_config`
- `merge_images_and_tags_config`
- `merge_scheduling`

## High-risk Fields
- `merge_tags_config.default_fuzzy`: Aggressive thresholds can over-merge unrelated notes.
- `merge_images_config.fields_to_scan_for_images`: Wrong field list can miss images or merge unwanted data.
- `merge_images_config.tagging.*`: Misconfigured tags can contaminate large note sets.
- `merge_scheduling.merge_field_index`: Wrong index compares the wrong field.

## Safe Edit Checklist
- Start with conservative thresholds (`0.95+`) before broad runs.
- Confirm field names/indexes match your note types.
- Confirm destination tags (`base_tag`, `tagging.*`, `tag_on_merge`) before saving.
- Run first pass on a small selected subset and review logs.

## Field Reference

### `merge_tags_config`
- `default_fuzzy`, `base_tag`, `log_folder`
- `merge_select_only`
- `merge_only_parents`
- `merge_only_from_parents`

### `merge_images_config`
- Thresholds: `default_threshold`, `min_threshold`, `max_threshold`, `ask_threshold_each_time`
- Scope: `allowed_models`, `excluded_tags`, `fields_to_scan_for_images`
- `merge_behavior`: HTML merge behavior toggles
- `logging`: popup/file logging controls
- `tagging`: tags for merged/donor/unchanged outcomes

### `merge_images_and_tags_config`
- `default_fuzzy`, `min_fuzzy`, `base_tag`, `log_folder`

### `merge_scheduling`
- `merge_similarity_threshold`, `abort_on_cancel`, `multi_card_policy`
- `default_fuzzy`, `min_fuzzy`, `merge_field_index`
- `scheduling_merge_log_path`, `use_text_replacements`, `tag_on_merge`
