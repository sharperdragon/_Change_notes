# Other

## What This Tab Controls
This tab contains operational settings for cleanup, batch note type conversion, and duplicate-like tagging.

## Key Sections
- `delete_empty_notes_config`
- `batch_note_change_config`
- `tag_dupes_config`

## High-risk Fields
- `delete_empty_notes_config.protected_notes`: Missing entries can allow accidental deletion.
- `batch_note_change_config.field_mappings`: Incorrect mappings can misplace content.
- `batch_note_change_config.enable_backup`: Disabling backup increases recovery risk.
- `tag_dupes_config.comparison_field`: Wrong field selection changes duplicate detection quality.

## Safe Edit Checklist
- Keep protected note types complete before cleanup operations.
- Validate field mappings with a tiny sample before bulk conversion.
- Keep backups enabled for large conversions.
- Confirm duplicate comparison field exists on target models.

## Field Reference

### `delete_empty_notes_config`
- `protected_notes`: Note types exempt from deletion.

### `batch_note_change_config`
- `hide_menu_when_one_type_selected`, `allow_single_type_override`
- `last_target_model`, `field_mappings`, `batch_size`, `show_progress`
- `last_mapping_profile`, `auto_confirm_mappings`
- `tag_on_change`, `enable_backup`, `backup_directory`

### `tag_dupes_config`
- `comparison_field`, `base_tag`, `multi_tag_child`
- `TAG UNMATCHED`, `unmatched_tag`, `log_folder`
