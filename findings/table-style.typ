// FairGuard findings-report table styling.
// Injected into the pandoc -> Typst build via `--include-in-header`. It lands
// AFTER pandoc's own `#set table(inset: 6pt, stroke: none)`, so it overrides it.
//
// Purpose: pandoc's default renders borderless tables and cannot wrap long
// inline-code tokens (file paths), which then overflow into neighbouring
// columns. This adds a light grid + shaded header, tightens the table font,
// and makes long inline code breakable so it wraps inside its cell.

#set table(
  stroke: 0.5pt + rgb("#c8c8cc"),
  inset: (x: 6pt, y: 4.5pt),
  align: left + top,
  fill: (x, y) => if y == 0 { rgb("#eef0f4") } else { white },
)

// Header row: bold.
#show table.cell.where(y: 0): set text(weight: "bold")

// Render the "role confirmed" check (✓, U+2713) as a green monochrome VECTOR
// glyph. The report source deliberately avoids the ✅ color emoji (U+2705),
// which some PDF viewers drop along with surrounding text; a `set` show rule
// only tints the matched glyph, so there is no recursion.
#show "✓": set text(fill: rgb("#1a7f37"))

// Slightly smaller type inside tables so wide tables fit the text block.
#show table: set text(size: 8.5pt)

// Make long inline code (e.g. skills/.../03_agency_concentration.py) wrap:
// insert zero-width break opportunities after path separators. Emitted as
// monospace text (not raw) to avoid re-triggering this show rule.
#show raw.where(block: false): it => {
  let t = it.text
  for s in ("/", "_", "-", ".", "::") {
    t = t.replace(s, s + "\u{200B}")
  }
  text(font: ("DejaVu Sans Mono", "Liberation Mono", "Consolas"), size: 0.92em)[#t]
}
