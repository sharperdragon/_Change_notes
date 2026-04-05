# Change Notes Add-on Configuration Guide

This file explains the top-level sections in `config.json`.

If the right pane in Anki's config editor looks broken, keep this file in simple markdown format (headings, bullets, fenced code) and avoid markdown tables.

## General Notes

- `config.json` is the full default configuration shipped with the add-on.
- Profile-specific changes are saved by Anki as overrides.
- Values in one section only affect that section's feature.

## `batch_note_change_config`

Controls batch note type conversion.

- `hide_menu_when_one_type_selected`: Hide type dropdown when only one type is detected.
- `allow_single_type_override`: Allow manual override when only one type is detected.
- `last_target_model`: Last selected target note type.
- `field_mappings`: Source-to-target field map.
- `batch_size`: Notes processed per batch.
- `show_progress`: Show a progress bar during conversion.
- `last_mapping_profile`: Last used mapping profile name.
- `auto_confirm_mappings`: Skip manual mapping confirmation.
- `tag_on_change`: Tag applied after conversion.
- `enable_backup`: Enable backup before conversion.
- `backup_directory`: Backup destination path.

## `tag_dupes_config`

Controls duplicate-like note tagging.

- `comparison_field`: Field used for duplicate comparison.
- `base_tag`: Base tag for matched groups.
- `multi_tag_child`: Tag used for groups with multiple matches.
- `TAG UNMATCHED`: If `"true"`, unmatched notes are tagged.
- `unmatched_tag`: Tag applied to unmatched notes.
- `log_folder`: Optional log folder override.

## `merge_tags_config`

Controls fuzzy grouping and tag merging.

- `default_fuzzy`: Fuzzy threshold for grouping.
- `base_tag`: Base tag for merged groups.
- `log_folder`: Optional log folder override.
- `merge_select_only`: Merge only selected notes.
- `merge_only_parents`: Restrict merging to configured parent tags.

## `merge_scheduling`

Controls scheduling merge behavior.

- `merge_similarity_threshold`: Similarity threshold for merge candidates.
- `default_fuzzy`: Default fuzzy threshold.
- `min_fuzzy`: Lower fuzzy bound.
- `merge_field_index`: Field index used for comparison.
- `scheduling_merge_log_path`: Log file name/path.
- `use_text_replacements`: Apply text replacements before comparison.
- `tag_on_merge`: Tag added to merged notes.

## `merge_images_config`

Controls image merge behavior.

- `default_threshold`: Default merge threshold.
- `min_threshold`, `max_threshold`: Threshold bounds.
- `ask_threshold_each_time`: Prompt for threshold each run.
- `allowed_models`: Optional allow-list of note types.
- `excluded_tags`: Skip notes with these tags.
- `fields_to_scan_for_images`: Fields scanned for image content.
- `merge_behavior`: Merge formatting controls.
- `logging`: Logging options.
- `tagging`: Tags applied based on merge result.

## `merge_images_and_tags_config`

Controls combined image+tag merge settings.

- `default_fuzzy`: Default fuzzy threshold.
- `min_fuzzy`: Lower fuzzy bound.
- `base_tag`: Base tag for merged results.
- `log_folder`: Optional log folder override.

## `delete_empty_notes_config`

Controls note type cleanup safeguards.

- `protected_notes`: Note types that should never be removed.

## `tag_selected_notes_config`

Legacy compatibility section for selected-note tagging.

- `base_name`: Label for the base tag action.
- `missed_base_tag`: Base tag list.
- `missed_month_tag`: Monthly tag list.
- `subset_1_name`, `subset_2_name`: Menu labels.
- `subset_tag_1`, `subset_tag_2`: Tags applied by subset actions.
- `other_menu`: Label/prefix/resources for extra menu entries.

`add_missed_tags` is the canonical section; this section is still merged for backward compatibility.

## `add_custom_tags`

Controls custom tag presets.

- `submenu_label`: Label shown in the browser context menu.
- `message_no_notes_selected`: Message shown when no notes are selected.
- `message_applied_template`: Tooltip template after applying tags (`{tag_count}`, `{note_count}` supported).
- `presets`: List of preset objects with `label` and `tags`.

## `add_missed_tags`

Controls missed-question tagging.

- `base_missed_tag`: Root tag for missed questions.
- `Q_Banks`: Question bank labels.
- `ui.menu_label`: Root browser-menu label.
- `ui.message_no_notes_selected`: Shared no-selection message.
- `ui.message_invalid_test_number`: Invalid test-number message.
- `ui.action_label_base`: Label for the base action.
- `ui.action_label_multi_missed`: Label for the multi-missed action.
- `ui.action_label_dynamic_test_prompt`: Label for the dynamic prompt action.
- `ui.action_label_key_info`: Label for the key-info action.
- `ui.action_label_correct_guess`: Label for the correct-guess action.
- `ui.prompt_title_generic`: Generic prompt title.
- `ui.prompt_label_generic`: Generic prompt label.

Legacy sections `add_tags` and `tag_selected_notes_config` are still merged for compatibility; `add_missed_tags` overrides them when keys overlap.

## `global_config`

Shared defaults used by multiple modules.

- `default_fuzzy`: Default fuzzy threshold.
- `default_note_type`: Default note type fallback.
- `log_folder`: Default log folder.

## `global_fuzzy_opts`

Global fuzzy threshold bounds.

- `default_fuzz`: Default fuzzy score.
- `min_fuzz`: Minimum allowed score.
- `max_fuzz`: Maximum allowed score.

## Example Snippet

```json
{
  "batch_note_change_config": {
    "hide_menu_when_one_type_selected": false,
    "allow_single_type_override": true,
    "last_target_model": "*Nord+",
    "field_mappings": {
      "Text": "Front",
      "Extra": "Back"
    },
    "batch_size": 200,
    "show_progress": true
  }
}
```
