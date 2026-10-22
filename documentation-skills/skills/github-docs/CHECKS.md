# CHECKS: github-docs

Every code `scripts/lint_docs.py` reports. FAIL blocks delivery; WARN fails only with `--strict`. Rules behind each:
`references/structure.md` (format) and `references/voice.md` (voice). Self-test: `scripts/test_docs.py` breaks the
example guide once per FAIL code below and checks the code fires.

| Code | Level | Checks |
|---|---|---|
| STRUCTURE | FAIL | README.md, glossary.md, revisions.md and index.md exist; at least two chapters |
| CHAPTER_FILES | FAIL | Chapter files are numbered 01, 02, ... without gaps |
| SECURITY_CHAPTER | FAIL | A chapter title has "safe" or "secure" |
| TROUBLESHOOTING | FAIL | A Problem · Likely cause · Fix table exists and every row is complete |
| SETTINGS_REFERENCE | WARN | A settings reference appendix exists |
| WORKED_EXAMPLE | FAIL | At least one `[!NOTE]` starting **Worked example** |
| CHECKS | WARN | At least one chapter has Check your understanding |
| HOME_SECTIONS | FAIL | The home page has Who this guide is for, How to use this guide, Contents (with markers), What you need, About this guide |
| TASK_FINDER | FAIL | An If you want to · Go to table links at least three chapters |
| REVISIONS | FAIL | revisions.md has a Version · Date · Change table with a row |
| INDEX | FAIL | index.md has at least three entries |
| SYNC_STALE | FAIL | `docs_tool.py sync` would change nothing (numbering, contents, navigation, index) |
| ANSWERS | FAIL | Appendix A answers every chapter's questions, same count, under the chapter's title |
| GLOSSARY_ORDER | FAIL | Glossary terms are A to Z |
| GLOSSARY_LINK | WARN | A page links a glossary term the first time it uses it |
| H1_ONE | FAIL | One `#` heading per page |
| HEADING_LEVEL | FAIL | Heading levels never skip |
| HEADING_CASE | WARN | Headings in sentence case, not Title Case |
| NUMBERING | FAIL | Chapter H1 is `Chapter N: Title` and `##` headings are `N.M Title` |
| OBJECTIVES | FAIL | A `[!NOTE]` **What you will learn** box with 2–6 items before the first section (not on Troubleshooting) |
| OBJECTIVE_VERB | FAIL | Objectives start with an observable verb, not understand or know |
| TAKEAWAYS | FAIL | A `[!TIP]` **Key takeaways** box with 2–6 items after the last section (not on Troubleshooting) |
| PLACEHOLDER | FAIL | No WRITE:, TODO, TBD, FIXME or lorem ipsum |
| NAV | FAIL | The page has navigation markers |
| LINK_BROKEN | FAIL | Relative links and anchors resolve |
| IMG_MISSING | FAIL | Images exist |
| IMG_ALT | FAIL | Alt text has four or more words (a logo's alt names the logo) |
| ALERT_KIND | FAIL | Alerts are NOTE, TIP, IMPORTANT, WARNING or CAUTION |
| ALERT_SYNTAX | FAIL | `> [!KIND]` stands alone on its line |
| ALERT_DENSITY | WARN | Two alerts per section at most, besides the two boxes |
| UNSAFE_ALTERNATIVE | FAIL | A WARNING, CAUTION or **Unsafe:** that says what not to do also says what to do instead |
| CODE_LANG | FAIL | Every code block has a language tag |
| COMMAND_WHERE | FAIL | The sentence before a shell command says where to run it |
| SECRET_LITERAL | FAIL | No real-looking key, token or password; use `<placeholders>` |
| VOICE_PADDING | FAIL / WARN | No reassurance or padding (fails: don't worry, simply, of course, please note, ...; warns: just, easy, very, in order to, ...) |
| SENTENCE_LONG | WARN | Sentences of 25 words or fewer |
| BACKGROUND_LONG | WARN | Paragraphs of 70 words or fewer outside `<details>` |
| CHOICE_RECOMMENDED | FAIL | A choice table (first header Option, Choice, Value or Mode) has exactly one `(recommended)` row |
| SETTING_RECOMMENDED | FAIL | Every setting under a Settings/Fields/Options section has **Recommended:**; the settings reference table has a value in every row |
| PROCEDURE_STEPS | FAIL / WARN | A `To ...:` procedure has 2–12 numbered steps (warns on steps over 40 words) |
| PROCEDURE_RESULT | FAIL | A procedure has at least one indented **Result:** line |
| PROCEDURE_VERB | WARN | Steps start with the action |
