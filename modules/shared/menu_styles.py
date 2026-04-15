"""Shared QMenu stylesheet builders and style profiles for _Change_notes."""

from __future__ import annotations

from pathlib import Path

# ! ------------------------- USER-TUNABLE STYLE DEFAULTS -------------------------
DEFAULT_SUBMENU_ARROW_ICON_ABS_PATH = str(
    (Path(__file__).resolve().parent.parent / "assets" / "submenu_arrow.svg")
)
DEFAULT_MENU_ITEM_HOVER_BACKGROUND_COLOR = "rgba(120, 160, 255, 60)"
DEFAULT_MENU_ITEM_PADDING_VERTICAL_PX = 4.5
DEFAULT_MENU_ITEM_PADDING_HORIZONTAL_PX = 6
DEFAULT_SUBMENU_ARROW_ICON_SIZE_PX = 8
DEFAULT_SUBMENU_ARROW_HORIZONTAL_PADDING_PX = 0

# Menu-specific behavior toggles.
CONTEXT_SUBMENUS_USE_SUBMENU_ITEM_STYLING = True
CONTEXT_SUBMENUS_USE_CUSTOM_SUBMENU_ARROW_ICON = True
CUSTOM_TAGS_USE_CUSTOM_MENU_STYLING = True
CUSTOM_TAGS_USE_CUSTOM_SUBMENU_ARROW_ICON = True
MISSED_TAGS_USE_CUSTOM_SUBMENU_ARROW_ICON = True

# Global menu surface/separator defaults.
DEFAULT_MENU_SURFACE_BACKGROUND_COLOR = "palette(base)"
DEFAULT_MENU_ITEM_BACKGROUND_COLOR = "transparent"
DEFAULT_MENU_SEPARATOR_LINE_COLOR = "palette(mid)"
DEFAULT_MENU_SEPARATOR_LINE_COLOR_FALLBACK = "rgba(128, 128, 128, 120)"
DEFAULT_MENU_SEPARATOR_LINE_COLOR_IN_USE = (
    DEFAULT_MENU_SEPARATOR_LINE_COLOR or DEFAULT_MENU_SEPARATOR_LINE_COLOR_FALLBACK
)
DEFAULT_MENU_SEPARATOR_HEIGHT_PX = 1
DEFAULT_MENU_SEPARATOR_MARGIN_HORIZONTAL_PX = 0
DEFAULT_MENU_SEPARATOR_MARGIN_VERTICAL_PX = 0
# ! -----------------------------------------------------------------------------


def build_qmenu_item_stylesheet(
    *,
    item_padding_vertical_px: float = DEFAULT_MENU_ITEM_PADDING_VERTICAL_PX,
    item_padding_horizontal_px: float = DEFAULT_MENU_ITEM_PADDING_HORIZONTAL_PX,
    hover_background_color: str = DEFAULT_MENU_ITEM_HOVER_BACKGROUND_COLOR,
) -> str:
    return (
        "QMenu::item {\n"
        f"    padding-top: {item_padding_vertical_px}px;\n"
        f"    padding-bottom: {item_padding_vertical_px}px;\n"
        f"    padding-left: {item_padding_horizontal_px}px;\n"
        f"    padding-right: {item_padding_horizontal_px}px;\n"
        "}\n"
        "QMenu::item:selected {\n"
        f"    background-color: {hover_background_color};\n"
        "}"
    )


def build_qmenu_right_arrow_stylesheet(
    *,
    use_custom_submenu_arrow_icon: bool,
    submenu_arrow_icon_abs_path: str,
    submenu_arrow_icon_size_px: float = DEFAULT_SUBMENU_ARROW_ICON_SIZE_PX,
    submenu_arrow_horizontal_padding_px: float | None = DEFAULT_SUBMENU_ARROW_HORIZONTAL_PADDING_PX,
) -> str:
    if not use_custom_submenu_arrow_icon or not submenu_arrow_icon_abs_path:
        return ""

    arrow_path = submenu_arrow_icon_abs_path.replace("\\", "/")
    lines = [
        "QMenu::right-arrow {",
        f'    image: url("{arrow_path}");',
        f"    width: {submenu_arrow_icon_size_px}px;",
        f"    height: {submenu_arrow_icon_size_px}px;",
    ]
    if submenu_arrow_horizontal_padding_px is not None:
        lines.extend(
            [
                f"    padding-left: {submenu_arrow_horizontal_padding_px}px;",
                f"    padding-right: {submenu_arrow_horizontal_padding_px}px;",
            ]
        )
    lines.append("}")
    return "\n".join(lines)


