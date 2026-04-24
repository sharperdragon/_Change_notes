# _Change_notes Configuration Guide

This guide explains what each config section does and what you can safely edit.

## Most Users Only Need These Settings

| Goal | Section | Keys to edit first |
| --- | --- | --- |
| Make tag merging stricter or looser | `merge_tags_config` | `default_fuzzy`, `comparison_field` |
| Restrict tag merges to specific parent tags | `merge_tags_config` | `merge_select_only`, `merge_only_parents` |
| Tag near-duplicates without merging notes | `tag_dupes_config` | `comparison_field`, `tag_unmatched`, `unmatched_tag` |
| Merge scheduling only when notes are very similar | `merge_scheduling` | `merge_similarity_threshold`, `multi_card_policy` |
| Exclude notes from image merging | `merge_images_config` | `excluded_tags`, `fields_to_scan_for_images` |
| Make image matching stricter or looser | `merge_images_config` | `default_threshold`, `min_threshold`, `max_threshold` |
| Control backups during batch note-type changes | `batch_note_change_config` | `enable_backup`, `backup_directory` |
| Protect note types from delete-empty cleanup | `delete_empty_notes_config` | `protected_notes` |

## Config Section Reference

### `global_config`

Shared fallback defaults used by multiple tools.

Most important keys

`default_fuzzy`: broad fallback similarity value
`default_note_type`: fallback note type. Set as most likely note type to be used
`log_folder`: default log directory name

Common mistakes

- Expecting this section to override module-specific settings
- Tuning a specific tool here instead of editing that tool's own section

### `global_fuzzy_opts`

Global fuzzy matching bounds used by related tools.

Most important keys

`default_fuzz`: default fuzzy value
`min_fuzz`: lower bound
`max_fuzz`: upper bound

Common mistakes

- Changing global bounds when only one tool actually needs adjustment

### `merge_tags_config`

How notes are compared for tag merging and how merge output is tagged.

Most important keys

`comparison_field`: note field used for text comparison
`default_fuzzy`: default match threshold
`min_fuzzy`, `max_fuzzy`: allowed threshold range
`ask_fuzzy_each_time`: prompts for a threshold each run when `true`
`base_tag`: parent tag used for merge output
`merge_select_only`: limits merges to allowed parent tags when `true`
`merge_only_parents`: allowed parent tag list

When to edit it

- Unrelated notes are being grouped together
- Similar notes are being missed
- You want merges limited to certain parent tags

Common mistakes

- Setting `default_fuzzy` too low and over-grouping
- Filling `merge_only_parents` but leaving `merge_select_only` set to `false`
- Using the legacy key `merge_only_from_parents` in new edits

### `tag_dupes_config`

Duplicate detection that tags likely matches without merging notes.

Most important keys

`comparison_field`: field used for duplicate matching
`base_tag`: parent tag for duplicate groups
`multi_tag_child`: child segment used for larger groups
`tag_unmatched`: tags notes with no matches when `true`
`unmatched_tag`: tag text for unmatched notes
`log_folder`: output log location

When to edit it

- You want cleaner duplicate-review tags
- You want unmatched notes tagged for follow-up
- You want a clearer output tag structure

Common mistakes

- Confusing duplicate tagging with actual note merging
- Enabling `tag_unmatched` but leaving `unmatched_tag` vague or unhelpful

### `merge_scheduling`

How scheduling data is merged between similar notes.

Most important keys

`merge_similarity_threshold`: match threshold (`0.0-1.0` or `0-100`)
`merge_field_index`: zero-based field index used for comparison
`multi_card_policy`: handling for notes with multiple cards (`skip`, `first_card`, `all_cards`)
`tag_on_merge`: optional tag added after a scheduling merge
`abort_on_cancel`: stops the run if the threshold prompt is canceled

When to edit it

- Scheduling merges are too strict or too permissive
- Multi-card notes need different handling
- You want an audit tag after successful scheduling merges

Common mistakes

- Using the wrong `merge_field_index`
- Setting the threshold so low that unrelated notes merge
- Forgetting to review `multi_card_policy` before running

### `merge_images_config`

How images are found, matched, inserted, logged, and tagged during image merge workflows.

Most important keys

`default_threshold`, `min_threshold`, `max_threshold`: image match strictness
`ask_threshold_each_time`: prompts for a threshold each run when `true`
`fields_to_scan_for_images`: fields scanned for `<img>` tags
`excluded_tags`: notes with these tags are skipped
`merge_behavior.wrap_images_in_div`: wraps inserted images for layout control
`merge_behavior.insert_new_line_between_images`: adds line breaks between inserted images
`merge_behavior.append_to_existing_field`: appends instead of replacing
`logging.enable_log_popup`, `logging.save_log_to_desktop`: run-log visibility
`tagging.add_to_merged`, `tagging.add_to_donor`, `tagging.add_to_unchanged`, `tagging.no_images_found`: result tags

When to edit it

