# pyright: reportMissingImports=false
from __future__ import annotations

import re

from aqt.qt import QAction, QMenu
from aqt.utils import showInfo, tooltip

from .missed_tags_config import (
    MissedTagsConfig,
    OtherResourceActionConfig,
    PromptActionConfig,
    _to_bool,
    load_runtime_config,
)
from .missed_tags_constants import (
    ACTION_KEY_CORRECT_TAG_MISSED_PROMPT,
    AMBOSS_APPEND_CORRECT_MARKED_DEFAULT,
    AMBOSS_CORRECT_MARKED_TAG_SEGMENT,
    CORRECT_MARKED_TAG_SEGMENT,
    DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL,
    MSG_INVALID_CORRECT_GUESS_SUBTAG,
    MSG_INVALID_CORRECT_MARKED_SOURCE_INPUT,
    MSG_INVALID_INTEGER_TEST_NUMBER,
    MSG_INVALID_NBME_INPUT,
    MSG_NO_NOTES_SELECTED,
    PROMPT_BEHAVIOR_BASE_ONLY,
    PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
    PROMPT_CORRECT_GUESS_SUBTAG_LABEL,
    PROMPT_CORRECT_GUESS_SUBTAG_TITLE,
    PROMPT_CORRECT_MARKED_CHECKBOX_LABEL,
    PROMPT_DEFAULT_LABEL,
    PROMPT_DEFAULT_TITLE,
    PROMPT_KIND_FORM,
    PROMPT_KIND_NONE,
    PROMPT_KIND_NUMBER,
    PROMPT_STYLE_NUMBER_ONLY,
    PROMPT_STYLE_RANGE_THEN_NUMBER,
    PROMPT_STYLE_ROTATION_THEN_NUMBER,
    PROMPT_TRUE_LEARN_TITLE,
)
from .missed_tags_prompts import (
    _correct_marked_checkbox_state_key,
    _get_saved_prompt_input,
    _positioned_text_prompt,
    _positioned_text_prompt_with_checkbox,
    _prompt_correct_missed_source_and_input,
    _save_prompt_input,
)
from .missed_tags_tag_utils import (
    _append_tag_segment,
    _extract_tag_suffix,
    _format_uworld_test_tag,
    _nbme_base_tag,
    _normalize_freeform_tag_path,
    _normalize_nbme_child_path,
    _normalize_uworld_child_tag_path,
    _resolved_base_tag,
    _should_add_missed_date_context,
    _uw_base_tag,
    base_tag_path,
    get_correct_guess_tags,
    get_current_or_next_rotation_meta,
    get_formatted_rotation_segment,
    get_missed_month_tag,
    get_missed_tag_for_rotation,
    get_rotation_key_info_tag,
    scrub_resource_label_to_tag,
)
from .shared.menu_styles import build_missed_tags_menu_stylesheet

def _add_tag_safe(note, tag: str):
    if hasattr(note, "add_tag"):
        note.add_tag(tag)
    else:
        note.addTag(tag)


def _save_note_safe(col, note):
    try:
        col.update_note(note)
    except Exception:
        note.flush()


def apply_tags_to_selected_notes(
    browser,
    tag_list: list[str],
    action_key: str,
    cfg: MissedTagsConfig | None = None,
):
    runtime_cfg = cfg or load_runtime_config()

    col = browser.mw.col
    nids = browser.selectedNotes()
    if not nids:
        return

    final = list(tag_list or [])
    rotation_warning = ""
    if _should_add_missed_date_context(runtime_cfg, action_key):
        rotation_tag, rotation_warning = get_missed_tag_for_rotation(runtime_cfg)
        final.append(rotation_tag)
        final.append(get_missed_month_tag(runtime_cfg))

    seen = set()
    final_tags = []
    for tag in final:
        if tag and tag not in seen:
            seen.add(tag)
            final_tags.append(tag)

    for nid in nids:
        note = col.get_note(nid)
        current = set(note.tags)
        for tag in final_tags:
            if tag not in current:
                _add_tag_safe(note, tag)
        _save_note_safe(col, note)

    browser.model.reset()
    msg = f"✅ Applied {len(final_tags)} tags to {len(nids)} notes."
    if rotation_warning:
        msg += f"\n⚠️ {rotation_warning}"
    tooltip(msg)


