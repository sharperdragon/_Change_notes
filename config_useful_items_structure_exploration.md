# Useful Config Items: Structure Exploration

Date: 2026-04-26

This file explores whether useful config items should remain section-local, move to top-level admin variables, or move under a global config namespace.

## Scope

- Includes only items previously classified as **useful config items**.
- Focuses on structure and maintainability, not behavior changes.

## Decision Heuristic

- Keep section-local when a key controls one workflow only.
- Prefer top-level admin variables for organization/menu/tag taxonomy choices that rarely change and represent policy.
- Prefer global nesting when the same concept appears across multiple modules (for example, shared threshold defaults or shared logging preferences).

## High-Confidence Keep Section-Local

### `merge_tags_config`

- `comparison_field`
- `default_fuzzy`
- `min_fuzzy`
- `ask_fuzzy_each_time`
- `base_tag`
- `merge_select_only`
- `merge_only_parents`
- `excluded_tags`

Reason: tightly coupled to one workflow (tag merge) and its UX.

### `tag_dupes_config`

- `comparison_field`
- `base_tag`
- `multi_tag_child`
- `tag_unmatched`
- `unmatched_tag`
- `log_folder`

Reason: duplicate-tagging behavior is module-specific and intentionally separate from merge behavior.

### `merge_scheduling`

- `merge_similarity_threshold`
- `merge_field_index`
- `multi_card_policy`
- `tag_on_merge`
- `abort_on_cancel`

Reason: scheduling merge has unique semantics and policy controls not shared by other modules.

### `merge_images_config`

- `default_threshold`
- `min_threshold`
- `ask_threshold_each_time`
- `fields_to_scan_for_images`
- `excluded_tags`
- `merge_behavior.*`
- `logging.*`
- `tagging.*`

Reason: image merge behavior is dense and highly workflow-specific; local grouping aids clarity.

## Plausible Top-Level Admin Variable Candidates

These can remain in section config, but are plausible to centralize as top-level admin policy variables if you want fewer nested edits.

- Taxonomy/menu/policy-heavy keys:
  - `delete_empty_notes_config.protected_notes`
  - `add_custom_tags.*`
  - `add_custom_tags_2.*`
  - `tag_missed_qid_notes.*`
  - `add_img_class.*`
  - `add_table_class.log_path`

Rationale:
- These define content taxonomy, labels, and house style rather than algorithm tuning.
- Admins often want these in one obvious place.

Tradeoff:
- Moving them top-level can reduce discoverability by feature area unless well documented.

## Plausible `global_config` Nesting Candidates

These are useful keys that could be normalized under a shared global subtree with per-module overrides.

- Already-global fuzzy controls:
  - `global_config.fuzzy_opts.default_fuzz`
  - `global_config.fuzzy_opts.min_fuzz`

- Possible extensions:
  - shared threshold UX defaults for `merge_tags_config` and `merge_images_config`
  - shared prompt behavior defaults (`ask_*_each_time` style)
  - shared logging visibility defaults (`logging.enable_log_popup`, `logging.save_log_to_desktop`)

Rationale:
- Reduces repeated patterns across modules.
- Supports a clean default/override model.

Tradeoff:
- Global nesting can hide local intent and increase “why is this value applied?” confusion unless override precedence is explicit.

## Practical Recommendation

- Keep workflow-specific algorithm controls section-local.
- Optionally centralize admin policy/taxonomy keys (menus, tags, protected lists) if your main goal is a single admin surface.
- If you introduce more shared defaults, adopt:
  - `global_config.<domain>.defaults`
  - `module_config.<key>` overrides that win over global defaults.
