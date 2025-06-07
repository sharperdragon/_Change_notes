# 🔄 Change Notes Add-on: Configuration Guide

This document explains the settings in `config.json` for the **Change Notes** add-on, which includes batch note type conversion, tag merging, and optional UI overrides.

---

## 🔧 Core Settings

| Key                           | Description                                                                 |
|--------------------------------|-----------------------------------------------------------------------------|
| `hide_menu_when_one_type_selected` | Hides the note type dropdown if there's only one type in the current context. | `false` by default. |
| `allow_single_type_override`  | Allows the user to override the only detected note type and manually select another. | Helpful for correcting misidentified notes. |
| `last_target_model`           | Stores the last selected model name to auto-populate the target note type field. | Example: `*Nord+` |
| `last_mapping_profile`        | Stores the name of the last field-mapping profile used, so it can be restored on reopen. | Default: `""` |

---

## 🗺️ Field Mapping

| Key            | Description |
|----------------|-------------|
| `field_mappings` | A dictionary mapping source fields to target fields. You can define preset mappings to accelerate batch note changes. |
| **Example**     | ```json\n"field_mappings": {\n  "Text": "Front",\n  "Extra": "Back"\n}\n``` |

---

## ⚙️ Batch Processing

| Key          | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| `batch_size` | Number of notes processed per batch. Adjust if you're hitting performance or timeout issues. |
| `show_progress` | If `true`, a progress bar will be shown during the batch conversion. |

---

## 📌 Example Config

```json
{
    "hide_menu_when_one_type_selected": false,
    "allow_single_type_override": true,
    "last_target_model": "*Nord+",
    "field_mappings": {
        "Text": "Front",
        "Extra": "Back"
    },
    "batch_size": 200,
    "show_progress": true,
    "last_mapping_profile": "Basic_to_Nord"
}
# 🛠️ Change Notes Add-on: Complete Configuration Guide

This guide documents all configuration blocks inside `config.json`, used by the Change Notes Add-on Suite. These include batch note-type conversion, fuzzy tag merging, duplicate detection, and cleanup utilities.

Each config block may merge with global defaults (`global_config`) during runtime.

---

## 🌐 `global_config`

**Applies to**: All modules

| Key                | Description                                                    | Example         |
|---------------------|----------------------------------------------------------------|------------------|
| `default_fuzzy`     | Default similarity threshold for fuzzy matching (`0–1.0`)     | `"0.99"`         |
| `default_note_type` | Default model name fallback                                   | `"*Nord+"`       |
| `log_folder`        | Default folder for logs and outputs                           | `"logs"`         |

---

## 🔁 `batch_note_change_config`

**Applies to**: Batch note type conversion and field mapping

| Key                              | Description                                                           | Example                  |
|----------------------------------|-----------------------------------------------------------------------|---------------------------|
| `hide_menu_when_one_type_selected` | Hide dropdown if only one note type is found                         | `false`                   |
| `allow_single_type_override`     | Allow override when only one note type exists                         | `true`                    |
| `last_target_model`              | Last selected model for dropdown                                      | `"*Nord+"`                |
| `field_mappings`                 | Field map: source field → target field                                | `{ "Text": "Front" }`     |
| `batch_size`                     | Notes processed per batch                                             | `200`                     |
| `show_progress`                  | Show a progress bar during conversion                                 | `true`                    |
| `last_mapping_profile`           | Last saved mapping profile name                                       | `""`                      |
| `auto_confirm_mappings`          | Automatically accept field mappings                                   | `false`                   |
| `tag_on_change`                  | Tag applied to updated notes                                          | `"NoteType::Changed"`     |
| `enable_backup`                  | Backup notes before changes                                           | `true`                    |
| `backup_directory`               | Directory where backups are saved                                     | `"~/Anki_Backups/NoteTypeChange"` |

---

## 🧠 `merge_tags_config`

**Applies to**: Fuzzy grouping of similar notes and merging their tags

| Key            | Description                                                         | Example        |
|----------------|---------------------------------------------------------------------|----------------|
| `default_fuzzy`| Similarity threshold to group notes                                 | `"0.99"`       |
| `base_tag`     | Base tag prefix for grouped notes                                   | `"TAGS_MERGED"`|
| `log_folder`   | Log directory override (fallback to global if empty)                | `""`           |

---

## 📌 `tag_dupes_config`

**Applies to**: Fuzzy matching and tagging of near-duplicate notes

| Key              | Description                                                        | Example         |
|------------------|--------------------------------------------------------------------|------------------|
| `comparison_field`| Note field to use for comparison                                  | `"Text"`         |
| `base_tag`        | Base tag applied to matched groups                                | `"Main_dupe"`    |
| `multi_tag_child` | Extra tag for groups of 3+ notes                                  | `"multiple"`     |
| `TAG UNMATCHED`   | If `"true"`, adds tag to unmatched notes                          | `"true"`         |
| `unmatched_tag`   | Tag applied to unmatched notes                                     | `"unmatched"`    |
| `log_folder`      | Log folder (empty means fallback to global setting)               | `""`             |

---

## 🚫 `delete_unused_config`

**Applies to**: Safe deletion / cleanup behavior

| Key              | Description                                                        | Example                          |
|------------------|--------------------------------------------------------------------|----------------------------------|
| `protected_notes`| List of model names to exclude from deletion or processing         | `["*Nord+", "*Nord-focus+"]`     |

---

## 🧪 Full Example

```json
{
  "global_config": {
    "default_fuzzy": "0.99",
    "default_note_type": "*Nord+",
    "log_folder": "logs"
  },
  "batch_note_change_config": {
    "hide_menu_when_one_type_selected": false,
    "allow_single_type_override": true,
    "last_target_model": "*Nord+",
    "field_mappings": {
      "Text": "Front",
      "Extra": "Back"
    },
    "batch_size": 200,
    "show_progress": true,
    "last_mapping_profile": "",
    "auto_confirm_mappings": false,
    "tag_on_change": "NoteType::Changed",
    "enable_backup": true,
    "backup_directory": "~/Anki_Backups/NoteTypeChange"
  },
  "merge_tags_config": {
    "default_fuzzy": "0.99",
    "base_tag": "TAGS_MERGED",
    "log_folder": ""
  },
  "tag_dupes_config": {
    "comparison_field": "Text",
    "base_tag": "Main_dupe",
    "multi_tag_child": "multiple",
    "TAG UNMATCHED": "true",
    "unmatched_tag": "unmatched",
    "log_folder": ""
  },
  "delete_unused_config": {
    "protected_notes": ["*Nord+", "*Nord-focus+"]
  }
}
```