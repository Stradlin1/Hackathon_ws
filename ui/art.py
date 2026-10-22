"""Generated plates: paths, inline data URIs and the plate figure markup.

Illustrations live in static/art/ as transparent webp (the paper ground was cut
to alpha by tools/prepare_art.py). Large plates go through st.image so the
browser fetches them once; small decorations are inlined as data URIs so a
missing file can never show a broken image. Every helper fails soft: if a file
is absent the page simply renders without the ornament.
"""

from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path

ART = Path(__file__).resolve().parent.parent / 'static' / 'art'


def esc(value: str) -> str:
    """Escape an attribute value; kept local so ui.art never imports ui.components."""
    return html.escape(value, quote=True)


@lru_cache(maxsize=None)
def path(name: str) -> Path | None:
    """Return the webp/png for a plate, or None when it has not been generated."""
    for suffix in ('.webp', '.png'):
        candidate = ART / f'{name}{suffix}'
        if candidate.is_file():
            return candidate
    return None


@lru_cache(maxsize=None)
def data_uri(name: str) -> str:
    """Inline a plate as a data URI; empty string when the file is missing."""
    file = path(name)
    if file is None:
        return ''
    mime = 'image/webp' if file.suffix == '.webp' else 'image/png'
    return f'data:{mime};base64,' + base64.b64encode(file.read_bytes()).decode('ascii')


def background(name: str) -> str:
    """CSS declarations that paint a plate, or an empty string when missing."""
    uri = data_uri(name)
    return f"background-image:url('{uri}')" if uri else ''


def figure(name: str, alt: str = '', caption: str = '') -> str:
    """Return a masked plate figure, or an empty string when the art is missing."""
    uri = data_uri(name)
    if not uri:
        return ''
    cap = f'<figcaption>{esc(caption)}</figcaption>' if caption else ''
    cls = 'plate plate-ornament' if name == 'fleuron' else 'plate'
    return (
        f'<figure class="{cls}">'
        f'<img src="{uri}" alt="{esc(alt)}" loading="lazy">'
        f'{cap}</figure>'
    )


def entry_art(name: str) -> str:
    """Small decorative plate used inside a card; empty string when missing."""
    decl = background(name)
    return f'<div class="entry-art" style="{decl}" aria-hidden="true"></div>' if decl else ''