def _ensure_selected_notes(browser) -> bool:
    if browser.selectedNotes():
        return True
    showInfo(MSG_NO_NOTES_SELECTED)
    return False


def _add_prompt_action(
    browser,
    menu,
    *,
    label: str,
    cfg: MissedTagsConfig,
    base_tags: list[str],
    action_key: str,
    title: str,
    prompt_label: str,
    blank_behavior: str,
    number_style: str,
    pad_label: bool = True,
    allow_freeform_child_segments: bool = False,
    include_rotation_for_freeform: bool = True,
    show_correct_marked_checkbox: bool = False,
) -> None:
    action_text = f"{label:<24}" if pad_label else label
    action = QAction(action_text, browser)
    action.triggered.connect(
        make_test_prompt_handler(
            browser,
            cfg,
            base_tags,
            action_key=action_key,
            title=title,
            label=prompt_label,
            blank_behavior=blank_behavior,
            number_style=number_style,
            allow_freeform_child_segments=allow_freeform_child_segments,
            include_rotation_for_freeform=include_rotation_for_freeform,
            show_correct_marked_checkbox=show_correct_marked_checkbox,
        )
    )
    menu.addAction(action)


def _add_form_prompt_action(
    browser,
    menu,
    *,
    label: str,
    cfg: MissedTagsConfig,
    base_tags: list[str],
    action_key: str,
    title: str,
    prompt_label: str,
    pad_label: bool = True,
    show_correct_marked_checkbox: bool = False,
) -> None:
    action_text = f"{label:<24}" if pad_label else label
    action = QAction(action_text, browser)

    def on_trigger():
        saved_form_value = _get_saved_prompt_input(action_key)
        append_correct_marked = False
        checkbox_state_key = ""
        if show_correct_marked_checkbox:
            checkbox_state_key = _correct_marked_checkbox_state_key(action_key)
            saved_append_state = _get_saved_prompt_input(checkbox_state_key)
            default_append_state = _to_bool(saved_append_state, AMBOSS_APPEND_CORRECT_MARKED_DEFAULT)
            form_value, append_correct_marked, ok = _positioned_text_prompt_with_checkbox(
                browser,
                title=title,
                label=prompt_label,
                default_text=saved_form_value,
                checkbox_label=PROMPT_CORRECT_MARKED_CHECKBOX_LABEL,
                checkbox_checked=default_append_state,
            )
        else:
            form_value, ok = _positioned_text_prompt(
                browser,
                title,
                prompt_label,
                default_text=saved_form_value,
            )
        if not ok:
            return
        if checkbox_state_key:
            _save_prompt_input(checkbox_state_key, "1" if append_correct_marked else "0")

        form_value = (form_value or "").strip()
        if form_value == "":
            _save_prompt_input(action_key, "")
            showInfo(MSG_INVALID_NBME_INPUT)
            return

        nbme_child_path = _normalize_nbme_child_path(form_value)
        if not nbme_child_path:
            showInfo(MSG_INVALID_NBME_INPUT)
            return
        _save_prompt_input(action_key, form_value)

        if not _ensure_selected_notes(browser):
            return
        resolved_base_tags = [str(tag).strip() for tag in base_tags if str(tag).strip()]
        if not resolved_base_tags:
            return
        formatted_tags = [f"{tag}::{nbme_child_path}" for tag in resolved_base_tags]
        if append_correct_marked:
            formatted_tags = [
                _append_tag_segment(tag, AMBOSS_CORRECT_MARKED_TAG_SEGMENT) for tag in formatted_tags
            ]
        apply_tags_to_selected_notes(browser, formatted_tags, action_key=action_key, cfg=cfg)

    action.triggered.connect(on_trigger)
    menu.addAction(action)


