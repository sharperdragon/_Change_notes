 1. Current Architecture (diagnostic overview)

'''

# _Change_notes: Anki Add-on Suite for Tag, Note, and Media Management

## Summary
_Change_notes is a modular suite of advanced tools for managing tags, note types, scheduling, and media in Anki decks. It provides batch operations, fuzzy matching, deduplication, and merging utilities, all configurable via a centralized system. Designed for power users and developers, it streamlines large-scale collection maintenance and data hygiene tasks.

---

## Overview and Purpose

_Change_notes is built to address common pain points in large Anki collections:
- **Tag deduplication and merging**
- **Note type batch conversion**
- **Schedule merging**
- **Image and media management**
- **Bulk tag addition and manipulation**

The suite is highly modular, allowing users to run individual tools or combine them for complex workflows. Each tool is configurable through JSON files or a GUI, with robust logging for transparency and troubleshooting.

---

## Folder Structure

```
_Change_notes/
│
├── config.json
├── config_manager.py
├── config_ui.py
├── meta.json
├── mw_app.css
├── print_length.py
├── logs/
│   └── merge_tags/
│       └── ...            # Runtime logs per tool
│
├── modules/
│   ├── utils.py
│   ├── small_modules.py
│   ├── add_tags.py
│   ├── export_nids.py
│   ├── batch_Note_type_change.py
│   ├── change_note_types.py
│   ├── assets/
│   │   ├── scrub_match.py
│   │   ├── scrub_match_sched.py
│   │   └── text_replacements.txt
│   ├── configs/
│   │   ├── merge_tags_config.json
│   │   ├── tag_dupes_config.json
│   │   └── ...           # Configs per module
│   ├── logs/
│   ├── merge/
│   │   ├── merge_schedule.py
│   │   ├── merge_tags.py
│   │   ├── tag_dupes.py
│   │   ├── Mod_merge_imgs.py
│   │   ├── logic_merge_tags.py
│   │   ├── logic_merge_imgs.py
│   │   ├── combo_runner.py
│   │   └── logs/
│   ├── merge_images_AND_tags/
│   │   ├── combo_runner.py
│   │   └── __init__.py
│   ├── add_table_class/
│   │   ├── main.py
│   │   └── config_*
│   └── Add_img_class/
│       ├── larger_helper.py
│       ├── config_*
│       ├── logs/Add_img_class_log.txt
│       └── vendor/PIL/
```

---

## Core Module Descriptions

| Module                   | Purpose                                                                 | Key Features                                             |
|--------------------------|-------------------------------------------------------------------------|----------------------------------------------------------|
| **Tag Dupes**            | Identify and merge duplicate/near-duplicate tags                        | Fuzzy matching, user review, batch merge                 |
| **Merge Tags**           | Consolidate tags according to config or rules                           | Mapping, aliasing, undo support                          |
| **Merge Schedule**       | Merge scheduling information between notes (e.g., for sync/merge tasks) | Field mapping, conflict resolution, audit logs           |
| **Merge Images**         | Deduplicate and merge media/image references across notes               | Hashing, reference update, orphan cleanup                |
| **Batch Note Type Change**| Change note types in bulk based on mapping or rules                    | Field mapping, type safety, dry-run mode                 |
| **Add Tags**             | Add or manipulate tags across selected notes                            | Regex selection, batch add/remove, preview mode          |

Each core module is self-contained, with its own configuration and logging.

---

## Configuration System

The add-on uses a layered configuration system:
- **Global config** (`config.json`): Controls general behavior, UI options, and defaults.
- **Per-tool config** (`modules/configs/*.json`): Each tool has its own config for fine-grained control.

Configuration can be edited via:
- The built-in config GUI (`config_ui.py`)
- Direct JSON file editing

**Example `merge_tags_config.json`:**
```json
{
    "merge_map": {
        "biology": "science",
        "bio": "science",
        "chem": "science"
    },
    "fuzzy_threshold": 0.85,
    "dry_run": true,
    "log_path": "logs/merge_tags/merge_tags_run_2024-05-22.log"
}
```

---

## Usage Instructions

### For End Users
1. **Install** the add-on in your Anki `addons21/` directory.
2. **Configure** via the config GUI or edit JSON files as needed.
3. **Access** tools via the Anki Tools menu or add-on submenu.
4. **Run** the desired operation. Logs and dry-run previews are available for all destructive actions.
5. **Review logs** in the `logs/` directory for results and troubleshooting.

### For Developers
- Each tool is a Python module with a main entry point.
- Add new modules under `modules/`, with supporting config and logs as needed.
- Use shared utilities from `modules/utils.py` and `modules/small_modules.py`.
- Register new tools in the central menu handler (see `config_manager.py`).

---

## Logging and Output Structure

All tools write detailed logs to `logs/` or their module subfolders. Log files include:
- Timestamps and run metadata
- Dry-run vs. live mode
- Actions taken (e.g., merged tags, changed note types)
- Errors and warnings

**Example log path:**  
`logs/merge_tags/merge_tags_run_2024-05-22.log`

---

## Developer Notes: Adding New Tools

1. **Create a new module** under `modules/`, following the structure of existing tools.
2. **Add a config file** in `modules/configs/`.
3. **Implement logging** to a dedicated subfolder in `logs/`.
4. **Register the tool** in the menu/UI system via `config_manager.py`.
5. **Document** the tool in this README and in the module docstring.
6. **(Optional)** Add GUI elements to `config_ui.py` for user configuration.

**Tip:** Use utility functions from `modules/utils.py` to maintain consistency.

---

## Compatibility Notes

- **Anki Version:** Designed for Anki 2.1.50 and above (Qt5/Qt6 compatible).
- **Platform:** Windows, macOS, Linux.
- **Conflicts:** Avoid running with other tag/note-type manipulation add-ons simultaneously.
- **Backups:** Always back up your collection before running batch operations.

---

## Submodules

### Add_img_class
Located at: `modules/Add_img_class/`

- **Purpose:** Advanced image manipulation and classification for note fields.
- **Features:** Image resizing, format conversion, integration with PIL (Python Imaging Library).
- **Config:** `config_*` files for image settings.
- **Log:** `logs/Add_img_class_log.txt`

### add_table_class
Located at: `modules/add_table_class/`

- **Purpose:** Adds or modifies table structures in note fields.
- **Features:** Table formatting, field mapping, batch conversion.
- **Config:** `config_*` files for table settings.

---

## Versioning and Credits

- **Version:** 1.0.0
- **Author:** [Your Name or Team]
- **Credits:**  
  - PIL (Python Imaging Library) for image processing (bundled in `vendor/PIL/`)
  - Anki and the Anki add-on community

**License:** MIT or GPLv3 (choose as appropriate)

---

For bug reports or feature requests, please open an issue or submit a pull request.