def build_qmenu_stylesheet(
    *,
    item_padding_vertical_px: float = DEFAULT_MENU_ITEM_PADDING_VERTICAL_PX,
    item_padding_horizontal_px: float = DEFAULT_MENU_ITEM_PADDING_HORIZONTAL_PX,
    hover_background_color: str = DEFAULT_MENU_ITEM_HOVER_BACKGROUND_COLOR,
    use_custom_submenu_arrow_icon: bool = False,
    submenu_arrow_icon_abs_path: str = "",
    submenu_arrow_icon_size_px: float = DEFAULT_SUBMENU_ARROW_ICON_SIZE_PX,
    submenu_arrow_horizontal_padding_px: float | None = DEFAULT_SUBMENU_ARROW_HORIZONTAL_PADDING_PX,
) -> str:
    item_stylesheet = build_qmenu_item_stylesheet(
        item_padding_vertical_px=item_padding_vertical_px,
        item_padding_horizontal_px=item_padding_horizontal_px,
        hover_background_color=hover_background_color,
    )
    arrow_stylesheet = build_qmenu_right_arrow_stylesheet(
        use_custom_submenu_arrow_icon=use_custom_submenu_arrow_icon,
        submenu_arrow_icon_abs_path=submenu_arrow_icon_abs_path,
        submenu_arrow_icon_size_px=submenu_arrow_icon_size_px,
        submenu_arrow_horizontal_padding_px=submenu_arrow_horizontal_padding_px,
    )
    if not arrow_stylesheet:
        return item_stylesheet.strip()
    return f"{item_stylesheet}\n{arrow_stylesheet}".strip()


def build_context_submenu_arrow_stylesheet() -> str:
    return build_qmenu_right_arrow_stylesheet(
        use_custom_submenu_arrow_icon=CONTEXT_SUBMENUS_USE_CUSTOM_SUBMENU_ARROW_ICON,
        submenu_arrow_icon_abs_path=DEFAULT_SUBMENU_ARROW_ICON_ABS_PATH,
    )


def build_context_submenu_item_stylesheet() -> str:
    if not CONTEXT_SUBMENUS_USE_SUBMENU_ITEM_STYLING:
        return ""

    return build_qmenu_item_stylesheet()


def build_custom_tags_menu_stylesheet() -> str:
    if not CUSTOM_TAGS_USE_CUSTOM_MENU_STYLING:
        return ""

    return build_qmenu_stylesheet(
        use_custom_submenu_arrow_icon=CUSTOM_TAGS_USE_CUSTOM_SUBMENU_ARROW_ICON,
        submenu_arrow_icon_abs_path=DEFAULT_SUBMENU_ARROW_ICON_ABS_PATH,
    )


def build_missed_tags_menu_stylesheet() -> str:
    base_stylesheet = build_qmenu_stylesheet(
        use_custom_submenu_arrow_icon=MISSED_TAGS_USE_CUSTOM_SUBMENU_ARROW_ICON,
        submenu_arrow_icon_abs_path=DEFAULT_SUBMENU_ARROW_ICON_ABS_PATH,
    )
    surface_and_separator_stylesheet = (
        "QMenu {\n"
        f"    background-color: {DEFAULT_MENU_SURFACE_BACKGROUND_COLOR};\n"
        "}\n"
        "QMenu::item {\n"
        f"    background-color: {DEFAULT_MENU_ITEM_BACKGROUND_COLOR};\n"
        "}\n"
        "QMenu::separator {\n"
        f"    height: {DEFAULT_MENU_SEPARATOR_HEIGHT_PX}px;\n"
        f"    background: {DEFAULT_MENU_SEPARATOR_LINE_COLOR_IN_USE};\n"
        f"    margin-left: {DEFAULT_MENU_SEPARATOR_MARGIN_HORIZONTAL_PX}px;\n"
        f"    margin-right: {DEFAULT_MENU_SEPARATOR_MARGIN_HORIZONTAL_PX}px;\n"
        f"    margin-top: {DEFAULT_MENU_SEPARATOR_MARGIN_VERTICAL_PX}px;\n"
        f"    margin-bottom: {DEFAULT_MENU_SEPARATOR_MARGIN_VERTICAL_PX}px;\n"
        "}"
    )
    return f"{base_stylesheet}\n{surface_and_separator_stylesheet}".strip()
