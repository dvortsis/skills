# Formats

Every Markdown deliverable starts with front matter:
```
---
format: video-script | quick-start | job-aid | facilitator-guide | knowledge-check
title: …
audience: …
objective: <observable action verb> …
path: foundation | standard | advanced | all
duration_min: <number>   (video-script optional, facilitator-guide required)
output: pdf               (quick-start or job-aid only: one-page PDF sheet; see "One-page PDF" below)
role: …                   (output: pdf, optional: the page's title band role; default audience)
owner: …                  (output: pdf: document-builder needs meta.owner)
diagram: [{label: …, icon: …}]   (output: pdf, optional: 3-6 steps, labels ≤4 words, Tabler icons)
pdf_figures: false         (output: pdf, optional: leave figures out of the one-page PDF; the .md keeps them)
screenshots: pending      (when the screens it teaches aren't supplied yet)
required_screenshots:     (quick start or job aid that teaches a screen and has no embedded screenshots)
  - <screen and the exact state to capture>
sources:
  - <source title or link>
---
```

| Format | Required H2 sections | Limits enforced by lint |
|---|---|---|
| video-script | Objective · Script · Wrap-up and Next Steps | Script table `Time | On Screen | Narration`; contiguous time codes (0:00-0:20); 2–6 min, or ±25% of duration_min; ≤160 words per minute overall and in every row (CAPTION_FILE); a `Check:` at least every 2 min, each with `Answer:` |
| quick-start | Who It's For · What You Can Do · Steps · Worked Example · Common Mistakes · Get Help | ≤450 words; ≤7 numbered steps (`output: pdf`: ≤250 words, 3–5 steps, ≤2 Common Mistakes) |
| job-aid | When to Use · Steps · Check Your Work · Get Help | ≤300 words; ≤10 numbered steps (`output: pdf`: ≤250 words, ≤8 steps) |
| facilitator-guide | Session Overview · Learning Objectives · Agenda · Modules · Practice Scenario · Transfer Scenario · Materials · Follow-up | Agenda table; one H3 per module, each with `Check:` and `Answer:`; Follow-up names the follow-up evaluation and when it is sent, 30 to 60 days after (FOLLOWUP_PLAN warns) |
| knowledge-check | Instructions · Questions · Scoring | 3–10 H3 questions, each with `Answer:` and `Why:`, plus `Why not <letter>:` feedback for every other option (WHY_PER_OPTION) |
All formats fail on placeholders (TBD, TODO, "First Last"), filler words, PHI patterns, missing sources or vague objectives.

**Screenshots.** A quick start or job aid whose steps teach a screen embeds the user's screenshots (`![alt](file.png)`) or lists them under `required_screenshots` with `screenshots: pending` (SCREENSHOTS_MISSING fails otherwise; pending warns). A training deck lists its captures in the deck's shot list (`build_deck.py --draft`). Pending screenshots are an open item; the material isn't complete until they are in.

**Plain words (shared rules, `scripts/plain_language.py`).** Every step and label is a full instruction that makes sense without the speaker notes; "Rate ease; Submit the test ID" warns as TELEGRAPHIC. Define or replace jargon at first use (JARGON_UNDEFINED warns for non-developer audiences). Off-style terms warn as TERM_BRAND with the preferred term: the shared AP rules in `references/terminology.json` plus the project's house terms (the `terminology` file its brand.json names; `--brand` overrides); non-developer audiences; "not run" when the shared file is missing.

**Retrieval check.** A labeled question ("Check:" in scripts and guides, a `statement` with `"role": "retrieval"` starting "Quick check:" and ending "?" in decks). The answer is never on the same slide. In scripts and guides it follows after a pause; in decks the next slide gives it on the slide (`"role": "answer"`) and the notes may repeat it.

**Captions and transcript (video script).** After the lint passes, `scripts/md_to_captions.py <file>.md` writes `<file>.srt` (one cue per Script row, start and end from Time) and `<file>.transcript.md`. Each narration cell must fit its slot at 160 words per minute (`references/training-rules.json`); a longer cell fails CAPTION_FILE and nothing is written. Deliver both files with the script.

**Follow-up evaluation (facilitator guide).** Follow-up says when the follow-up evaluation is sent, 30 to 60 days after the session, and what it asks (use, barriers, results). Build it with material-composer's `follow-up-evaluation` format.

**Feedback for every option (knowledge check).** `Why:` explains the answer; `Why not <letter>:` explains each wrong option, so learners see why each choice is right or wrong.

**One name per set.** The materials keep one name for each document, role, status and screen label (for example "Quick Start", never also "quick reference"), and the deck uses the same names. Quote screen labels exactly as the screen shows them.

## One-page PDF (`output: pdf`, quick-start and job-aid)
The .md stays the single source: never edit the doc.json, .docx or PDF by hand. Convert with `scripts/md_to_sheet.py <file>.md` (`--combine` puts several .md files in one doc.json, one page each), build with document-builder (`build_doc.py <file>.doc.json --out <file>.docx --pdf`; the converter prints the exact command), then `lint_training.py <file>.md --pdf <file>.pdf`.
* Limits (QS_PDF_LIMITS, `references/sheet-output.json`): quick-start ≤250 words, 3–5 steps, Common Mistakes ≤2; job-aid ≤250 words, ≤8 steps. `output: pdf` on any other format fails.
* Sheet doc.json: `meta.layout: "sheet"`, `doc_type` = format; one top-level section (page) titled with the role; each H2 a level-2 subsection; Who It's For + What You Can Do and Common Mistakes + Get Help as half-width pairs; Steps → numbered block (plus a step_diagram from `diagram:`); Worked Example → card.
* QS_SOURCE_MATCH: every sentence of the .md body (front matter excluded; quotes, dashes and whitespace normalized) must appear in the PDF text; otherwise `<title>: PDF text differs from the source (<section> step <n>)`. Edit the .md, convert, rebuild, re-lint. On a match the lint prints `QS_SOURCE_MATCH pass: <title>` before the LINT summary.
* When a documentation overlay skill is attached, the PDF also passes its gate and sheet visual review.
* Other sheet formats (quick-reference card, checklist, one-pager, status report, FAQ sheet) are not training formats: material-composer owns that format catalog.

## Training deck (slide-deck)
Outline of 6–10 slides, then map into deck.json: `summary` (what learners will be able to do) → how it is organized (`diagram` process or `screenshot` with callouts) → Foundation walkthrough (`screenshot`, ≤3 callouts) → retrieval check (`statement`, answer in notes) → Standard/Advanced task (`screenshot` or `diagram`) → common mistakes (`cards`, one per mistake, or `bullets`) → `closing` with day-one actions as asks. Speaker notes on every slide. Consecutive walkthrough screenshots share one `series` value (3 at most); put a `hero` statement before the transfer scenario in decks of 8+ slides; a repeating routine can be a `diagram` `cycle`; an ordered procedure can be `steps`. A presented user guide is a `meta.type: inform` deck whose layouts follow each slide's message (for example `anatomy` for a screen's parts, `annotated` for how to read a view, `callouts` for tips and warnings, `contact` to close). A comprehensive, technical or printable user guide is a Word/PDF document: hand the content to document-builder (`doc_type: user-guide`). Build and lint with that skill.

## Confluence training page (confluence-page-builder, optional)
`page_type: training-page`; sections Learning Objectives · Walkthrough · Practice · Knowledge Check · Quick Reference · Get Help. Put knowledge-check answers inside an `expand` block titled "Show answers". Link the video and quick start in Quick Reference.

## File names
`<Subject>_<Format>.md` (for example `Denials_Report_Quick_Start.md`); revisions add `_v2`.
