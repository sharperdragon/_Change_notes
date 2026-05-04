# add_table_class Configuration Notes

This module classifies selected-note HTML tables and adds `two-cols` to 2-column tables.

## Runtime Config Source

Settings are read from the root add-on `config.json` section:

```json
"add_table_class": {
  "apply_to_existing_classes": true,
  "log_path": "~/Desktop/anki_logs/Add_table_class_log.txt"
}
```

## Settings

- `apply_to_existing_classes`
  - `true`: tables with existing class attributes are still processed.
  - `false`: tables that already have any class are skipped.
- `log_path`: output path for run diagnostics.

## Behavior Notes

- Tables with class `no-auto-class` are always skipped.
- Only tables detected as exactly 2 columns in the first row are updated.
