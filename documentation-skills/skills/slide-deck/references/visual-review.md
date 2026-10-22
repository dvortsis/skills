# Visual review by contact sheet (VISUAL_BATCH)

Lint measures the built file; this review checks what a viewer sees. Run it after lint reports 0 failed.

1. **Render into a new folder.** `python scripts/render_preview.py <Name>.pptx` converts the deck, writes the slide PNGs to a new `<Name>_preview_<timestamp>` folder and runs the shared `scripts/visual_batch.py render`, which puts contact sheets of 4 slides (`sheet_01.png`, ...) and `visual_log.json` in a new `<Name>_render_<timestamp>` folder inside it. It prints that render folder and the next commands. Never reuse an older render: a viewer can show a stale image when a file name repeats.
2. **View every contact sheet.** Then record it: `python scripts/visual_batch.py viewed <render folder> --sheet 1 2 3`.
3. **Full size where it matters.** Open a slide full size (`pages/page_NNN.png`) when its sheet shows a possible problem, and for every slide with small text (dense tables, charts with axis labels, annotated screenshots). Record each view: `visual_batch.py full <render folder> --page P --reason "..."`. Open the sheet before the full-size view; check fails a full-size view whose sheet was never viewed.
4. **Record findings.** `visual_batch.py finding <render folder> --page P --text "what is wrong"`. Look for overflow or clipped text, a word alone on a last line, titles that wrap badly, mismatched comparison headings, unbalanced or half-empty cards, crowding under the title, overlapping shapes, empty space, inconsistent footers, a logo that is missing, stretched or crowded, and a cover or divider that reads poorly.
5. **Fix and rebuild.** Fix `deck.json` (never the .pptx), rebuild and re-lint, check the fixed slide, then `visual_batch.py fixed <render folder> --page P --note "how"`.
6. **Check.** `python scripts/visual_batch.py check <render folder> --log <file_key>.visual_qa.md` fails (VISUAL_BATCH) when a page is on no viewed sheet, a full-size view skipped its sheet, or a finding is unfixed, and writes the page table to the log. `<file_key>` is the deck name without its version suffix.
7. **Reply line.** Copy the line check prints: `visual review: N pages on S sheets, F viewed full size, M findings fixed`. If render_preview printed NOT RUN (no LibreOffice or PyMuPDF, or the conversion failed), write `visual review: not run (<reason>)`, never "passed".

Brand fonts missing in the sandbox are substituted in the render only; judge spacing with that in mind and note it if a finding depends on font metrics.
