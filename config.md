# _Change_notes Configuration Guide

This guide explains what each config section does and what you can safely edit.

## Most Users Only Need These Settings

- **Make tag/image merge matching stricter or looser**: edit `global_config.fuzzy_opts` (`default_fuzz`, `min_fuzz`).
- **Restrict tag merges to specific parent tags**: edit `merge_tags_config` with `merge_select_only` and `merge_only_parents`.
- **Block specific tags from being transferred during tag merge**: edit `merge_tags_config` with `excluded_tags`.
- **Tag near-duplicates without merging notes**: edit `tag_dupes_config` with `comparison_field`, `tag_unmatched`, and `unmatched_tag`.
- **Merge scheduling only when notes are very similar**: edit `merge_scheduling` with `merge_similarity_threshold` and `multi_card_policy`.
- **Exclude notes from image merging**: edit `merge_images_config` with `excluded_tags` and `fields_to_scan_for_images`.
- **Tune image merge strictness**: edit `global_config.fuzzy_opts` (`default_fuzz`, `min_fuzz`).
- **Control separator breaks in the Browser right-click menu**: edit `global_config.main_context_menu_separator_before` and `global_config.main_context_menu_separator_after_edit_menu`.
- **Control backups during batch note-type changes**: edit `batch_note_change_config` with `enable_backup` and `backup_directory`.
- **Protect note types from delete-empty cleanup**: edit `delete_empty_notes_config` with `protected_notes`.

## Config Section Reference

### `global_config`

Shared fallback defaults used by multiple tools.

#### Most Important Keys

- `fuzzy_opts.default_fuzz`: default fuzzy value for shared threshold prompts.
- `fuzzy_opts.min_fuzz`: lower fuzzy bound for shared threshold prompts.
- `main_context_menu_separator_before`: per-top-level-item bool map for adding a separator before this add-on's Browser right-click menu entries.
- `main_context_menu_separator_after_edit_menu`: add trailing separator after `Edit Menu`.

`main_context_menu_separator_before` supported keys:
- `missed_tags_menu`
- `add_custom_tags_1`, `add_custom_tags_2`, `add_custom_tags_3` (and any additional `add_custom_tags_<n>` section keys you create)
- `other_actions_menu`
- `add_img_class_action`
- `merge_menu`
- `edit_menu`

#### Common Mistakes

- Assuming module sections still own fuzzy thresholds.
- Tuning module behavior here that is unrelated to fuzzy thresholds.
- Editing legacy top-level `global_fuzzy_opts` instead of `global_config.fuzzy_opts`.

### `merge_tags_config`

How notes are compared for tag merging and how merge output is tagged.

#### Most Important Keys

- `comparison_field`: note field used for text comparison.
- Threshold defaults come from `global_config.fuzzy_opts` (`default_fuzz`, `min_fuzz`).
- `ask_fuzzy_each_time`: prompts for a threshold each run when `true`.
- `base_tag`: parent tag used for merge output.
- `merge_select_only`: limits merges to allowed parent tags when `true`.
- `merge_only_parents`: allowed parent tag list.
- `excluded_tags`: tags (and their child tags) that should never transfer between notes.

#### When To Edit It

- Unrelated notes are being grouped together.
- Similar notes are being missed.
- You want merges limited to certain parent tags.
- You need some tags to stay local to each note even when merge runs.

#### Common Mistakes

- Setting `global_config.fuzzy_opts.default_fuzz` too low and over-grouping.
- Filling `merge_only_parents` but leaving `merge_select_only` set to `false`.
- Using `excluded_tags` expecting notes with those tags to be skipped entirely (it only blocks tag transfer).

### `tag_dupes_config`

Duplicate detection that tags likely matches without merging notes.

#### Most Important Keys

- `comparison_field`: field used for duplicate matching.
- `base_tag`: parent tag for duplicate groups.
- `multi_tag_child`: child segment used for larger groups.
- `tag_unmatched`: tags notes with no matches when `true`.
- `unmatched_tag`: tag text for unmatched notes.
- `log_folder`: output log location.

#### When To Edit It

- You want cleaner duplicate-review tags.
- You want unmatched notes tagged for follow-up.
- You want a clearer output tag structure.

#### Common Mistakes

- Confusing duplicate tagging with actual note merging.
- Enabling `tag_unmatched` but leaving `unmatched_tag` vague or unhelpful.

### `merge_scheduling`

How scheduling data is merged between similar notes.