def _add_schema_driven_action(
    browser,
    menu,
    *,
    label: str,
    cfg: MissedTagsConfig,
    tags: list[str],
    action_key: str,
    prompt_cfg: PromptActionConfig,
    pad_label: bool = True,
) -> None:
    resolved_tags = [str(tag).strip() for tag in tags if str(tag).strip()]
    if not resolved_tags:
        return

    if prompt_cfg.kind == PROMPT_KIND_NONE:
        action_label = f"{label:<24}" if pad_label else label
        add_static_action(browser, menu, action_label, resolved_tags, action_key=action_key, cfg=cfg)
        return

    if prompt_cfg.kind == PROMPT_KIND_FORM:
        _add_form_prompt_action(
            browser,
            menu,
            label=label,
            cfg=cfg,
            base_tags=resolved_tags,
            action_key=action_key,
            title=prompt_cfg.title,
            prompt_label=prompt_cfg.label,
            pad_label=pad_label,
            show_correct_marked_checkbox=prompt_cfg.show_correct_marked_checkbox,
        )
        return

    _add_prompt_action(
        browser,
        menu,
        label=label,
        cfg=cfg,
        base_tags=resolved_tags,
        action_key=action_key,
        title=prompt_cfg.title,
        prompt_label=prompt_cfg.label,
        blank_behavior=prompt_cfg.blank_behavior,
        number_style=prompt_cfg.number_style,
        pad_label=pad_label,
        allow_freeform_child_segments=prompt_cfg.allow_freeform_child_segments,
        include_rotation_for_freeform=prompt_cfg.include_rotation_for_freeform,
        show_correct_marked_checkbox=prompt_cfg.show_correct_marked_checkbox,
    )


def add_base_plain_action(browser, menu, cfg: MissedTagsConfig):
    action = QAction(cfg.action_label_base, browser)
    action.triggered.connect(
        lambda _: apply_tags_to_selected_notes(browser, cfg.base_missed_tag, action_key="base_plain", cfg=cfg)
    )
    menu.addAction(action)


def add_missed_tag_menu_items(browser, menu):
    cfg = load_runtime_config()

    tag_menu = QMenu(cfg.missed_tags_menu_label, browser)
    tag_menu.setStyleSheet(build_missed_tags_menu_stylesheet())

    add_uworld_tags(browser, tag_menu, cfg)
    add_uworld_correct_missed_tag(browser, tag_menu, cfg)
    add_nbme_tag(browser, tag_menu, cfg)
    add_amboss_tag(browser, tag_menu, cfg)
    if cfg.show_base_plain_action:
        add_base_plain_action(browser, tag_menu, cfg)

    add_multi_tag(browser, tag_menu, cfg)
    add_key_info_action(browser, tag_menu, cfg)

    add_correct_guess_action(browser, tag_menu, cfg)

    if cfg.other_submenu_enabled:
        submenu_label = str(cfg.other_submenu_label).strip() or "Other"
        other_menu = QMenu(submenu_label, browser)
        other_menu.setStyleSheet(build_missed_tags_menu_stylesheet())
        add_other_resources_actions(browser, other_menu, cfg)
        if other_menu.actions():
            tag_menu.addMenu(other_menu)
    else:
        add_other_resources_actions(browser, tag_menu, cfg)

    if tag_menu.actions():
        menu.addMenu(tag_menu)


def add_nbme_tag(browser, menu, cfg: MissedTagsConfig):
    base_tag = _nbme_base_tag(cfg)
    _add_schema_driven_action(
        browser,
        menu,
        label=cfg.subset_2_name,
        cfg=cfg,
        tags=[base_tag],
        action_key="nbme_form_prompt",
        prompt_cfg=cfg.nbme_prompt,
        pad_label=True,
    )


def add_amboss_tag(browser, menu, cfg: MissedTagsConfig):
    _add_schema_driven_action(
        browser,
        menu,
        label=cfg.amboss_top_level_name,
        cfg=cfg,
        tags=[cfg.amboss_base_tag],
        action_key="amboss_test_prompt",
        prompt_cfg=cfg.amboss_prompt,
        pad_label=True,
    )


def add_multi_tag(browser, menu, cfg: MissedTagsConfig):
    add_static_action(
        browser,
        menu,
        f"{cfg.action_label_multi_missed:<24}",
        list(cfg.multi_miss_tags),
        action_key="multi_missed",
        cfg=cfg,
    )


def add_uworld_tags(browser, menu, cfg: MissedTagsConfig):
    set_name = cfg.subset_1_name
    base = _uw_base_tag(cfg)
    if set_name and base:
        _add_schema_driven_action(
            browser,
            menu,
            label=set_name,
            cfg=cfg,
            tags=[base],
            action_key="uw_test_prompt",
            prompt_cfg=cfg.uworld_prompt,
            pad_label=True,
        )


