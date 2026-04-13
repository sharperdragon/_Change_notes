# Custom Tags

## What This Tab Controls
This tab configures preset tag actions shown in the Browser context menu.

## Key Sections
- `add_custom_tags`

## High-risk Fields
- `add_custom_tags.presets`: Invalid shape (missing `label` or invalid `tags`) breaks menu actions.
- `add_custom_tags.submenu_label`: Frequent renames can make menu navigation inconsistent.
- `add_custom_tags.group_labels`: Keys not matching `presets[].group` will not affect submenu labels.

## Safe Edit Checklist
- Keep `presets` as an array of objects.
- For each preset, keep `label` as a string and `tags` as a string array.
- Save and test from Browser on a small selected note set.

## Field Reference

### Top-level
- `submenu_label`: Root menu label for custom tag presets.
- `group_labels`: Optional map from group key to displayed submenu label.
- `presets`: Preset definitions.

No-selection and success toast messages are hardcoded in code and not editable in config.

### Preset item
- `label`: Menu label shown to the user.
- `group` (optional): Single submenu bucket for related presets.
- `tags`: Array of tags applied to selected notes.

## Example

```json
{
  "add_custom_tags": {
    "submenu_label": "Custom Tags",
    "group_labels": {
      "Drugs": "💊 Drugs"
    },
    "presets": [
      {
        "label": "ADRs",
        "group": "Drugs",
        "tags": ["#Custom::Bugs+Drugs::Drugs::ADRs"]
      },
      {
        "label": "DO_Med",
        "tags": ["#Custom::DO_Med"]
      }
    ]
  }
}
```
