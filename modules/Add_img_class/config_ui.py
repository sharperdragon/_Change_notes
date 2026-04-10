"""Compatibility shim for legacy imports.

The add-on's canonical configuration UI lives at the root package:
`_Change_notes.config_ui.ConfigDialog`.
"""

from ...config_ui import ConfigDialog

__all__ = ["ConfigDialog"]