def add_uworld_correct_missed_tag(browser, menu, cfg: MissedTagsConfig):
    action_label = str(cfg.action_label_uw_correct_missed or DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL).strip()
    action = QAction(action_label or DEFAULT_UW_CORRECT_MISSED_ACTION_LABEL, browser)

    def on_trigger():
        if not _ensure_selected_notes(browser):
            return

        selected_source, source_input, ok = _prompt_correct_missed_source_and_input(browser, action.text())
        if not ok:
            return

        base_missed_tag = _resolved_base_tag(cfg)
        configured_base_tag = (
            str(cfg.uw_correct_missed_tags[0]).strip()
            if cfg.uw_correct_missed_tags
            else f"{base_missed_tag}::{CORRECT_MARKED_TAG_SEGMENT}"
        )
        configured_segment = _normalize_freeform_tag_path(cfg.uw_correct_missed_tag_segment)
        if not configured_segment:
            configured_segment = _normalize_freeform_tag_path(
                _extract_tag_suffix(configured_base_tag, CORRECT_MARKED_TAG_SEGMENT)
            )
        correct_marked_segment = configured_segment or CORRECT_MARKED_TAG_SEGMENT
        correct_marked_base_tag = configured_base_tag or f"{base_missed_tag}::{correct_marked_segment}"
        raw_input = str(source_input or "").strip()
        if selected_source == "UWorld":
            try:
                test_number = int(raw_input)
            except ValueError:
                showInfo(MSG_INVALID_INTEGER_TEST_NUMBER)
                return
            if test_number <= 0:
                showInfo(MSG_INVALID_INTEGER_TEST_NUMBER)
                return
            uworld_base_tag = _uw_base_tag(cfg)
            source_tag = _format_uworld_test_tag(cfg, uworld_base_tag, test_number)
            formatted_tag = f"{source_tag}::{correct_marked_segment}"
        elif selected_source == "NBME":
            nbme_child_path = _normalize_nbme_child_path(raw_input)
            if not nbme_child_path:
                showInfo(MSG_INVALID_NBME_INPUT)
                return
            nbme_base_tag = _nbme_base_tag(cfg)
            source_tag = f"{nbme_base_tag}::{nbme_child_path}"
            formatted_tag = f"{source_tag}::{correct_marked_segment}"
        elif selected_source == "Amboss":
            normalized_input = _normalize_freeform_tag_path(raw_input)
            if not normalized_input:
                showInfo(MSG_INVALID_CORRECT_MARKED_SOURCE_INPUT)
                return
            amboss_base_tag = str(cfg.amboss_base_tag).strip() or f"{base_missed_tag}::Amboss"
            source_tag = f"{amboss_base_tag}::{normalized_input}"
            formatted_tag = f"{source_tag}::{correct_marked_segment}"
        else:
            normalized_input = _normalize_freeform_tag_path(raw_input)
            if not normalized_input:
                showInfo(MSG_INVALID_CORRECT_MARKED_SOURCE_INPUT)
                return
            formatted_tag = f"{correct_marked_base_tag}::{normalized_input}"

        apply_tags_to_selected_notes(
            browser,
            [formatted_tag],
            action_key=ACTION_KEY_CORRECT_TAG_MISSED_PROMPT,
            cfg=cfg,
        )

    action.triggered.connect(on_trigger)
    menu.addAction(action)


