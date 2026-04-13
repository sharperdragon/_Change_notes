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
- Image insertion is append-only (set in `modules/merge_imgs.py` via `IMAGE_INSERT_POLICY = "append_only"`), so added images are written to the end of each target field.
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

## `tag_missed_qid_notes`

Canonical section for missed-question tagging.

This section combines previous behavior from `add_missed_tags` and
`tag_selected_notes_config`. Legacy sections are still merged for compatibility.

## `add_custom_tags`

Controls custom tag presets.

- `submenu_label`: Label shown in the browser context menu.
- `group_labels`: Optional mapping of group keys to display labels. Keys must match `presets[].group`.
- `presets`: List of preset objects with `label` and `tags`.
- `presets[].group`: Optional single-level submenu name; presets sharing a group render under that submenu.

Custom-tag no-selection/success messages are hardcoded in `modules/add_custom_tags.py` and are not configurable.

### Missed Tags Schema

Controls missed-question tagging using an action-grouped schema.

- `ui.menu_label`: Root menu label.
- `rotation.schedule`: Rotation windows used for rotation-aware tags (`label`, `start`, `end`).
- `rotation.exhausted_policy`: Rotation fallback strategy (`unknown` or `next`).
- `rotation.parent_tag_segment`, `rotation.winter_break_label`, `rotation.post_rotation_label`: Rotation tag segment controls.
- `actions.base`: Base action (`label`, `tags`).
- `actions.uworld`: UWorld action (`label`, `base_tags`, `default_tag_prefix`, `test_range_block_size`).
- `actions.nbme`: NBME action (`label`, `base_tags`, `default_tag_prefix`).
- `actions.amboss`: Amboss action (`label`, `base_tag`, `blank_behavior`, `number_style`, `remove_from_other_menu`).
- `actions.multi_missed`: 2x Missed action (`label`, `tag_segment`).
- `actions.key_info`: Key Info action (`label`, `tag_base`).
- `actions.correct_guess`: Correct-Guess action (`label`, `tags`, `include_rotation`, `rotation_lowercase`, `unknown_segment`).
- `actions.other`: Other resources action group (`resources`, `tag_suffix`).
- `Q_Banks`: Legacy/informational field only (currently not used by runtime behavior).

Prompt dialog titles/labels and validation/no-selection messages are intentionally defined in code (`modules/add_missed_tags.py`) rather than config.

### Legacy Compatibility Mapping

Legacy keys are still accepted and normalized into the canonical action-grouped structure.

| Legacy key | Canonical key |
| --- | --- |
| `base_missed_tag`, `missed_base_tag` | `actions.base.tags` |
| `subset_1_name` | `actions.uworld.label` |
| `subset_tag_1`, `subset_1_tag` | `actions.uworld.base_tags` |
| `subset_2_name` | `actions.nbme.label` |
| `subset_tag_2`, `subset_2_tag` | `actions.nbme.base_tags` |
| `test_range_block_size` | `actions.uworld.test_range_block_size` |
| `rotation_schedule` | `rotation.schedule` |
| `schedule_exhausted_policy` | `rotation.exhausted_policy` |
| `tags.rotation_parent_segment` | `rotation.parent_tag_segment` |
| `tags.winter_break_label` | `rotation.winter_break_label` |
| `tags.post_rotation_label` | `rotation.post_rotation_label` |
| `tags.default_test_tag_prefix` | `actions.uworld.default_tag_prefix` |
| `tags.default_nbme_tag_prefix`, `tags.default_comquest_tag_prefix` | `actions.nbme.default_tag_prefix` |
| `tags.multi_miss_tag` | `actions.multi_missed.tag_segment` |
| `tags.key_tag_base` | `actions.key_info.tag_base` |
| `tags.other_suffix` | `actions.other.tag_suffix` |
| `other_menu.resources`, `other_resources` | `actions.other.resources` |
| `ui.action_label_base` | `actions.base.label` |
| `ui.action_label_multi_missed` | `actions.multi_missed.label` |
| `ui.action_label_key_info` | `actions.key_info.label` |
| `ui.action_label_correct_guess` | `actions.correct_guess.label` |
| `amboss.top_level_name` | `actions.amboss.label` |
| `amboss.base_tag` | `actions.amboss.base_tag` |
| `amboss.blank_behavior` | `actions.amboss.blank_behavior` |
| `amboss.number_style` | `actions.amboss.number_style` |
| `amboss.remove_from_other_menu` | `actions.amboss.remove_from_other_menu` |
| `correct_guess.tags` | `actions.correct_guess.tags` |
| `correct_guess.include_rotation` | `actions.correct_guess.include_rotation` |
| `correct_guess.rotation_lowercase` | `actions.correct_guess.rotation_lowercase` |
| `correct_guess.unknown_segment` | `actions.correct_guess.unknown_segment` |

Legacy sections `add_missed_tags`, `add_tags`, and `tag_selected_notes_config` are still merged for compatibility. The canonical `tag_missed_qid_notes` section wins when keys overlap.

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
