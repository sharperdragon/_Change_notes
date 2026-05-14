# Missed Tags

## What This Tab Controls
This tab configures the canonical missed-question tagging flow, including rotation-aware tags and action groups.

## Key Sections
- `tag_missed_notes` (canonical)

## High-risk Fields
- `rotation.schedule`: Invalid dates or overlapping windows can produce incorrect rotation tags.
- `actions.*.tag_segment` / `actions.*.absolute_tags`: Wrong tag targets can apply incorrect or broad tags.
- `actions.*.prompt`: Incorrect prompt kind/style can produce unexpected tag paths.
- `actions.uworld.prompt.parent_range_block_size`: Bad values can generate incorrect top-level UWorld buckets.
- `actions.uworld.prompt.range_block_size`: Bad values can generate incorrect second-level UWorld buckets.
- `rotation.exhausted_policy`: Wrong fallback policy changes post-schedule behavior.

## Safe Edit Checklist
- Keep schedule dates in `YYYY-MM-DD` format.
- Keep `absolute_tags` as arrays when used.
- Verify action labels still make sense in Browser menu order.
- Save and run one missed-tag action on a small selected set.

## Compatibility Notes
Use canonical keys inside `tag_missed_notes`.
Standardized action keys are normalized at runtime so existing behavior remains compatible.
Legacy section names are still merged into `tag_missed_notes` by `ConfigManager`:
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
- Shared standardized keys:
- `menu_label`: Action label shown in the menu.
- `child_of_primary_missed`: Build tags under the main missed root when `true`.
- `tag_segment`: Segment used under the missed root.
- `absolute_tags`: Full tags for actions that should not be child tags.
- `add_missed_date_context`: Include date context tags for the action.
- `prompt.kind`: `none`, `number`, or `form`.
- `prompt.number_style`: `number_only`, `range_then_number`, `rotation_then_number`.
- UWorld-specific prompt keys:
- `prompt.parent_range_block_size`: Parent range width (for example, `50` gives `001-050`).
- `prompt.range_block_size`: Child range width (for example, `5` gives `01-05`).
- `correct_tag_missed`: source-selector action for `UW Correct + Missed Tag`; uses shared keys such as `menu_label`, `tag_segment`, and `add_missed_date_context`.
- `other` supports:
- `submenu_bool`: when `true`, render other-resource actions under a dedicated submenu.
- `submenu_label`: submenu title used when `submenu_bool` is enabled.
- `tagging`: shared tagging behavior for other resources.
- `actions`: list of extra resource actions with the same standardized action keys.

## Partial Example

```json
{
  "tag_missed_notes": {
    "ui": { "menu_label": "Missed Tags" },
    "rotation": {
      "exhausted_policy": "unknown",
      "parent_tag_segment": "Rotation"
    },
    "actions": {
      "base": {
        "menu_label": "♦️ Base",
        "child_of_primary_missed": false,
        "absolute_tags": ["##Missed-Qs"],
        "add_missed_date_context": false
      },
      "uworld": {
        "menu_label": "🗺️ UWorld",
        "child_of_primary_missed": true,
        "tag_segment": "*UW_Tests",
        "add_missed_date_context": true,
        "prompt": {
          "kind": "number",
          "number_style": "range_then_number",
          "parent_range_block_size": 50,
          "range_block_size": 5
        }
      },
      "correct_tag_missed": {
        "menu_label": "UW Correct + Missed Tag",
        "child_of_primary_missed": true,
        "tag_segment": "correct_marked",
        "add_missed_date_context": true
      },
      "amboss": {
        "menu_label": "🦠 Amboss",
        "child_of_primary_missed": true,
        "tag_segment": "Amboss",
        "add_missed_date_context": true,
        "prompt": {
          "kind": "number",
          "number_style": "number_only"
        }
      }
    }
  }
}
```