def add_other_resources_actions(
    browser,
    menu,
    cfg: MissedTagsConfig,
    resources_override: list[str] | None = None,
):
    if resources_override is not None:
        other_actions = []
        for idx, resource_name in enumerate(resources_override, start=1):
            canonical = scrub_resource_label_to_tag(resource_name)
            if not canonical:
                continue
            action_key = (
                f"other_resource_{idx:02d}_{re.sub(r'[^a-z0-9]+', '_', canonical.lower()).strip('_')}"
            )
            prompt_cfg = PromptActionConfig(
                kind=PROMPT_KIND_NONE,
                number_style=PROMPT_STYLE_ROTATION_THEN_NUMBER,
                blank_behavior=PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
                title=PROMPT_DEFAULT_TITLE,
                label=PROMPT_DEFAULT_LABEL,
                allow_freeform_child_segments=False,
                include_rotation_for_freeform=True,
            )
            include_base_tag = True
            if canonical.lower() == "true-learn":
                action_key = "true_learn_test_prompt"
                prompt_cfg = PromptActionConfig(
                    kind=PROMPT_KIND_NUMBER,
                    number_style=PROMPT_STYLE_ROTATION_THEN_NUMBER,
                    blank_behavior=PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
                    title=PROMPT_TRUE_LEARN_TITLE,
                    label=PROMPT_DEFAULT_LABEL,
                    allow_freeform_child_segments=False,
                    include_rotation_for_freeform=True,
                )
                include_base_tag = False
            resource_tag = base_tag_path(cfg, cfg.other_suffix, canonical)
            other_actions.append(
                OtherResourceActionConfig(
                    action_key=action_key,
                    label=str(resource_name).strip() or canonical,
                    tags=[resource_tag],
                    prompt=prompt_cfg,
                    include_base_tag=include_base_tag,
                )
            )
    else:
        other_actions = list(cfg.other_resource_actions)

    for action_spec in other_actions:
        canonical_label = scrub_resource_label_to_tag(action_spec.label)
        if cfg.amboss_remove_from_other_menu and canonical_label.lower() == "amboss":
            continue
        action_tags = [str(tag).strip() for tag in action_spec.tags if str(tag).strip()]
        if not action_tags:
            continue
        if action_spec.include_base_tag and action_spec.prompt.kind == PROMPT_KIND_NONE:
            action_tags = list(cfg.base_missed_tag) + action_tags
        _add_schema_driven_action(
            browser,
            menu,
            label=action_spec.label,
            cfg=cfg,
            tags=action_tags,
            action_key=action_spec.action_key,
            prompt_cfg=action_spec.prompt,
            pad_label=False,
        )


def make_test_prompt_handler(
    browser,
    cfg: MissedTagsConfig,
    base_tags: list[str],
    action_key: str,
    title: str | None = None,
    label: str | None = None,
    blank_behavior: str = PROMPT_BEHAVIOR_BASE_PLUS_ROTATION,
    number_style: str = PROMPT_STYLE_RANGE_THEN_NUMBER,
    allow_freeform_child_segments: bool = False,
    include_rotation_for_freeform: bool = True,
    show_correct_marked_checkbox: bool = False,
):
    def on_trigger():
        prompt_title = (title or PROMPT_DEFAULT_TITLE).strip() or PROMPT_DEFAULT_TITLE
        prompt_label = (label or PROMPT_DEFAULT_LABEL).strip() or PROMPT_DEFAULT_LABEL
        saved_test_num = _get_saved_prompt_input(action_key)
        append_correct_marked = False
        checkbox_state_key = ""
        if show_correct_marked_checkbox:
            checkbox_state_key = _correct_marked_checkbox_state_key(action_key)
            saved_append_state = _get_saved_prompt_input(checkbox_state_key)
            default_append_state = _to_bool(saved_append_state, AMBOSS_APPEND_CORRECT_MARKED_DEFAULT)
            test_num, append_correct_marked, ok = _positioned_text_prompt_with_checkbox(
                browser,
                title=prompt_title,
                label=prompt_label,
                default_text=saved_test_num,
                checkbox_label=PROMPT_CORRECT_MARKED_CHECKBOX_LABEL,
                checkbox_checked=default_append_state,
            )
        else:
            test_num, ok = _positioned_text_prompt(
                browser, prompt_title, prompt_label, default_text=saved_test_num
            )
        if not ok:
            return
        if checkbox_state_key:
            _save_prompt_input(checkbox_state_key, "1" if append_correct_marked else "0")
        test_num = (test_num or "").strip()
        rot_num_2d, rot_label, _ = get_current_or_next_rotation_meta(cfg)
        rotation_segment = get_formatted_rotation_segment(cfg, rot_num_2d, rot_label)

        resolved_base_tags = [str(tag).strip() for tag in base_tags if str(tag).strip()]
        if not resolved_base_tags:
            return

        def _build_formatted_tag(base_tag: str) -> str:
            if test_num == "":
                if allow_freeform_child_segments and not include_rotation_for_freeform:
                    return f"{base_tag}"
                if blank_behavior == PROMPT_BEHAVIOR_BASE_ONLY:
                    return f"{base_tag}"
                return f"{base_tag}::{rotation_segment}"

            if allow_freeform_child_segments:
                freeform_path = _normalize_freeform_tag_path(test_num)
                if freeform_path:
                    if include_rotation_for_freeform:
                        return f"{base_tag}::{rotation_segment}::{freeform_path}"
                    return f"{base_tag}::{freeform_path}"
                if blank_behavior == PROMPT_BEHAVIOR_BASE_ONLY:
                    return f"{base_tag}"
                if include_rotation_for_freeform:
                    return f"{base_tag}::{rotation_segment}"
                return f"{base_tag}"

            try:
                tn = int(test_num)
            except ValueError:
                if action_key == "uw_test_prompt":
                    freeform_path = _normalize_uworld_child_tag_path(test_num)
                    if freeform_path:
                        return f"{base_tag}::{freeform_path}"
                if blank_behavior == PROMPT_BEHAVIOR_BASE_ONLY:
                    return f"{base_tag}"
                return f"{base_tag}::{rotation_segment}"

            if number_style == PROMPT_STYLE_ROTATION_THEN_NUMBER:
                return f"{base_tag}::{rotation_segment}::{tn:02d}"
            if number_style == PROMPT_STYLE_NUMBER_ONLY:
                return f"{base_tag}::{tn:02d}"
            return _format_uworld_test_tag(cfg, base_tag, tn)

        if test_num == "":
            _save_prompt_input(action_key, "")
        elif allow_freeform_child_segments:
            _save_prompt_input(action_key, test_num)
        else:
            try:
                int(test_num)
            except ValueError:
                if action_key == "uw_test_prompt" and _normalize_uworld_child_tag_path(test_num):
                    _save_prompt_input(action_key, test_num)
            else:
                _save_prompt_input(action_key, test_num)

        formatted_tags = [_build_formatted_tag(base_tag) for base_tag in resolved_base_tags]
        if append_correct_marked:
            formatted_tags = [
                _append_tag_segment(tag, AMBOSS_CORRECT_MARKED_TAG_SEGMENT) for tag in formatted_tags
            ]

        if not _ensure_selected_notes(browser):
            return
        apply_tags_to_selected_notes(browser, formatted_tags, action_key=action_key, cfg=cfg)

    return on_trigger