- Image matching is too loose or too strict
- The wrong fields are being scanned
- Certain tagged notes should never be included

Common mistakes

- Forgetting to include the field that actually contains images
- Excluding tags too broadly and skipping too many notes

### `merge_images_and_tags_config`

Defaults for the combined image-and-tag merge workflow.

#### Keys

`default_fuzzy`: default similarity threshold
`min_fuzzy`: lower threshold bound
`base_tag`: parent output tag
`log_folder`: log location for this combined workflow

Common mistakes

- Editing this section expecting it to affect image-only or tag-only runs

### `delete_empty_notes_config`

Protection rules for delete-empty note cleanup.

Most important keys

`protected_notes`: note-type names or wildcard patterns that should never be deleted

When to edit it

- You add note types that must be protected
- You want wildcard protection for groups of note types

Common mistakes

- Running cleanup before adding protected note types

### `batch_note_change_config`

Batch note-type conversion behavior, mapping memory, and backups.

Most important keys

`batch_size`: number of notes processed per batch. High values can stall anki, low values are slower
`show_progress`: progress visibility during the run
`auto_confirm_mappings`: skips repeated mapping confirmations when `true`
`field_mappings`, `last_mapping_profile`, `last_target_model`: saved mapping state
`tag_on_change`: optional tag added to changed notes
`enable_backup`, `backup_directory`: backup safety settings. Enable backup ALWAYS on first run.

When to edit it

- You want safer backups or a custom backup folder
- You want different speed or visibility behavior for large runs

### `add_custom_tags`

The first browser preset-tag menu.

Most important keys

`submenu_label`: top-level menu label
`group_labels`: optional display labels for groups
`presets`: preset list with `label`, `tags`, and optional `group`

When to edit it

- You want faster manual tagging from the browser
- You want grouped presets under cleaner menu labels

Common mistakes

- Overloading one menu with too many flat presets
- Using unclear preset labels

### `add_custom_tags_2`

An optional second preset-tag menu using the same schema as `add_custom_tags`.

Most important keys

`submenu_label`: second top-level menu label
`group_labels`: optional display labels for grouped presets
`presets`: second preset list

When to edit it

- You want to separate preset sets, such as content tags vs workflow tags

Common mistakes

- Forgetting this menu stays hidden when `presets` is empty

### `tag_missed_qid_notes`

Menu labels and tagging behavior for missed-question workflows, including UWorld, NBME, AMBOSS, and custom resources.

Most important keys

`ui.menu_label`: top-level menu title
`rotation.schedule`: rotation windows with `label`, `start`, and `end`
`rotation.exhausted_policy`, `rotation.parent_tag_segment`: post-schedule behavior and tag path segment
`actions.base.tags`: base missed-question tags
`actions.uworld.*`, `actions.nbme.*`, `actions.amboss.*`: source-specific behavior
`actions.other.resources`, `actions.other.tag_suffix`: custom resource menu and tag suffix

When to edit it

- Your rotation schedule changes
- You want different tags by resource
- You want different behavior for repeated misses or custom sources

Common mistakes

- Leaving `rotation.schedule` outdated
- Mixing legacy missed-tag sections with canonical edits
- Renaming tags without checking saved searches that depend on them

### `add_table_class`

Automatic class assignment for HTML `<table>` elements.

Most important keys

`apply_to_existing_classes`: when `false`, tables that already have a class are skipped
`log_path`: log file path

When to edit it

- You want broader table normalization
- You need to preserve existing table classes

Common mistakes

- Applying changes broadly in cards with custom table styling

### `add_img_class`

Adds CSS classes to `<img>` tags based on native image size and aspect ratio.

Most important keys

`small_width`: width in pixels; adds `small` when `width < small_width`
`ultra-wide_ratio`: uses `width / height`; adds `ultra-wide` when the ratio is above this value
`landscape_ratio_min`: adds `img-landscape` when the ratio is above this value but not ultra-wide
`tall_ratio`: adds `img-tall` when the ratio is below this value
`square_min`, `square_max`: adds `img-square` when the ratio falls between these bounds

When to edit it

- You have defined CSS classes for (preferably) all the defined classes
- Image classes do not match your card CSS expectations
- You want stricter separation between landscape, tall, and square images

#### Avoid

- Mixing up pixel thresholds and ratio thresholds
- Setting overlapping or inverted square bounds

## Examples

### Stricter tag matching and parent-limited merges

```json
{
  "merge_tags_config": {
    "comparison_field": "Text",
    "default_fuzzy": 0.92,
    "merge_select_only": true,
    "merge_only_parents": [
      "Step1",
      "Step2"
    ]
  }
}
```

JSON Safety Checklist

- Use double quotes for keys and string values
- Separate items with commas
- Use `true` and `false` without quotes
- Most thresholds use decimal values from `0.0` to `1.0`

`merge_similarity_threshold` also accepts `0-100`  
Example: `85` means `0.85`