#### Most Important Keys

- `merge_similarity_threshold`: match threshold (`0.0-1.0` or `0-100`).
- `merge_field_index`: zero-based field index used for comparison.
- `multi_card_policy`: handling for notes with multiple cards (`skip`, `first_card`, `all_cards`).
- `tag_on_merge`: optional tag added after a scheduling merge.
- Threshold prompt cancel behavior is fixed: cancel aborts the run.

#### When To Edit It

- Scheduling merges are too strict or too permissive.
- Multi-card notes need different handling.
- You want an audit tag after successful scheduling merges.

#### Common Mistakes

- Using the wrong `merge_field_index`.
- Setting the threshold so low that unrelated notes merge.
- Forgetting to review `multi_card_policy` before running.

### `merge_images_config`

How images are found, matched, inserted, logged, and tagged during image merge workflows.

#### Most Important Keys

- Threshold defaults come from `global_config.fuzzy_opts` (`default_fuzz`, `min_fuzz`).
- `ask_threshold_each_time`: prompts for a threshold each run when `true`.
- `fields_to_scan_for_images`: fields scanned for `<img>` tags.
- `excluded_tags`: notes with these tags are skipped.
- `merge_behavior.wrap_images_in_div`: wraps inserted images for layout control.
- `merge_behavior.insert_new_line_between_images`: adds line breaks between inserted images.
- `merge_behavior.append_to_existing_field`: appends instead of replacing.
- `logging.enable_log_popup`, `logging.save_log_to_desktop`: run-log visibility.
- `tagging.add_to_merged`, `tagging.add_to_donor`, `tagging.add_to_unchanged`, `tagging.no_images_found`: result tags.
- Use `{MM-DD}` inside an image result tag to insert the run date, for example `DONE::IMG_Uni::{MM-DD}::donor`.

#### When To Edit It

- Image matching is too loose or too strict.
- The wrong fields are being scanned.
- Certain tagged notes should never be included.

#### Common Mistakes

- Forgetting to include the field that actually contains images.
- Excluding tags too broadly and skipping too many notes.

### `merge_images_and_tags_config`

Reserved section for combined image-and-tag merge workflow defaults.

#### Current Behavior

- Current runtime behavior relies on shared/global fuzzy settings and in-file defaults.
- Values placed here may be retained for forward compatibility but are not the primary control path today.

### `delete_empty_notes_config`

Protection rules for delete-empty note cleanup.

#### Most Important Keys

- `protected_notes`: note-type names or wildcard patterns that should never be deleted.

#### When To Edit It

- You add note types that must be protected.
- You want wildcard protection for groups of note types.

#### Common Mistakes

- Running cleanup before adding protected note types.

### `batch_note_change_config`

Batch note-type conversion behavior, mapping memory, and backups.

#### Most Important Keys

- `hide_menu_when_one_type_selected`: hide the batch-change menu action when selection contains only one source note type.
- `allow_single_type_override`: if `false`, block the run when selection has only one source note type.
- `batch_size`: chunk size used for backup creation and post-change mapping/tagging.
- `show_progress`: show progress bar during backup and post-change processing.
- `auto_confirm_mappings`: when `true`, reuse `last_mapping_profile` (or auto-pick the only profile) without prompting.
- `field_mappings`, `last_mapping_profile`, `last_target_model`: saved mapping state.
- `tag_on_change`: optional tag added only to notes whose note type actually changed.
- `enable_backup`, `backup_directory`: write a JSON backup snapshot before conversion.
- **Enable backup ALWAYS on first run.**

#### When To Edit It

- You want safer backups or a custom backup folder.
- You want different speed or visibility behavior for large runs.

### `custom_tags_config.add_custom_tags_<n>`

A browser preset-tag menu section. Any numbered section key (`add_custom_tags_1`, `add_custom_tags_2`, `add_custom_tags_3`, …) is auto-discovered and shown as a top-level menu in ascending numeric order.

#### Most Important Keys

- `menu_label`: top-level menu label for that section.
- `group_labels`: optional display labels for groups.
- `presets`: preset list with `label`, `tags`, and optional `group`.

#### When To Edit It

- You want faster manual tagging from the browser.
- You want grouped presets under cleaner menu labels.
- You want multiple top-level custom-tag menus split by purpose (for example, workflow vs content tags).

#### Common Mistakes

- Overloading one menu with too many flat presets.
- Using unclear preset labels.
- Forgetting any section with empty `presets` stays hidden.

