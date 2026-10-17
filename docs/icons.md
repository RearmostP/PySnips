# UI icons

The supplied pack lives unchanged in `assets/icons/actions`, `navigation`,
`content`, and `cloud`. The editor toolbar keeps its existing glyphs in
`assets/icons/editor/*.svg`, now using `currentColor` too. Legacy chevrons are
under `navigation`, and the application logo is in
`branding/pysnips-multisize.ico`. The old standalone `hamburger.svg` was replaced
by `navigation/menu.svg`.

```python
from core.ui.icons import icon, set_button_icon, NAV_ICON_SIZE

set_button_icon(delete_button, 'actions/delete')
set_button_icon(menu_button, 'navigation/menu', size=NAV_ICON_SIZE)
set_button_icon(back_button, 'navigation/arrow_back', mirror_rtl=True)
menu.addAction(icon('navigation/settings', menu), 'Settings', open_settings)
```

`icon(name, widget=None, mirror_rtl=False)` returns a `QIcon`. Names resolve
relative to `ASSETS_DIR / 'icons'`, independently of the working directory.
`.svg` is optional; explicit `.ico` supports the existing application logo.
Missing, unreadable or invalid SVG files and unsafe names return an empty icon.
`set_button_icon` uses 18px by default; navigation buttons use 20px. Qt handles
icon/text placement for the button's layout direction. Keep action text; compact
icon-only controls have translated tooltips and accessible names.

Qt SVG loading renders `currentColor` black by default; it does not inherit QSS
text colors. A small `QIconEngine` replaces `currentColor` in SVG bytes in memory
at paint time, then renders with Qt SVG. When an owner widget is supplied, its
current foreground palette role provides the color, including Disabled mode.
This respects action-specific QSS colors, such as text on accent buttons.
Theme changes repaint the same icon with the new palette; no generated files,
theme-specific icon copies, theme-name checks or external libraries are used.

For ownerless icons, `ThemeManager` exposes the validated palette through the
application's `themeColors` property. This is necessary because applying QSS
does not change `QApplication.palette()`. Without a loaded theme the helper uses
the native application palette. Supplying the widget is preferred when its
text differs from the general theme text. Owner references are weak so an icon
can safely outlive its original widget. High-DPI requests render at physical
resolution and retain the requested device pixel ratio.

Only the directional back arrow opts into horizontal mirroring. It reads the
owner's live layout direction, so switching between Hebrew and English works
without rebuilding icons. Other icons retain their original geometry.

Icons cover home navigation, snippet navigation/search/cards, category actions,
editor save/cancel and existing toolbar controls, details, trash, settings and
cloud backup actions. Card buttons retain their 35px height but can grow to fit
icon plus translated text; their header keeps its natural height to avoid
clipping the action row. Obsolete textual `[+]` and back-arrow markers were
replaced by the corresponding icons, preserving the label words.

There is no suitable search-index rebuild glyph in this pack, so that button
stays text-only. Existing section headings remain text to avoid adding layouts.
The attachment toolbar keeps its existing paperclip instead of replacing it
with a generic plus. `folder_category.svg` depicts folder trash (and duplicates
`content/trash.svg` in the supplied pack); category creation uses `actions/add`.

`PySnips.spec` already includes all of `assets`, and the direct QtSvg import is
discoverable by PyInstaller. The standalone updater retains its existing native
ICO loading and packaging; it does not need the action icon pack.

Validate with `python -m unittest discover -s tests -v`, `python -m pip check`,
and `git diff --check`. Icon tests cover rendering, palette changes, disabled
states, ownerless fallback, missing assets, high DPI, RTL mirroring and UI wiring.
