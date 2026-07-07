# Fonts And Color Notes

## Three-Color E-Paper

Most 4.2 inch tri-color e-paper modules are white / black / red. They cannot
render blue. The current mock data keeps an `accent` field for UI semantics, but
the firmware maps non-red accents to black.

If a future panel supports four colors, only `DashboardUI` should change.

## Chinese Text

The firmware skeleton uses Adafruit GFX mono fonts, which do not contain Chinese
glyphs. The data model is UTF-8, but visible Chinese rendering requires one of
these approaches:

1. **Server-side raster text blocks**
   - Server renders Chinese sections as monochrome bitmaps.
   - ESP32 only draws images.
   - Best visual fidelity, more server work.

2. **Embedded Chinese bitmap subset**
   - Generate a small glyph subset for the actual UI words.
   - ESP32 renders those glyphs locally.
   - Good for fixed labels and limited todo text.

3. **Use English-only MVP**
   - Fastest firmware bring-up.
   - Later add Chinese font support when layout is stable.

Recommended path:

- MVP: English labels and short ASCII/Latin data.
- v2: server-side rendered Chinese text regions if Chinese todo/notes are
  required on the device.

