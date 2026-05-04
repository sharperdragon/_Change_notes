# Add CSS Class

## What This Tab Controls
This tab controls table/image class assignment helpers used to standardize card HTML rendering.

## Key Sections
- `add_table_class`
- `add_img_class`

## High-risk Fields
- `add_img_class.square_min` / `square_max`: Bad boundaries misclassify many images.
- `add_img_class.ultra-wide_ratio` / `landscape_ratio_min` / `tall_ratio`: Incorrect ratios distort class assignment.
- `add_table_class.log_path`: Invalid path hides diagnostics when tuning.

## Safe Edit Checklist
- Keep ratio thresholds ordered and logically consistent.
- Tune values with small batches first.
- Keep logging enabled while iterating.
- Inspect resulting HTML classes on representative notes.

## Field Reference

### `add_table_class`
- `apply_to_existing_classes`: Whether existing class attributes should still be processed.
- `log_path`: Log output location.

### `add_img_class`
- `small_width`: Width cutoff for small image logic.
- `ultra-wide_ratio`: Aspect ratio threshold for very wide images.
- `landscape_ratio_min`: Minimum ratio for landscape classification.
- `tall_ratio`: Threshold for portrait/tall classification.
- `square_min`, `square_max`: Bounds for square-like detection.

## Example

```json
{
  "add_table_class": {
    "apply_to_existing_classes": true,
    "log_path": "~/Desktop/anki_logs/Add_table_class_log.txt"
  },
  "add_img_class": {
    "small_width": 340,
    "ultra-wide_ratio": 1.9,
    "landscape_ratio_min": 1.19,
    "tall_ratio": 0.9,
    "square_min": 0.9,
    "square_max": 1.19
  }
}
```