def add_static_action(browser, menu, set_name: str, tags: list[str], action_key: str, cfg: MissedTagsConfig):
    action = QAction(set_name, browser)
    action.triggered.connect(
        lambda _, tags=tags, k=action_key: apply_tags_to_selected_notes(browser, tags, action_key=k, cfg=cfg)
    )
    menu.addAction(action)


def add_key_info_action(browser, menu, cfg: MissedTagsConfig):
    action = QAction(cfg.action_label_key_info, browser)

    def on_click():
        if not _ensure_selected_notes(browser):
            return
        key_tag = get_rotation_key_info_tag(cfg)
        apply_tags_to_selected_notes(browser, [key_tag], action_key="add_key_info_action", cfg=cfg)

    action.triggered.connect(on_click)
    menu.addAction(action)


def add_correct_guess_action(browser, menu, cfg: MissedTagsConfig):
    action = QAction(cfg.action_label_correct_guess, browser)

    def on_trigger():
        if not _ensure_selected_notes(browser):
            return

        saved_subtag = _get_saved_prompt_input("correct_guess_subtag_prompt")
        subtag, ok = _positioned_text_prompt(
            browser,
            PROMPT_CORRECT_GUESS_SUBTAG_TITLE,
            PROMPT_CORRECT_GUESS_SUBTAG_LABEL,
            default_text=saved_subtag,
        )
        if not ok:
            return

        subtag = str(subtag or "").strip()
        if re.search(r"\s", subtag):
            showInfo(MSG_INVALID_CORRECT_GUESS_SUBTAG)
            return

        _save_prompt_input("correct_guess_subtag_prompt", subtag)
        apply_tags_to_selected_notes(
            browser,
            get_correct_guess_tags(cfg, subtag=subtag),
            action_key="correct_guess",
            cfg=cfg,
        )

    action.triggered.connect(on_trigger)
    menu.addAction(action)
