# _Change_notes: Advanced Anki Add-on Suite for Tag, Note, and Media Management

## Introduction

_Change_notes is a powerful, modular add-on suite designed to enhance and streamline the management of Anki collections at scale. It provides a comprehensive set of tools focused on tag deduplication and merging, note type batch conversion, schedule merging, media handling, and bulk tag operations. Built with flexibility and extensibility in mind, _Change_notes caters both to power users looking to maintain large decks efficiently and developers aiming to extend its capabilities.

The add-on emphasizes explicit workflows, detailed logging, and configurable behavior through JSON files or a GUI interface. It supports complex operations such as fuzzy matching for tags, conflict resolution in scheduling data, and media deduplication, all while maintaining data integrity and offering dry-run previews.

---

## Overview

_Change_notes addresses common pain points encountered when managing large Anki collections, including but not limited to:

- Deduplicating and merging tags with fuzzy matching and user confirmation.
- Batch conversion of note types with field mapping and validation.
- Merging scheduling data to maintain consistent learning progress across notes.
- Managing images and media references to reduce redundancy.
- Adding, removing, or modifying tags in bulk with regex support.

Each tool is designed as a standalone module yet integrates seamlessly into the suite, allowing users to combine operations into complex workflows. The configuration system supports global and per-tool settings, enabling tailored behavior for different collections or use cases.

---

## Workflows

### Typical User Workflow

1. **Backup First:** Always create a backup of your Anki collection before running any batch operations.
2. **Configure Tools:** Use the config GUI or edit JSON files to set up your desired operations (e.g., tag merge maps, note type mappings).
3. **Dry-Run Mode:** Run tools in dry-run mode to preview changes without affecting your collection.
4. **Review Logs:** Examine detailed logs generated during dry runs to verify planned changes.
5. **Execute Changes:** Run the tools in live mode to apply changes to your collection.
6. **Validate Results:** Inspect your collection to ensure changes applied correctly and as expected.
7. **Combine Tools:** For complex maintenance, chain multiple tools using provided combo runners or scripts.

### Developer Workflow

1. **Add Modules:** Create new Python modules under `modules/` following existing patterns.
2. **Create Configs:** Add configuration JSON files in `configs/`.
3. **Implement Logging:** Ensure detailed logs are written in dedicated subfolders under `logs/`.
4. **Register Tools:** Update menu and UI registration in `__init__.py` and the target module(s).
5. **Document:** Provide module docstrings and update this README with new tool descriptions.
6. **Test:** Use dry-run modes and logging to verify correctness before release.

---

## Naming Conventions and File Structure

- **Modules:** Named with lowercase and underscores (e.g., `merge_tags.py`), grouped by functionality.
- **Configs:** JSON files named with tool identifiers and `_config.json` suffix (e.g., `merge_tags_config.json`).
- **Logs:** Stored under `logs/` with subfolders per module, log files named with timestamps (e.g., `merge_tags_run_YYYY-MM-DD.log`).
- **Assets:** Static resources like text replacements or helper scripts are stored in `modules/assets/`.
- **Submodules:** Organized as subfolders with `__init__.py` for package recognition.

This consistent naming and organization facilitate easy navigation, maintenance, and extension of the add-on suite.

---

## Folder Structure

```text
_Change_notes/
│
├── README.md
├── __init__.py
├── meta.json
├── config.json
├── config.md
├── config_manager.py
├── config_ui.py
│
├── configs/                               # Default source for per-module config sections
│   ├── add_custom_tags.json
│   ├── tag_missed_qid_notes.json          # Canonical missed-tags section
│   ├── add_missed_tags.json               # Legacy missed-tags compatibility
│   └── add_tags.json                      # Legacy compatibility defaults
│
├── logs/
│
└── modules/
    ├── utils.py
    ├── merge_utils.py
    ├── add_custom_tags.py
    ├── add_missed_tags.py
    ├── change_note_types.py
    ├── del_empty_notes.py
    ├── export_nids.py
    ├── export_UW_qid_tags.py
    ├── img_tags_merge.py
    ├── merge_imgs.py
    ├── merge_schedule.py
    ├── merge_tags.py
    └── tag_dupes.py
    │
    ├── logs/
    │
    ├── assets/
    │   ├── merge_utils.py
    │   ├── scrub_match.py
    │   ├── scrub_match_sched.py
    │   └── text_replacements.txt
    │
    ├── Add_img_class/
    │   ├── config_manager.py
    │   ├── config_ui.py
    │   ├── config.json
    │   ├── config.md
    │   ├── larger_helper.py
    │   ├── larger_imgs.txt
    │   ├── logs/
    │   └── vendor/
    │
    └── add_table_class/
        ├── config_manager.py
        ├── config_ui.py
        ├── config.json
        ├── config.md
        └── main.py
```

---

## Core Module Descriptions

