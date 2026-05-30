# Global

## What This Tab Controls
This tab defines shared defaults across modules, including global fuzzy thresholds.

## Key Sections
- `global_config`

## High-risk Fields
- `global_config.fuzzy_opts.default_fuzz`: Too low increases false matches; too high can miss intended merges.
- `global_config.default_note_type`: If invalid, operations that rely on a fallback model can misroute.
- `global_config.fuzzy_opts.min_fuzz`: Extreme bounds can break threshold UX.
- `global_config.main_context_menu_separator_before`: Wrong keys or accidental `true` values can produce unexpected menu breaks.

## Safe Edit Checklist
- Keep fuzzy values in `[0.0, 1.0]`.
- Keep `min_fuzz <= default_fuzz <= 1.0`.
- Use an existing note type for `default_note_type`.
- Use booleans in `main_context_menu_separator_before` and only supported keys.
- Save and run one merge-related action as a smoke test.

## Field Reference

### `global_config`
- `default_note_type`: Fallback note type used where a target model is required.
- `log_folder`: Default logging folder/path for modules that emit logs.
- `fuzzy_opts.default_fuzz`: Preferred default slider/input value for fuzzy comparisons.
- `fuzzy_opts.min_fuzz`: Lower bound for fuzzy threshold controls.
- `main_context_menu_separator_before`: Adds a separator before each named top-level Browser right-click menu item for this add-on.
- `main_context_menu_separator_after_edit_menu`: Adds a trailing separator after `Edit Menu`.

`main_context_menu_separator_before` keys:
- `missed_tags_menu`
- `add_custom_tags_1`, `add_custom_tags_2`, `add_custom_tags_3` (and any added `add_custom_tags_<n>` section keys)
- `other_actions_menu`
- `add_img_class_action`
- `merge_menu`
- `edit_menu`

## Example

```json
{
  "global_config": {
    "default_note_type": "*Nord+",
    "log_folder": "logs",
    "fuzzy_opts": {
      "default_fuzz": 0.97,
      "min_fuzz": 0.59
    },
    "main_context_menu_separator_before": {
      "missed_tags_menu": true,
      "add_custom_tags_1": false,
      "add_custom_tags_2": false,
      "add_custom_tags_3": false,
      "other_actions_menu": true,
      "add_img_class_action": false,
      "merge_menu": true,
      "edit_menu": false
    },
    "main_context_menu_separator_after_edit_menu": true
  }
}
```
