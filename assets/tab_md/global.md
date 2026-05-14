# Global

## What This Tab Controls
This tab defines shared defaults across modules, including global fuzzy thresholds.

## Key Sections
- `global_config`

## High-risk Fields
- `global_config.fuzzy_opts.default_fuzz`: Too low increases false matches; too high can miss intended merges.
- `global_config.default_note_type`: If invalid, operations that rely on a fallback model can misroute.
- `global_config.fuzzy_opts.min_fuzz`: Extreme bounds can break threshold UX.

## Safe Edit Checklist
- Keep fuzzy values in `[0.0, 1.0]`.
- Keep `min_fuzz <= default_fuzz <= 1.0`.
- Use an existing note type for `default_note_type`.
- Save and run one merge-related action as a smoke test.

## Field Reference

### `global_config`
- `default_note_type`: Fallback note type used where a target model is required.
- `log_folder`: Default logging folder/path for modules that emit logs.
- `fuzzy_opts.default_fuzz`: Preferred default slider/input value for fuzzy comparisons.
- `fuzzy_opts.min_fuzz`: Lower bound for fuzzy threshold controls.

## Example

```json
{
  "global_config": {
    "default_note_type": "*Nord+",
    "log_folder": "logs",
    "fuzzy_opts": {
      "default_fuzz": 0.97,
      "min_fuzz": 0.59
    }
  }
}
```