| Module                    | Purpose                                                                 | Key Features                                                      |
|---------------------------|-------------------------------------------------------------------------|-------------------------------------------------------------------|
| **Tag Dupes**             | Identify and merge duplicate or near-duplicate tags                     | Fuzzy matching, user review, batch merge                          |
| **Merge Tags**            | Consolidate tags based on mapping or rules                              | Mapping, aliasing, undo support                                   |
| **Merge Schedule**        | Merge scheduling data between notes (for sync or merge tasks)           | Field mapping, conflict resolution, audit logs                    |
| **Merge Images**          | Deduplicate and merge media/image references across notes               | Hashing, reference update, orphan cleanup                         |
| **Batch Note Type Change**| Change note types in bulk using mappings or rules                       | Field mapping, type safety, dry-run mode                          |
| **Add Missed Tags**       | Add missed-question tags from context menu actions                      | Rotation/month-aware tagging, source-specific presets             |
| **Add Custom Tags**       | Add user-defined preset tags from a dedicated context submenu           | Config-driven labels/tags, batch apply to selected notes          |
| **Add_img_class**         | Advanced image manipulation and classification within note fields       | PIL-backed processing, normalization, detailed logging            |
| **add_table_class**       | Structured table insertion and modification in note fields              | HTML/Markdown tables, batch-safe operations, configurable layouts |

## Internal Support Packages

- `utils/` – shared helpers and safety checks  
- `assets/` – static resources and scrub/replace rules  
- `merge_utils.py` – shared merge logic (tags/images/schedule)

Each module includes configuration files and produces detailed logs to facilitate auditing and troubleshooting.

---

## Configuration System

_Change_notes employs a layered configuration approach to maximize flexibility:

- **Global Configuration (`config.json`):** Controls overall add-on behavior, UI settings, and default options.
- **Tool-specific Configuration (`configs/*.json`):** Fine-tunes individual tool behavior such as merge maps, thresholds, and dry-run settings.
- **Custom Tag Presets (`add_custom_tags` section):** Defines the top-level Custom Tags submenu label and tag presets.
- **Missed Tags (`tag_missed_qid_notes` section):** Canonical source for missed-tag UI labels/messages and base defaults, with legacy merge support from `add_missed_tags`, `add_tags`, and `tag_selected_notes_config`.

Configuration can be edited using:

- The built-in configuration GUI (`config_ui.py`) for interactive adjustment.
- Direct editing of JSON files for advanced customization.

**Example of `merge_tags_config.json`:**

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

**Example of `add_custom_tags` section:**

```json
{
  "submenu_label": "Custom Tags",
  "presets": [
    {
      "label": "ADRs",
      "tags": ["#Custom::Bugs+Drugs::Drugs::ADRs"]
    },
    {
      "label": "DO_Med",
      "tags": ["#Custom::DO_Med"]
    }
  ]
}
```

Custom-tag no-selection and success messages are hardcoded in `modules/add_custom_tags.py` and are not configurable.

**Example of `tag_missed_qid_notes` UI overrides:**

```json
{
  "tag_missed_qid_notes": {
    "ui": {
      "menu_label": "Missed Tags ❌",
      "message_invalid_test_number": "❌ Please enter a valid integer test number."
    }
  }
}
```

---

## Usage Instructions

### For End Users

1. **Install** the add-on by placing it in your Anki `addons21/` directory.
2. **Backup** your collection before running batch operations.
3. **Configure** tools via the configuration GUI or by editing the JSON config files.
4. **Access** the tools through the Anki Tools menu or the add-on submenu.
5. **Run** tools in dry-run mode initially to preview changes without modifying data.
6. **Review logs** located in the `logs/` directory to verify intended actions.
7. **Execute** the operation in live mode to apply changes.
8. **Validate** your collection post-operation to ensure correctness.

### For Developers

- Develop new modules under `modules/` with clear separation of concerns.
- Add configuration files in `configs/`.
- Implement detailed logging for transparency.
- Register new tools in the menu system via `__init__.py` and module menu hook functions.
- Update this README with documentation for new modules.
- Use shared utilities from `modules/utils.py` and `modules/shared/`.
- Test thoroughly with dry-run modes before deployment.

---

## Logging and Output Structure

All tools generate detailed logs stored under the `logs/` directory or their respective module subfolders. Logs include:

- Run timestamps and metadata.
- Dry-run vs. live mode indicators.
- Detailed actions performed (e.g., tags merged, note types changed).
- Errors, warnings, and informational messages.

**Example log file path:**  
`logs/merge_tags/merge_tags_run_2024-05-22.log`

---

## Versioning and Credits

- **Version:** 1.0.0
- **Author:** [Your Name or Team]
- **Credits:**  
  - PIL (Python Imaging Library) for image processing (bundled in `vendor/PIL/`)
  - Anki and the Anki add-on community

**License:** MIT or GPLv3 (choose as appropriate)

---

## Support and Contributions

For bug reports, feature requests, or contributions:

- Open an issue on the repository.
- Submit pull requests with clear descriptions and tests.
- Follow coding and documentation standards consistent with existing modules.

---

Thank you for using _Change_notes. We hope it makes managing your Anki collections easier and more efficient.
