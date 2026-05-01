# Redundant Config Items Review

Date: 2026-04-26

This file lists config items currently documented in `config.md` that are redundant in the current runtime implementation.

## Method

- Reviewed documented keys in `config.md`.
- Checked live usage in `modules/*` and config loading paths.
- Marked keys as redundant when they are not consumed by runtime logic (or have no functional effect).

## Redundant Items

### `global_config`

- `default_fuzzy`
  - Why redundant: no active module reads this as an effective global fallback.
  - Practical effect: changing it does not change behavior in current code paths.

- `default_note_type`
  - Why redundant: no active module uses this key at runtime.
  - Practical effect: changing it has no effect.

- `log_folder`
  - Why redundant: active modules use section-specific log settings or hardcoded log paths.
  - Practical effect: changing it has no effect.

### `merge_images_and_tags_config`

- `default_fuzzy`
- `min_fuzzy`
- `base_tag`
- `log_folder`
  - Why redundant: the combined merge module loads the section but does not read these keys for runtime behavior.
  - Practical effect: changing these values currently does not change merge behavior.

## Notes

- If future features are added that consume any of the above keys, this classification should be revisited.
- Redundant does not always mean delete immediately; it can also mean deprecate first, then remove after a migration window.
