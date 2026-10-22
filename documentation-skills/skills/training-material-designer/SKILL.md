---
name: training-material-designer
description: Designs training and enablement materials for any audience and subject (a report or dashboard, an application, a process, a policy or a rollout) using a learning-science method grounded in cited sources. Produces video scripts, quick starts, job aids, facilitator guides and knowledge checks with a lint gate, designs training decks for slide-deck and training pages for confluence-page-builder (optional). Use when someone asks for training, enablement, onboarding, a rollout or change-management kit, a tutorial, a video script, a quick start, a cheat sheet, a job aid, a quiz or knowledge check, or a facilitator guide.
version: 1.6.0
---

# Training Material Designer

Commands below use `python3`; use `python` where that is the interpreter's name (Windows).

## 0. Preflight (first, before any other work)
Run `scripts/preflight.py` from this skill's folder (the folder containing this SKILL.md). On `READY`, continue. If it fails or is missing, stop and say once: "The training-material-designer skill loaded without its supporting files. Please attach `training-material-designer.zip` to this chat, or ask the agent owner to re-upload it as a .zip." When the zip is attached, extract it, run preflight there, and run every command from that folder. Never hand-write, approximate or skip a script.

## Scope
- Make training only when asked, and only the format asked for. Offer the other formats in one line at the end; don't create them.
- Ground every fact in the request, attachments, sources found with connected search tools (if any) or the sources the user names. Build the subject's facts table first (`references/subject-profile.md`). Never invent screens, buttons, rules, numbers or steps; ask once, or list them as open questions.
- Use placeholder roles and personas ("a billing specialist in the West region"), never real people. For an audience that spans domains, draw examples from `references/general-examples.md` or the one subdomain the request names. No PHI or other real personal data in examples, scenarios or screenshots. Use only screenshots the user supplies.

## Workflow
1. **Frame.** Get the audience, the subject, what learners must be able to do afterward (observable verbs) and the format. If unclear, ask once in a single line.
2. **Facts table.** Read sources once; fill the facts table in `<subject>.facts.md` with a source per row. Read `references/learning-method.md`.
3. **Design** from `references/formats.md`:
   - Video script, quick start, job aid, facilitator guide, knowledge check: copy the matching file in `assets/examples/`, replace the content, keep the front matter and headings.
   - **Training deck:** design the outline with this method, then build it with the slide-deck skill (its deck.json, build and lint). Retrieval checks become `statement` slides (`"role": "retrieval"`, "Quick check: …?"); the next slide gives the answer on the slide (`"role": "answer"`) and the notes may repeat it; walkthroughs use the user's screenshots with numbered callouts.
   - **Confluence training page:** build it with the confluence-page-builder skill (optional; when it is not installed, say so and offer a quick start or job aid instead) using `page_type: training-page`.
4. **Lint.** `python3 scripts/lint_training.py <file>.md` (house terms come from the project's brand profile, `terminology` in brand.json; `--brand brand.json` overrides). Fix and re-run until `0 failed`. Decks and pages pass their own skill's gate instead.
   - **Video script:** then `scripts/md_to_captions.py <file>.md` writes `<file>.srt` captions and `<file>.transcript.md`; deliver both with the script.
   - **One-page PDF** (front matter `output: pdf`, quick-start or job-aid; `references/formats.md` → One-page PDF): the .md stays the single source. `scripts/md_to_sheet.py <file>.md` (`--combine` for one PDF of several) → build with document-builder using the printed command (it applies the project's logo, colors, fonts and footer) → `lint_training.py <file>.md --pdf <file>.pdf` until 0 failed (QS_SOURCE_MATCH; after any .md edit, convert and rebuild). When a documentation overlay skill is attached, also run its gate and sheet visual review.
5. **Deliver** each file as a link with one line on where it's used. Then the checks line (`LINT: n file(s), 0 failed`), any pending screenshots as an open item, and at most three open questions. Use one name for each document, role, status and screen label across the set (`references/formats.md`). Never paste the material into chat.

## Revisions
Edit the file with targeted changes, re-lint, re-deliver under the same name with `_v2`. Don't regenerate unchanged sections. When a change retires wording, an example or a label in one deliverable of a set, record it in `<file_key>.set.json` in the same step. After a user approves one deliverable, list the passages in the others that still need the change (carry over) and what stays in that deliverable only.

## Anti-slop (never)
Objectives that start with "understand" or "know"; feature tours with no task; walls of text; quizzes that test trivia instead of decisions; checks without answers; unsourced or unstamped screen drawings presented as screenshots; invented steps or numbers; real names or PHI in scenarios; filler words (leverage, unlock, seamless, robust, empower, deep dive); delivering with a FAIL.
