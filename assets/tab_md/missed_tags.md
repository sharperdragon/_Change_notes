# Missed Tags

## What This Tab Controls
This tab configures the canonical missed-question tagging flow, including rotation-aware tags and action groups.

## Key Sections
- `tag_missed_qid_notes` (canonical)

## High-risk Fields
- `rotation.schedule`: Invalid dates or overlapping windows can produce incorrect rotation tags.
- `actions.*.tags` / `actions.*.base_tags`: Wrong tag arrays can apply incorrect or broad tags.
- `actions.uworld.test_range_block_size`: Bad values can generate misleading bucket tags.
- `rotation.exhausted_policy`: Wrong fallback policy changes post-schedule behavior.

## Safe Edit Checklist
- Keep schedule dates in `YYYY-MM-DD` format.
- Keep all tag collections as arrays where expected.
- Verify action labels still make sense in Browser menu order.
- Save and run one missed-tag action on a small selected set.

## Compatibility Notes
Use canonical keys inside `tag_missed_qid_notes`; per-key legacy alias remapping is no longer applied at runtime.
Legacy section names are still merged into `tag_missed_qid_notes` by `ConfigManager`:
- `add_missed_tags`
- `tag_selected_notes_config`
- `add_tags`

## Field Reference

### `ui`
- `menu_label`: Root menu label.

### `rotation`
- `schedule`: Rotation blocks (`label`, `start`, `end`).
- `exhausted_policy`: Behavior when outside configured windows.
- `parent_tag_segment`: Parent rotation segment in final tags.
- `winter_break_label`: Winter-break window label.
- `post_rotation_label`: Post-rotation fallback label.

### `actions`
- `base`: Baseline missed tagging action.
- `uworld`: UWorld-specific tags and range grouping.
- `nbme`: NBME-specific tags.
- `amboss`: Amboss-specific tagging behavior.
- `multi_missed`: Re-missed marker.
- `key_info`: Key-info marker.
- `correct_guess`: Correct-guess marker with optional rotation context.
- `other`: Additional resource grouping.

## Partial Example

```json
{
  "tag_missed_qid_notes": {
    "ui": { "menu_label": "Missed Tags" },
    "rotation": {
      "exhausted_policy": "unknown",
      "parent_tag_segment": "Rotation"
    },
    "actions": {
      "base": {
        "label": "Base",
        "tags": ["##Missed-Qs"]
      },
      "uworld": {
        "label": "UWorld",
        "base_tags": ["##Missed-Qs::UW_Tests"],
        "default_tag_prefix": "UW_Tests",
        "test_range_block_size": 25
      }
    }
  }
}
```
