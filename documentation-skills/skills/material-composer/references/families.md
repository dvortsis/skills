# Families (read only your family's section)

## Reference Sheet (renderer doc-sheet)
One page per role or topic, scannable in under a minute. Title band, purpose line, a step diagram when there is a
sequence of 3–6 steps, numbered steps, one card for the worked example or key rule, two half-width blocks for short
sections, help block last. Budget: the format's word limit (250–450). Never shrink text to fit; cut words or split into a
second role page. Tables only for lookups (codes, contacts). Figures: the user's screenshots or library illustrations,
cropped so figure text is 8 pt or larger. Lists of 2–8 items. Exemplars: Quick Reference Card, Status Report.

## Long-Form Document (renderer doc-long)
Read, searched and kept. Task-based chapters, required sections per doc_type, procedures with results, captioned tables
and figures, glossary, revision history, sources. Reports lead with an Executive Summary that states the answer; every
number cites its source; recommendations are actions with an owner role. Guides and manuals use the textbook profile.

## Presentation (renderer deck)
One message per slide, titles that state the point. Instructor-led decks pair with a facilitator guide: every retrieval
slide has a matching "Check:" in the guide and the guide's agenda adds up to the session length (ILT_PAIR). Use the deck
skill's storytelling and visual-selection references.

## Facilitation (renderer training-md)
Lets someone else run the session the same way. Session overview, objectives, agenda table with minutes, one module per
H3 with timing, what to say, "Check:" and "Answer:", practice and transfer scenarios, materials and follow-up.

## Communication (renderer md)
Short, direct, warm. Order: why it is changing, what changes for the reader, what to do (with the date), help. Emails
have a subject of 60 characters or fewer that names the change. Talking points add anticipated questions with answers.
Chat posts stay under 120 words. A kit is a kit.json listing each piece with audience, channel, ADKAR stage, send date
and owner role, plus `names` (one canonical name and the variants to avoid); KIT_COVERAGE checks every piece.
Every kit also has an adoption-measures piece (reinforcement stage; `measures` list: measure, source, review_date; a
target only with its target_source, in Markdown a Target needs a Target Source section): KIT_ADOPTION.
Exemplars: Announcement Email, Manager Talking Points, FAQ, Adoption Measures, Change Kit.

## E-Learning (renderer module)
Self-paced practice with feedback: intro with objectives, short content screens (one idea each), a scenario or question
at least every 5 screens, feedback on every option, summary. 5–25 screens. HTML works offline. Storyboard is the review
copy. See `forms-and-elearning.md`.

## Data Collection (renderer form)
One question at a time, neutral wording, one scale per survey (1–5 with end labels by default), required items marked,
estimated minutes for surveys, no PHI fields unless approved. Training evaluations: 4–12 items covering relevance,
clarity, practice and confidence, plus one open comment. Readiness surveys map items to ADKAR stages. Outputs: fillable
PDF and an .xlsx question bank. Trackers (action tracker, issue log) use the xlsx renderer instead: one table, every status from the dropdown. See `forms-and-elearning.md`.

## Assessment (renderer training-md)
Questions test decisions in realistic situations; each has Answer and Why; 3–10 questions; scoring states the pass mark
only when the source gives one.
