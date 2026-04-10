# Global

## What This Tab Controls
This tab defines shared defaults that multiple modules may inherit when module-specific values are not provided.

## Key Sections
- `global_config`
- `global_fuzzy_opts`

## High-risk Fields
- `global_config.default_fuzzy`: Too low increases false matches; too high can miss intended merges.
- `global_config.default_note_type`: If invalid, operations that rely on a fallback model can misroute.
- `global_fuzzy_opts.min_fuzz` / `global_fuzzy_opts.max_fuzz`: Inverted or extreme bounds can break threshold UX.

## Safe Edit Checklist
- Keep fuzzy values in `[0.0, 1.0]`.
- Keep `min_fuzz <= default_fuzz <= max_fuzz`.
- Use an existing note type for `default_note_type`.
- Save and run one merge-related action as a smoke test.

## Field Reference

### `global_config`
- `default_fuzzy`: Baseline fuzzy threshold used by modules that defer to global defaults.
- `default_note_type`: Fallback note type used where a target model is required.
- `log_folder`: Default logging folder/path for modules that emit logs.

### `global_fuzzy_opts`
- `default_fuzz`: Preferred default slider/input value for fuzzy comparisons.
- `min_fuzz`: Lower bound for fuzzy threshold controls.
- `max_fuzz`: Upper bound for fuzzy threshold controls.

## Example

```json
{
  "global_config": {
    "default_fuzzy": "0.95",
    "default_note_type": "*Nord+",
    "log_folder": "logs"
  },
  "global_fuzzy_opts": {
    "default_fuzz": 0.97,
    "min_fuzz": 0.59,
    "max_fuzz": 1.0
  }
}
```