### `tag_missed_notes`

Menu labels and tagging behavior for missed-question workflows, including UWorld, NBME, AMBOSS, and custom resources.

#### Most Important Keys

- `ui.menu_label`: top-level menu title.
- `date.include_day_segment`: include day in missed-date context tags.
- `date.split_weeks`: when `true` and `date.include_day_segment` is `true`, nest day tags under `week_1`..`week_4`.
- `rotation.schedule`: rotation windows with `segment_label`, `start`, and `end` (`segment_label` is used directly as the final tag child segment).
- `rotation.exhausted_policy`, `rotation.parent_tag_segment`: post-schedule behavior and tag path segment.
- `actions.<action>.menu_label`: menu text for the action.
- `actions.base.menu_display`: show/hide the `Base` action row in the Missed Tags menu.
- `actions.<action>.prompt.show_correct_marked_checkbox`: show/hide the `correct_marked` checkbox for that specific prompt action.
- `actions.<action>.child_of_primary_missed`: when `true`, action tags are built under the main missed-tag root.
- `actions.<action>.tag_segment` / `actions.<action>.absolute_tags`: relative segment vs explicit full tags.
- `actions.<action>.add_missed_date_context`: whether missed-date context tags are added for the action.
- `actions.<action>.prompt.kind`: prompt mode (`none`, `number`, `form`).
- `actions.<action>.prompt.number_style`: number style (`number_only`, `range_then_number`, `rotation_then_number`).
- `actions.uworld.prompt.parent_range_block_size`, `actions.uworld.prompt.range_block_size`: UWorld numeric grouping (for example, `001-050::01-05`).
- `actions.correct_tag_missed`: controls the `UW Correct + Missed Tag` source-selector action (`menu_label`, `tag_segment`, `add_missed_date_context`).
- `actions.other.submenu_bool`, `actions.other.submenu_label`: put extra resources under an `Other` submenu (or inline when disabled).
- `actions.other.tagging` and `actions.other.actions`: standardized config for additional resource actions.

Week mapping used by `date.split_weeks`:
- `week_1`: days `01-07`
- `week_2`: days `08-14`
- `week_3`: days `15-21`
- `week_4`: days `22-31`

#### When To Edit It

- Your rotation schedule changes.
- You want different tags by resource.
- You want different behavior for repeated misses or custom sources.

#### Common Mistakes

- Leaving `rotation.schedule` outdated.
- Mixing legacy per-action keys (`label`, `base_tag`, `base_tags`) with standardized action keys in the same action.
- Renaming tags without checking saved searches that depend on them.

### `add_table_class`

Automatic class assignment for HTML `<table>` elements.

#### Most Important Keys

- `apply_to_existing_classes`: when `false`, tables that already have a class are skipped.
- `log_path`: log file path.

#### When To Edit It

- You want broader table normalization.
- You need to preserve existing table classes.

#### Common Mistakes

- Applying changes broadly in cards with custom table styling.

### `add_img_class`

Adds CSS classes to `<img>` tags based on native image size and aspect ratio.

#### Most Important Keys

- `small_width`: width in pixels; adds `small` when `width < small_width`.
- `ultra-wide_ratio`: uses `width / height`; adds `ultra-wide` when the ratio is above this value.
- `landscape_ratio_min`: adds `img-landscape` when the ratio is above this value but not ultra-wide.
- `tall_ratio`: adds `img-tall` when the ratio is below this value.
- `square_min`, `square_max`: adds `img-square` when the ratio falls between these bounds.

#### When To Edit It

- You have defined CSS classes for (preferably) all the defined classes.
- Image classes do not match your card CSS expectations.
- You want stricter separation between landscape, tall, and square images.

#### Avoid

- Mixing up pixel thresholds and ratio thresholds.
- Setting overlapping or inverted square bounds.

## Examples

### Stricter Tag Matching And Parent-Limited Merges

    {
      "merge_tags_config": {
        "comparison_field": "Text",
        "merge_select_only": true,
        "excluded_tags": [
          "DoNotTransfer",
          "Leech"
        ],
        "merge_only_parents": [
          "Step1",
          "Step2"
        ]
      }
    }

### JSON Safety Checklist

- Use double quotes for keys and string values.
- Separate items with commas.
- Use `true` and `false` without quotes.
- Most thresholds use decimal values from `0.0` to `1.0`.

`merge_similarity_threshold` also accepts `0-100`.
Example: `85` means `0.85`.
