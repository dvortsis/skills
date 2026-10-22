---
name: github-docs
description: Writes a textbook-style setup and user guide as GitHub Markdown in the project's docs/ folder (home page with a task finder, numbered chapters with What you will learn, task procedures with results, recommended-and-safe choices, worked examples, key takeaways, check questions with answers, settings reference, glossary, revisions and index) for moderately technical users who can install an app but may not know how to set it up safely. Reads the project itself for the facts (Unraid templates, compose files, Dockerfiles, .env examples, Windows installer scripts, settings code) and enforces the format and a calm, brief voice with a lint gate. Use when someone asks for GitHub docs, a docs folder, a setup or install guide, a user guide or README-linked documentation for a self-hosted app, container, NAS app or Windows app. Not for API reference docs for developers, Word or PDF documents, slides or Confluence pages.
version: 1.0.0
---

# GitHub Docs

You write the guide's Markdown pages in `docs/`; the scripts find the project's facts, scaffold the pages, keep the
generated parts in sync and check the result. GitHub renders the pages as they are, and maintainers keep editing them.

## 0. Preflight (first, before any other work)
Run `scripts/preflight.py` from this skill's folder (the folder containing this SKILL.md) with `python3` (or `python`
on Windows; the commands below say `python`). On `READY`, continue. If it fails or is missing, stop and say once: "The
github-docs skill loaded without its supporting files. Please attach `github-docs.zip` to this chat, or ask the agent
owner to re-upload it as a .zip." Never hand-write, approximate or skip a script.

## Workflow
1. **Frame.** The reader is the capable installer in `references/audience.md` unless the user names someone else;
   read it and `references/voice.md` once. Get the app name, the install methods to cover and the version. Infer what
   you can from the project; ask once, in one line, for the rest.
2. **Facts.** Run `python scripts/discover.py --project <repo> --out setup.facts.md`. It lists ports, folders,
   variables, secrets, network mode, installer service and firewall rules, each with its file and line, the files
   that define the settings screen (read them for every field's label, default and effect), the CONCEPTS the guide
   must explain and the OPEN questions. Every fact in the guide comes from that table, a file you read, or the user.
   Ask the OPEN questions once; anything still unknown becomes an open item in your reply, never a guess. Never
   invent a button, label, default or behavior.
3. **Outline.** Plan the chapters as tasks in the order the reader does them. The usual outline:
   Before you start · Install <app> · Set up <app> · Keep <app> safe · Everyday use (updates, backups) ·
   Troubleshooting, then Appendix A (answers), Appendix B (settings reference), glossary, revisions, index. Drop what
   the app doesn't need; the safety chapter and troubleshooting are required (`references/structure.md`).
4. **Scaffold.** `python scripts/docs_tool.py new <repo>/docs --title "<App> setup guide" --app <App> --chapters
   "Before you start;Install <App>;..."` (refuses to overwrite; for an existing docs folder, add pages by hand in the
   same shape). The home page gets the project logo when the brand has one (`scripts/brand.py`).
5. **Write.** Replace every `WRITE:` marker. Copy the patterns in `assets/example/project/docs/` (a complete guide for
   a synthetic app). For each step use the three-part pattern: do, why (one sentence), safe. For each choice, the
   recommended option first; name unsafe options with the safe alternative. Explain only the concepts discover
   listed, from `references/concepts.md`, in one sentence plus a `<details>` section or a glossary link. Add
   `<!-- index: term -->` markers under headings. Screenshots: only ones the user supplies; list missing ones in
   `docs/images/SHOTLIST.md` and report them as pending.
6. **Sync.** `python scripts/docs_tool.py sync <repo>/docs` numbers chapters and sections, fixes links to renumbered
   headings, and writes the contents, navigation and index. Run it after every edit.
7. **Lint.** `python scripts/lint_docs.py <repo>/docs`, fix, sync and re-run until `0 failed`; use `--strict` before
   delivering, so warnings get fixed too or are explained in the reply. The codes are listed in
   `references/structure.md` and `CHECKS.md`.
8. **Deliver.** Add one line to the project's top-level README linking `docs/README.md`. Reply in at most 6 lines:
   the chapter list, the open questions and pending screenshots, and `LINT: n checks, 0 failed, w warnings`. Don't
   paste the guide into chat. Don't commit or push unless the user asks.

## Revisions
Edit the pages in place, run sync and lint, and add a row to `revisions.md`. When the app changes (a new setting, a
new default), rerun discover and compare it with `setup.facts.md` before editing, so every changed fact is updated.

## Rules
- The reader can install an app, open an address and paste a command when told where. Everything else gets an exact
  instruction or a one-sentence explanation first.
- Every command says exactly where to run it and has a language tag; values to change are `<placeholders>`
  explained right after; no real keys, tokens or passwords anywhere.
- Every setting shows **Recommended:**; every choice table has exactly one `(recommended)` row; every unsafe option
  names the safe alternative in the same place.
- The safe defaults this skill holds the guide to: the web UI is never port-forwarded (VPN for remote access),
  firewall prompts allow private networks only, Defender exclusions cover only the data folder, UPnP stays off unless
  the app needs it, the data folder is mapped and backed up, and default passwords are replaced first.
- Sentence-case headings, second person, present tense, sentences of 25 words or fewer, paragraphs of 70 words or
  fewer outside `<details>`.

## Never
Reassurance or padding ("don't worry", "simply", "easy", "please note"); lectures; invented labels, defaults or
screens; a choice without its safe answer; a warning without what to do instead; a command without where to run it;
real secrets in examples; instructions to disable a firewall or antivirus, forward a web UI port or use the router
DMZ; delivering with a FAIL.
