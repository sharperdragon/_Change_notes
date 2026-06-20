# Custom Tags

## What This Tab Controls
This tab configures preset tag actions shown in the Browser context menu.

## Key Sections
- `custom_tags_config.add_custom_tags_<n>` (any numbered section, such as `_1`, `_2`, `_3`)

## High-risk Fields
- `custom_tags_config.add_custom_tags_<n>.presets`: Invalid shape (missing `label` or invalid `tags`) breaks menu actions.
- `custom_tags_config.add_custom_tags_<n>.menu_label`: Frequent renames can make menu navigation inconsistent.
- `custom_tags_config.add_custom_tags_<n>.group_labels`: Keys not matching `presets[].group` will not affect submenu labels.
- `custom_tags_config.add_custom_tags_<n>.presets`: If empty, that menu stays hidden.

## Safe Edit Checklist
- Keep `presets` as an array of objects.
- For each preset, keep `label` as a string and `tags` as a string array.
- Save and test from Browser on a small selected note set.

## Field Reference

### Per menu section
- `menu_label`: Root menu label for custom tag presets.
- `group_labels`: Optional map from group key to displayed submenu label.
- `presets`: Preset definitions.

All numbered `add_custom_tags_<n>` sections use the same fields and are shown in ascending numeric order.

No-selection and success toast messages are hardcoded in code and not editable in config.

### Preset item
- `label`: Menu label shown to the user.
- `group` (optional): Single submenu bucket for related presets.
- `tags`: Array of tags applied to selected notes.

## Example

```json
{
  "custom_tags_config": {
    "add_custom_tags_1": {
      "menu_label": "Custom Tags",
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
    },
    "add_custom_tags_2": {
      "menu_label": "Custom Tags 2",
      "group_labels": {},
      "presets": []
    },
    "add_custom_tags_3": {
      "menu_label": "Custom Tags 3",
      "group_labels": {},
      "presets": []
    }
  }
}
```
