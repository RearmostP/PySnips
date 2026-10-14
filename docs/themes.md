# Themes

All themes share `assets/themes/style.qss`. Each theme directory contains only
`colors.json`, a flat object mapping semantic color names to `#RRGGBB` values or
`transparent`. The stylesheet uses `$name` placeholders, replaced with Python's
standard `string.Template`; there is no stylesheet engine or token hierarchy.

To add a theme, copy an existing `colors.json` into a new theme directory and
adjust its colors. Keep the same keys as the bundled palettes. Settings discovers
directories containing `colors.json`. PyInstaller already packages all assets.

`ThemeManager.apply(name)` keeps its existing API. Unknown or missing theme names
fall back to dark. Invalid JSON, duplicate keys, invalid colors, missing
placeholders, and unreadable files raise a `ValueError` identifying the theme and
paths. Validation happens before applying the stylesheet or changing `current`,
so a failed load preserves the active stylesheet and theme. A missing or broken
dark fallback raises the same clear error.

The palette groups page and input surfaces, text emphasis, borders, navigation,
selection, primary/secondary/destructive actions, and links. The few card roles
preserve the transparent dark cards and the outlined light cards. Distinct roles
may have the same hex value in one theme but differ in the other; each role is
defined once, and styles reference its name rather than repeating its value.

Migration notes:

- All 163 selectors from the previous stylesheets remain. Repeated selector
  blocks and obsolete earlier colors have been consolidated.
- Both themes now use the dark theme's existing spacing and font weights, except
  the card container retains the light theme's 6px radius (invisible on the dark
  transparent container). Light card actions are slightly less bold, and their
  padding, preview padding, navigation spacing and heading weights now match dark.
- Transparent 1px borders reserve space for card/action/badge outlines and focus
  states in both themes. Dark cards and actions can gain 1px of border space.
- Closely related shades were consolidated: toolbar separators use the standard
  border, navigation splitters use the preview border, popup surfaces use the
  standard surface, and badges use muted text. Light preview text uses the main
  text color; create actions use white text. Navigation and focus states are
  shared, including RTL alignment and the light theme's disabled card states.
- The primary accent, danger colors and their hover/pressed shades are preserved.
  Dimensions declared in Designer and application behavior are unchanged.

Validation: `python -m unittest discover -s tests -v` with
`QT_QPA_PLATFORM=offscreen`, followed by `git diff --check`.
