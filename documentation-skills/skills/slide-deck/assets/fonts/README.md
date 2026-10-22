# Fallback fonts

Used only when the project names no font of its own (scripts/brand.py looks for the project's fonts first: a brand
profile, CSS and Tailwind fonts, design tokens, Office templates, font files the project ships, @fontsource packages and
its UI framework's default).

| Font | Version | Role | Source | License |
|---|---|---|---|---|
| Inter | 4.1 | body, headings | https://github.com/rsms/inter (release v4.1) | SIL Open Font License 1.1, `Inter-OFL.txt` |
| JetBrains Mono | 2.304 | code | https://github.com/JetBrains/JetBrainsMono (release v2.304) | SIL Open Font License 1.1, `JetBrainsMono-OFL.txt` |

The font files are stored unmodified as base64 text (`*.ttf.b64`) so an upload can't corrupt them; `fonts.json` holds
each file's size and SHA-256, and brand.py decodes them into a cache folder on first use and checks them there.
The builds use them to measure text and line spacing, embed them in PDFs and (Word) in documents. Under the OFL they
may be bundled and redistributed with software, but not sold on their own; keep the license files with them.
