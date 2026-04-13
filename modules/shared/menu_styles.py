"""Shared QMenu stylesheet builders for _Change_notes."""

from __future__ import annotations

# ! --------------------- USER-TUNABLE SHARED STYLE DEFAULTS ---------------------
DEFAULT_MENU_ITEM_HOVER_BACKGROUND_COLOR = "rgba(120, 160, 255, 60)"
DEFAULT_MENU_ITEM_PADDING_TOP_PX = 4.5
DEFAULT_MENU_ITEM_PADDING_BOTTOM_PX = 4.5
DEFAULT_MENU_ITEM_PADDING_LEFT_PX = 6
DEFAULT_MENU_ITEM_PADDING_RIGHT_PX = 6
DEFAULT_SUBMENU_ARROW_ICON_SIZE_PX = 12
DEFAULT_SUBMENU_ARROW_HORIZONTAL_PADDING_PX = 0
# ! -----------------------------------------------------------------------------


def build_qmenu_item_stylesheet(
    *,
    item_padding_top_px: float = DEFAULT_MENU_ITEM_PADDING_TOP_PX,
    item_padding_bottom_px: float = DEFAULT_MENU_ITEM_PADDING_BOTTOM_PX,
    item_padding_left_px: float = DEFAULT_MENU_ITEM_PADDING_LEFT_PX,
    item_padding_right_px: float = DEFAULT_MENU_ITEM_PADDING_RIGHT_PX,
    hover_background_color: str = DEFAULT_MENU_ITEM_HOVER_BACKGROUND_COLOR,
) -> str:
    return (
        "QMenu::item {\n"
        f"    padding-top: {item_padding_top_px}px;\n"
        f"    padding-bottom: {item_padding_bottom_px}px;\n"
        f"    padding-left: {item_padding_left_px}px;\n"
        f"    padding-right: {item_padding_right_px}px;\n"
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
    item_padding_top_px: float = DEFAULT_MENU_ITEM_PADDING_TOP_PX,
    item_padding_bottom_px: float = DEFAULT_MENU_ITEM_PADDING_BOTTOM_PX,
    item_padding_left_px: float = DEFAULT_MENU_ITEM_PADDING_LEFT_PX,
    item_padding_right_px: float = DEFAULT_MENU_ITEM_PADDING_RIGHT_PX,
    hover_background_color: str = DEFAULT_MENU_ITEM_HOVER_BACKGROUND_COLOR,
    use_custom_submenu_arrow_icon: bool = False,
    submenu_arrow_icon_abs_path: str = "",
    submenu_arrow_icon_size_px: float = DEFAULT_SUBMENU_ARROW_ICON_SIZE_PX,
    submenu_arrow_horizontal_padding_px: float | None = DEFAULT_SUBMENU_ARROW_HORIZONTAL_PADDING_PX,
) -> str:
    item_stylesheet = build_qmenu_item_stylesheet(
        item_padding_top_px=item_padding_top_px,
        item_padding_bottom_px=item_padding_bottom_px,
        item_padding_left_px=item_padding_left_px,
        item_padding_right_px=item_padding_right_px,
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
