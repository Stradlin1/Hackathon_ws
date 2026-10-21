"""Inline SVG icons.

Emoji are not used anywhere in the interface: a Linux desktop without a colour
emoji font renders them as tofu boxes. These 24x24 stroke icons inherit the text
colour (currentColor) and need no font, file or network access.
"""

from __future__ import annotations

_PATHS = {
    'search': '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4.5 4.5"/>',
    'layers': '<path d="M12 3.5 3.5 8l8.5 4.5L20.5 8 12 3.5Z"/><path d="M3.5 12.5 12 17l8.5-4.5"/>',
    'lock': '<rect x="5" y="10.5" width="14" height="9.5" rx="2.2"/>'
            '<path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5"/>',
    'clipboard': '<rect x="5" y="4.5" width="14" height="16" rx="2.2"/>'
                 '<path d="M9 4.5V3h6v1.5"/><path d="M9 11h6M9 15h4"/>',
    'camera': '<path d="M4 8.5h3l1.5-2h7L17 8.5h3v10H4Z"/><circle cx="12" cy="13" r="3.2"/>',
    'folder': '<path d="M3.5 6.5h6l2 2h9v11h-17Z"/>',
    'bell': '<path d="M6 9.5a6 6 0 0 1 12 0c0 3.8 1 5.3 2 6.5H4c1-1.2 2-2.7 2-6.5Z"/>'
            '<path d="M10 19a2 2 0 0 0 4 0"/>',
    'inbox': '<path d="M3.5 13.5 6 5.5h12l2.5 8v5h-17Z"/><path d="M3.5 13.5H9l1 3h4l1-3h5.5"/>',
    'check': '<circle cx="12" cy="12" r="8.5"/><path d="M8.5 12.2 11 14.7l4.5-5"/>',
    'handshake': '<path d="M3.5 12.5 8 8l2.5 2.5L12 9l1.5 1.5L16 8l4.5 4.5"/>'
                 '<path d="M8 17.5 12 21l4-3.5"/>',
    'home': '<path d="M4 11 12 4l8 7"/><path d="M6.5 9.8V20h11V9.8"/>',
    'sparkle': '<path d="M12 3.5 13.8 9l5.5 1.8-5.5 1.8L12 18l-1.8-5.4L4.7 10.8 10.2 9Z"/>',
    'user': '<circle cx="12" cy="8.5" r="3.6"/><path d="M5 20c.8-3.4 3.6-5.2 7-5.2S18.2 16.6 19 20"/>',
}


def icon(name: str, size: int = 18) -> str:
    """Return an inline SVG for the given name; unknown names fall back to a dot."""
    body = _PATHS.get(name, '<circle cx="12" cy="12" r="3"/>')
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{body}</svg>'
    )
